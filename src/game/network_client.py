import socketio
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class NetworkPlayer:
    id: str
    name: str
    x: float
    y: float
    pokemon: str
    direction_x: float = 1  # Default looking right
    direction_y: float = 0  # Default looking right
    in_dungeon: bool = False  # Whether the player is in a dungeon

@dataclass
class WildPokemon:
    id: str
    name: str
    level: int
    current_hp: int
    max_hp: int
    position: List[float]
    moves: List[str]
    animation_state: str = "Idle"

@dataclass
class ServerDungeon:
    dungeon_id: str
    width: int
    height: int
    tile_size: int
    floor: int
    tiles: List[List[int]]
    ladder_position: tuple[int, int]
    wild_pokemon: List[WildPokemon]
    explored: List[List[bool]]
    enemy_projectiles: List[dict] = field(default_factory=list)  # Store enemy projectiles data
    spawn_point: tuple[int, int] = field(default=(0, 0))  # Store the validated spawn point
    rooms: List[dict] = field(default_factory=list)  # Store room data for minimap
    
    def get_player_spawn(self):
        """Return the spawn point for the player in this dungeon.
        This method is required for compatibility with the Dungeon class.
        """
        return self.spawn_point

class NetworkClient:
    def __init__(self):
        self.sio = socketio.Client()
        self.connected = False
        self.players: Dict[str, NetworkPlayer] = {}
        self.player_id: Optional[str] = None
        self.current_dungeon: Optional[ServerDungeon] = None
        self.in_dungeon = False
        self.wild_pokemon: List[WildPokemon] = []
        self._setup_events()
    
    def _setup_events(self):
        @self.sio.event
        def connect():
            print('Connected to server')
            self.connected = True

        @self.sio.event
        def disconnect():
            print('Disconnected from server')
            self.connected = False
            self.players.clear()
            self.player_id = None
            self.current_dungeon = None
            self.in_dungeon = False
            self.wild_pokemon.clear()

        @self.sio.on('players_state')
        def on_players_state(data):
            self.players.clear()
            for player_data in data['players']:
                self.players[player_data['id']] = NetworkPlayer(
                    id=player_data['id'],
                    name=player_data['name'],
                    x=player_data['x'],
                    y=player_data['y'],
                    pokemon=player_data['pokemon'],
                    direction_x=player_data.get('direction_x', 1),
                    direction_y=player_data.get('direction_y', 0),
                    in_dungeon=player_data.get('in_dungeon', False)
                )

        @self.sio.on('player_joined')
        def on_player_joined(data):
            self.players[data['id']] = NetworkPlayer(
                id=data['id'],
                name=data['name'],
                x=data['x'],
                y=data['y'],
                pokemon=data['pokemon'],
                direction_x=data.get('direction_x', 1),
                direction_y=data.get('direction_y', 0),
                in_dungeon=data.get('in_dungeon', False)
            )

        @self.sio.on('player_moved')
        def on_player_moved(data):
            if data['id'] in self.players:
                self.players[data['id']].x = data['x']
                self.players[data['id']].y = data['y']
                self.players[data['id']].direction_x = data['direction_x']
                self.players[data['id']].direction_y = data['direction_y']

        @self.sio.on('player_disconnected')
        def on_player_disconnected(data):
            if data['player_id'] in self.players:
                del self.players[data['player_id']]
                
        @self.sio.on('dungeon_state')
        def on_dungeon_state(data):
            print(f"Received dungeon state: {data['dungeon_id']}")
            self.in_dungeon = True
            
            # Create ServerDungeon object
            state = data['state']
            
            # Validate spawn point from server
            spawn_point = (0, 0)
            if 'spawn_point' in state:
                spawn_point = tuple(state['spawn_point'])
                print(f"Received spawn point from server: {spawn_point}")
                
                # Validate that the spawn point is on a walkable tile
                spawn_x, spawn_y = spawn_point
                grid_x = int(spawn_x // state['tile_size'])
                grid_y = int(spawn_y // state['tile_size'])
                
                if (0 <= grid_x < len(state['tiles'][0]) and 
                    0 <= grid_y < len(state['tiles']) and 
                    state['tiles'][grid_y][grid_x] == 0):
                    print(f"Spawn point is valid (on a floor tile)")
                else:
                    print(f"WARNING: Received invalid spawn point from server! Will need to find a valid position.")
                    # We'll let the main game loop handle finding a valid position
            else:
                print(f"No spawn point received from server, will use default")
            
            self.current_dungeon = ServerDungeon(
                dungeon_id=data['dungeon_id'],
                width=state['width'],
                height=state['height'],
                tile_size=state['tile_size'],
                floor=state['floor'],
                tiles=state['tiles'],
                ladder_position=state['ladder_position'],
                wild_pokemon=[],
                explored=state['explored'],
                enemy_projectiles=[],
                spawn_point=spawn_point,
                rooms=state.get('rooms', [])
            )
            
            # Update wild Pokémon
            self.wild_pokemon = []
            for pokemon_data in state['wild_pokemon']:
                self.wild_pokemon.append(WildPokemon(
                    id=pokemon_data['id'],
                    name=pokemon_data['name'],
                    level=pokemon_data['level'],
                    current_hp=pokemon_data['current_hp'],
                    max_hp=pokemon_data['max_hp'],
                    position=pokemon_data['position'],
                    moves=pokemon_data['moves'],
                    animation_state=pokemon_data['animation_state']
                ))
        
        @self.sio.on('dungeon_update')
        def on_dungeon_update(data):
            if self.in_dungeon and self.current_dungeon:
                # Update wild Pokémon
                if 'wild_pokemon' in data:
                    self.wild_pokemon = []
                    for pokemon_data in data['wild_pokemon']:
                        self.wild_pokemon.append(WildPokemon(
                            id=pokemon_data['id'],
                            name=pokemon_data['name'],
                            level=pokemon_data['level'],
                            current_hp=pokemon_data['current_hp'],
                            max_hp=pokemon_data['max_hp'],
                            position=pokemon_data['position'],
                            moves=pokemon_data['moves'],
                            animation_state=pokemon_data['animation_state']
                        ))
                
                # Update explored tiles
                if 'explored' in data and self.current_dungeon:
                    self.current_dungeon.explored = data['explored']
                
                # Update enemy projectiles
                if 'enemy_projectiles' in data and self.current_dungeon:
                    self.current_dungeon.enemy_projectiles = data['enemy_projectiles']
        
        @self.sio.on('movement_rejected')
        def on_movement_rejected(data):
            print(f"Movement rejected, reverting to position: ({data['x']}, {data['y']})")
            # This would be handled in the game to revert player position
        
        @self.sio.on('attack_results')
        def on_attack_results(data):
            print(f"Attack results: {len(data['affected_pokemon'])} Pokémon affected")
            # This would be handled in the game to show attack effects
        
        @self.sio.on('exited_dungeon')
        def on_exited_dungeon(data):
            print(f"Exited dungeon, position: ({data['x']}, {data['y']})")
            self.in_dungeon = False
            self.current_dungeon = None
            self.wild_pokemon.clear()
    
    def connect_to_server(self, server_url: str = 'http://localhost:5000') -> bool:
        try:
            if not self.connected:
                self.sio.connect(server_url)
            return True
        except Exception as e:
            print(f'Failed to connect to server: {e}')
            return False
    
    def disconnect_from_server(self):
        if self.connected:
            self.sio.disconnect()
    
    def get_dungeon_tiles(self):
        """Get the tiles of the current dungeon for minimap rendering."""
        if self.current_dungeon:
            return self.current_dungeon.tiles
        return []
    
    def get_dungeon_explored(self):
        """Get the explored tiles of the current dungeon for minimap rendering."""
        if self.current_dungeon:
            return self.current_dungeon.explored
        return []
    
    def get_dungeon_ladder_position(self):
        """Get the position of the ladder in the current dungeon."""
        if self.current_dungeon:
            return self.current_dungeon.ladder_position
        return (0, 0)
    
    def get_wild_pokemon(self):
        """Get the wild Pokémon in the current dungeon."""
        return self.wild_pokemon
    
    def join_game(self, player_name: str, pokemon_name: str, x: float, y: float):
        if self.connected:
            self.sio.emit('player_join', {
                'name': player_name,
                'pokemon': pokemon_name,
                'x': x,
                'y': y
            })
    
    def update_position(self, x: float, y: float, direction_x: float, direction_y: float):
        if self.connected:
            # Validate movement against dungeon tiles if in dungeon
            if self.in_dungeon and self.current_dungeon:
                tile_x = int(x / self.current_dungeon.tile_size)
                tile_y = int(y / self.current_dungeon.tile_size)
                
                # Check if the position is within bounds and on a valid tile
                if (0 <= tile_x < self.current_dungeon.width and
                    0 <= tile_y < self.current_dungeon.height and
                    self.current_dungeon.tiles[tile_y][tile_x] == 0):  # 0 represents floor tiles
                    
                    # Update explored tiles around the player
                    self._update_explored_tiles(tile_x, tile_y)
                    
                    # Send movement to server
                    self.sio.emit('player_move', {
                        'x': x,
                        'y': y,
                        'direction_x': direction_x,
                        'direction_y': direction_y
                    })
            else:
                # Not in dungeon, send movement directly
                self.sio.emit('player_move', {
                    'x': x,
                    'y': y,
                    'direction_x': direction_x,
                    'direction_y': direction_y
                })
                
    def _update_explored_tiles(self, center_x: int, center_y: int, visibility_radius: int = 5):
        """Update the explored tiles around the player's position"""
        if not self.current_dungeon or not self.current_dungeon.explored:
            return
            
        for y in range(max(0, center_y - visibility_radius), 
                       min(self.current_dungeon.height, center_y + visibility_radius + 1)):
            for x in range(max(0, center_x - visibility_radius),
                          min(self.current_dungeon.width, center_x + visibility_radius + 1)):
                # Simple circular visibility check
                if ((x - center_x) ** 2 + (y - center_y) ** 2) <= visibility_radius ** 2:
                    self.current_dungeon.explored[y][x] = True
    
    def get_other_players(self) -> List[NetworkPlayer]:
        return [p for p in self.players.values() if p.id != self.player_id]
    
    def enter_dungeon(self, floor: int = 1):
        """Request to enter a dungeon"""
        if self.connected:
            self.sio.emit('enter_dungeon', {
                'floor': floor
            })
    
    def exit_dungeon(self):
        """Request to exit the current dungeon"""
        if self.connected and self.in_dungeon:
            self.sio.emit('exit_dungeon')
    
    def next_floor(self):
        """Request to advance to the next floor"""
        if self.connected and self.in_dungeon:
            self.sio.emit('next_floor')
    
    def attack(self, move_name: str, damage: int, attack_range: int, attack_type: str = 'direct'):
        """Send an attack to the server"""
        if self.connected and self.in_dungeon:
            self.sio.emit('attack', {
                'move_name': move_name,
                'damage': damage,
                'range': attack_range,
                'type': attack_type
            })
    
    def update_dungeon(self):
        """Request an update of the dungeon state"""
        if self.connected and self.in_dungeon:
            self.sio.emit('update_dungeon')
    
    def get_dungeon_tiles(self) -> List[List[int]]:
        """Get the current dungeon tiles"""
        if self.in_dungeon and self.current_dungeon:
            return self.current_dungeon.tiles
        return []
    
    def get_dungeon_explored(self) -> List[List[bool]]:
        """Get the explored tiles for the current dungeon"""
        if self.in_dungeon and self.current_dungeon:
            return self.current_dungeon.explored
        return []
    
    def get_dungeon_ladder_position(self) -> tuple[int, int]:
        """Get the position of the ladder in the current dungeon"""
        if self.in_dungeon and self.current_dungeon:
            return self.current_dungeon.ladder_position
        return (0, 0)
    
    def get_wild_pokemon(self) -> List[WildPokemon]:
        """Get the wild Pokémon in the current dungeon"""
        if self.in_dungeon:
            return self.wild_pokemon
        return []