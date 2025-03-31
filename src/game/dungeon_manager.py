import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import logging

@dataclass
class Room:
    x: int
    y: int
    width: int
    height: int

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
    cooldown: int = 0

@dataclass
class ServerDungeon:
    width: int
    height: int
    tile_size: int
    floor: int
    tiles: List[List[int]]
    rooms: List[Room]
    ladder_position: Tuple[int, int]
    wild_pokemon: List[WildPokemon] = field(default_factory=list)
    explored: Dict[str, List[List[bool]]] = field(default_factory=dict)  # Player ID -> explored tiles

class DungeonManager:
    def __init__(self):
        self.dungeons: Dict[str, ServerDungeon] = {}  # Dungeon ID -> Dungeon
        self.player_dungeons: Dict[str, str] = {}  # Player ID -> Dungeon ID
        
    def create_dungeon(self, width: int, height: int, tile_size: int, floor: int = 1) -> str:
        """Create a new dungeon and return its ID"""
        dungeon_id = f"dungeon_{len(self.dungeons)}"
        tiles, rooms = self._generate_dungeon(width, height, tile_size)
        room_objects = [Room(r[0], r[1], r[2], r[3]) for r in rooms]
        ladder_position = self._place_ladder(room_objects, tile_size)
        
        dungeon = ServerDungeon(
            width=width,
            height=height,
            tile_size=tile_size,
            floor=floor,
            tiles=tiles,
            rooms=room_objects,
            ladder_position=ladder_position,
            wild_pokemon=self._spawn_wild_pokemon(room_objects, tile_size, floor)
        )
        
        self.dungeons[dungeon_id] = dungeon
        return dungeon_id
    
    def assign_player_to_dungeon(self, player_id: str, dungeon_id: str) -> None:
        """Assign a player to a dungeon"""
        self.player_dungeons[player_id] = dungeon_id
        # Initialize explored tiles for this player
        dungeon = self.dungeons[dungeon_id]
        width_tiles = dungeon.width // dungeon.tile_size
        height_tiles = dungeon.height // dungeon.tile_size
        dungeon.explored[player_id] = [[False for _ in range(width_tiles)] for _ in range(height_tiles)]
    
    def get_player_spawn(self, dungeon_id: str) -> Tuple[int, int]:
        """Get the spawn position for a player in a dungeon
        Enhanced to ensure players never spawn in walls.
        """
        dungeon = self.dungeons[dungeon_id]
        
        # Validate that we have rooms
        if not dungeon.rooms:
            logging.error(f"No rooms found in dungeon {dungeon_id}")
            # Create a default spawn at (0,0) and find a valid spot from there
            return self._find_nearest_valid_spawn(dungeon_id, 0, 0)
        
        first_room = dungeon.rooms[0]
        
        # Calculate center of first room
        center_x = (first_room.x + first_room.width // 2) * dungeon.tile_size
        center_y = (first_room.y + first_room.height // 2) * dungeon.tile_size
        
        # If center is walkable, use it
        if self.is_walkable(dungeon_id, center_x, center_y):
            logging.info(f"Using room center as spawn point: ({center_x}, {center_y})")
            return center_x, center_y
            
        # Otherwise, search nearby tiles for a walkable spot
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                test_x = center_x + (dx * dungeon.tile_size)
                test_y = center_y + (dy * dungeon.tile_size)
                if self.is_walkable(dungeon_id, test_x, test_y):
                    logging.info(f"Using nearby tile as spawn point: ({test_x}, {test_y})")
                    return test_x, test_y
                    
        # If no walkable spot found, search the entire first room systematically
        logging.info(f"Searching entire first room for spawn point")
        for ry in range(first_room.y, first_room.y + first_room.height):
            for rx in range(first_room.x, first_room.x + first_room.width):
                world_x = rx * dungeon.tile_size
                world_y = ry * dungeon.tile_size
                if self.is_walkable(dungeon_id, world_x, world_y):
                    logging.info(f"Found valid spawn in room: ({world_x}, {world_y})")
                    return world_x, world_y
        
        # If still no walkable spot found, try all rooms
        logging.warning(f"First room has no valid spawn points, checking all rooms")
        for room in dungeon.rooms[1:]:  # Skip first room as we already checked it
            for ry in range(room.y, room.y + room.height):
                for rx in range(room.x, room.x + room.width):
                    world_x = rx * dungeon.tile_size
                    world_y = ry * dungeon.tile_size
                    if self.is_walkable(dungeon_id, world_x, world_y):
                        logging.info(f"Found valid spawn in another room: ({world_x}, {world_y})")
                        return world_x, world_y
        
        # If still no walkable spot found, use spiral search to find the nearest valid position
        logging.warning(f"No valid spawn found in any room, using spiral search")
        return self._find_nearest_valid_spawn(dungeon_id, center_x, center_y)
    
    def is_walkable(self, dungeon_id: str, x: int, y: int) -> bool:
        """Check if a position is walkable in the dungeon"""
        dungeon = self.dungeons[dungeon_id]
        # Convert to tile coordinates
        tile_x = x // dungeon.tile_size
        tile_y = y // dungeon.tile_size
        
        # Check bounds
        if tile_x < 0 or tile_x >= len(dungeon.tiles[0]) or tile_y < 0 or tile_y >= len(dungeon.tiles):
            return False
            
        # Check if tile is floor (0 is floor, 1 is wall)
        return dungeon.tiles[tile_y][tile_x] == 0

    def update_explored(self, player_id: str, position: Tuple[float, float]) -> None:
        """Update explored tiles for a player"""
        if player_id not in self.player_dungeons:
            return
            
        dungeon_id = self.player_dungeons[player_id]
        dungeon = self.dungeons[dungeon_id]
        
        grid_x = int(position[0] // dungeon.tile_size)
        grid_y = int(position[1] // dungeon.tile_size)
        
        if 0 <= grid_x < len(dungeon.tiles[0]) and 0 <= grid_y < len(dungeon.tiles):
            dungeon.explored[player_id][grid_y][grid_x] = True
            
            # Check if the player is in a room and mark the entire room as explored
            for room in dungeon.rooms:
                if room.x <= grid_x < room.x + room.width and room.y <= grid_y < room.y + room.height:
                    for y in range(room.y, room.y + room.height):
                        for x in range(room.x, room.x + room.width):
                            dungeon.explored[player_id][y][x] = True
                    break
    
    def is_valid_move(self, dungeon_id: str, x: float, y: float, width: float, height: float) -> bool:
        """Check if a move is valid"""
        dungeon = self.dungeons[dungeon_id]
        
        # Check all four corners of the rectangle
        corners = [
            (x, y),                # Top-left
            (x + width, y),        # Top-right
            (x, y + height),       # Bottom-left
            (x + width, y + height) # Bottom-right
        ]
        
        for corner in corners:
            if not self._is_walkable(dungeon, corner[0], corner[1]):
                return False
                
        return True
    
    def get_dungeon_state(self, dungeon_id: str, player_id: str) -> dict:
        """Get the current state of a dungeon for a specific player"""
        dungeon = self.dungeons[dungeon_id]
        
        return {
            "width": dungeon.width,
            "height": dungeon.height,
            "tile_size": dungeon.tile_size,
            "floor": dungeon.floor,
            "tiles": dungeon.tiles,
            "ladder_position": dungeon.ladder_position,
            "explored": dungeon.explored.get(player_id, []),
            "wild_pokemon": [
                {
                    "id": pokemon.id,
                    "name": pokemon.name,
                    "level": pokemon.level,
                    "current_hp": pokemon.current_hp,
                    "max_hp": pokemon.max_hp,
                    "position": pokemon.position,
                    "moves": pokemon.moves,
                    "animation_state": pokemon.animation_state
                } for pokemon in dungeon.wild_pokemon
            ]
        }
    
    def update_wild_pokemon(self, dungeon_id: str, player_positions: Dict[str, Tuple[float, float]]) -> None:
        """Update wild Pokémon behavior based on player positions"""
        dungeon = self.dungeons[dungeon_id]
        
        for pokemon in dungeon.wild_pokemon:
            # Decrease cooldown if it exists
            if pokemon.cooldown > 0:
                pokemon.cooldown -= 1
            
            # Find the closest player
            closest_player_id = None
            closest_distance = float('inf')
            
            for player_id, position in player_positions.items():
                dx = position[0] - pokemon.position[0]
                dy = position[1] - pokemon.position[1]
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < closest_distance:
                    closest_distance = distance
                    closest_player_id = player_id
            
            if closest_player_id is None:
                continue
                
            # Get the closest player's position
            player_pos = player_positions[closest_player_id]
            
            # Simple AI: move towards the player if they're close enough
            if closest_distance < 300:  # Detection range
                # Calculate direction to player
                dx = player_pos[0] - pokemon.position[0]
                dy = player_pos[1] - pokemon.position[1]
                
                # Normalize the direction vector
                magnitude = math.sqrt(dx*dx + dy*dy)
                if magnitude > 0:
                    dx = (dx / magnitude) * 2  # Speed of 2
                    dy = (dy / magnitude) * 2
                    
                    # HP percentage to determine if the Pokémon should retreat
                    hp_percentage = pokemon.current_hp / pokemon.max_hp
                    if hp_percentage < 0.3:  # Retreat when HP is below 30%
                        dx = -dx
                        dy = -dy
                    
                    # Try to move
                    new_x = pokemon.position[0] + dx
                    new_y = pokemon.position[1] + dy
                    
                    if self._is_walkable(dungeon, new_x, new_y):
                        pokemon.position[0] = new_x
                        pokemon.position[1] = new_y
                        pokemon.animation_state = "Walk"
                    else:
                        # Try horizontal movement
                        if self._is_walkable(dungeon, pokemon.position[0] + dx, pokemon.position[1]):
                            pokemon.position[0] += dx
                            pokemon.animation_state = "Walk"
                        # Try vertical movement
                        elif self._is_walkable(dungeon, pokemon.position[0], pokemon.position[1] + dy):
                            pokemon.position[1] += dy
                            pokemon.animation_state = "Walk"
                        else:
                            pokemon.animation_state = "Idle"
            else:
                # Random wandering when no player is nearby
                if random.random() < 0.02:  # 2% chance to change direction each update
                    angle = random.uniform(0, 2 * math.pi)
                    dx = math.cos(angle) * 2
                    dy = math.sin(angle) * 2
                    
                    new_x = pokemon.position[0] + dx
                    new_y = pokemon.position[1] + dy
                    
                    if self._is_walkable(dungeon, new_x, new_y):
                        pokemon.position[0] = new_x
                        pokemon.position[1] = new_y
                        pokemon.animation_state = "Walk"
                    else:
                        pokemon.animation_state = "Idle"
    
    def handle_player_attack(self, dungeon_id: str, player_id: str, attack_data: dict) -> List[dict]:
        """Handle a player's attack and return affected wild Pokémon"""
        dungeon = self.dungeons[dungeon_id]
        affected_pokemon = []
        
        # Extract attack data
        attack_type = attack_data.get("type", "direct")
        position = attack_data.get("position", (0, 0))
        direction = attack_data.get("direction", (0, 0))
        damage = attack_data.get("damage", 10)
        range_value = attack_data.get("range", 50)
        
        for pokemon in dungeon.wild_pokemon:
            # Calculate distance between attack and Pokémon
            if attack_type == "direct":
                # Direct attacks need to be close to the Pokémon
                dx = pokemon.position[0] - position[0]
                dy = pokemon.position[1] - position[1]
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance <= range_value:
                    # Apply damage
                    pokemon.current_hp = max(0, pokemon.current_hp - damage)
                    affected_pokemon.append({
                        "id": pokemon.id,
                        "damage": damage,
                        "current_hp": pokemon.current_hp,
                        "max_hp": pokemon.max_hp
                    })
            elif attack_type == "projectile":
                # Projectile logic would be implemented here
                pass
        
        # Remove fainted Pokémon
        dungeon.wild_pokemon = [p for p in dungeon.wild_pokemon if p.current_hp > 0]
        
        return affected_pokemon
    
    def _generate_dungeon(self, width: int, height: int, tile_size: int) -> Tuple[List[List[int]], List[Tuple[int, int, int, int]]]:
        """Generate a random dungeon layout"""
        # Initialize the dungeon grid with walls (1)
        width_tiles = width // tile_size
        height_tiles = height // tile_size
        tiles = [[1 for _ in range(width_tiles)] for _ in range(height_tiles)]

        # Generate random rooms with spacing
        num_rooms = random.randint(8, 15)  # Number of rooms
        rooms = []
        for _ in range(num_rooms):
            for attempt in range(5):  # Try up to 5 times to place the room
                room_width = random.randint(3, 8)  # Room width in tiles
                room_height = random.randint(3, 8)  # Room height in tiles
                room_x = random.randint(1, width_tiles - room_width - 2)  # Leave 1-tile spacing
                room_y = random.randint(1, height_tiles - room_height - 2)  # Leave 1-tile spacing

                # Check if the room overlaps with existing rooms or is too close (less than 1 tile apart)
                overlaps = False
                for other_room in rooms:
                    if (
                        room_x - 1 < other_room[0] + other_room[2] and
                        room_x + room_width + 1 > other_room[0] and
                        room_y - 1 < other_room[1] + other_room[3] and
                        room_y + room_height + 1 > other_room[1]
                    ):
                        overlaps = True
                        break

                if not overlaps:
                    # Room placement is valid, add it to the list
                    rooms.append((room_x, room_y, room_width, room_height))

                    # Carve out the room in the grid
                    for y in range(room_y, room_y + room_height):
                        for x in range(room_x, room_x + room_width):
                            tiles[y][x] = 0  # 0 represents a floor
                    break  # Exit the retry loop if the room is successfully placed

        # Connect the rooms with walkways
        for i in range(len(rooms) - 1):
            room_a = rooms[i]
            room_b = rooms[i + 1]

            # Get the center of each room
            center_a = (room_a[0] + room_a[2] // 2, room_a[1] + room_a[3] // 2)
            center_b = (room_b[0] + room_b[2] // 2, room_b[1] + room_b[3] // 2)

            # Create a horizontal walkway
            if center_a[0] < center_b[0]:
                for x in range(center_a[0], center_b[0] + 1):
                    tiles[center_a[1]][x] = 0
            else:
                for x in range(center_b[0], center_a[0] + 1):
                    tiles[center_a[1]][x] = 0

            # Create a vertical walkway
            if center_a[1] < center_b[1]:
                for y in range(center_a[1], center_b[1] + 1):
                    tiles[y][center_b[0]] = 0
            else:
                for y in range(center_b[1], center_a[1] + 1):
                    tiles[y][center_b[0]] = 0

        return tiles, rooms
    
    def _place_ladder(self, rooms: List[Room], tile_size: int) -> Tuple[int, int]:
        """Place the ladder in a random room"""
        random_room = random.choice(rooms[1:]) if len(rooms) > 1 else rooms[0]  # Skip the first room if possible
        ladder_x = random.randint(random_room.x + 1, random_room.x + random_room.width - 2) * tile_size
        ladder_y = random.randint(random_room.y + 1, random_room.y + random_room.height - 2) * tile_size
        return ladder_x, ladder_y
    
    def _is_walkable(self, dungeon: ServerDungeon, x: float, y: float) -> bool:
        """Check if a position is walkable"""
        grid_x = int(x // dungeon.tile_size)
        grid_y = int(y // dungeon.tile_size)
        if 0 <= grid_x < len(dungeon.tiles[0]) and 0 <= grid_y < len(dungeon.tiles):
            return dungeon.tiles[grid_y][grid_x] == 0
        return False
        
    def _find_nearest_valid_spawn(self, dungeon_id: str, x: float, y: float) -> Tuple[int, int]:
        """Find the nearest valid (walkable) spawn point using a spiral search pattern.
        Enhanced to ensure players never spawn in walls.
        """
        dungeon = self.dungeons[dungeon_id]
        
        # First try: check if the original position is already valid
        if self.is_walkable(dungeon_id, x, y):
            return (int(x), int(y))
        
        # Second try: check room centers first as they're most likely to be valid
        for room in dungeon.rooms:
            room_center_x = (room.x + room.width // 2) * dungeon.tile_size
            room_center_y = (room.y + room.height // 2) * dungeon.tile_size
            if self.is_walkable(dungeon_id, room_center_x, room_center_y):
                return (room_center_x, room_center_y)
        
        # Third try: systematic search through all room tiles
        for room in dungeon.rooms:
            for ry in range(room.y, room.y + room.height):
                for rx in range(room.x, room.x + room.width):
                    world_x = rx * dungeon.tile_size
                    world_y = ry * dungeon.tile_size
                    if self.is_walkable(dungeon_id, world_x, world_y):
                        return (world_x, world_y)
        
        # Last resort: spiral search from the original position
        # Convert to tile coordinates
        center_x = int(x // dungeon.tile_size)
        center_y = int(y // dungeon.tile_size)
        
        # Spiral pattern: right, down, left, up
        dx = [1, 0, -1, 0]
        dy = [0, 1, 0, -1]
        
        # Start from the center and spiral outward
        current_x = center_x
        current_y = center_y
        layer = 1
        max_layers = 100  # Significantly increased search radius
        
        while layer < max_layers:
            for direction in range(4):
                steps = layer if direction % 2 == 0 else layer
                
                for _ in range(steps):
                    current_x += dx[direction]
                    current_y += dy[direction]
                    
                    # Check bounds
                    if (0 <= current_x < len(dungeon.tiles[0]) and 
                        0 <= current_y < len(dungeon.tiles)):
                        # Convert back to world coordinates
                        world_x = current_x * dungeon.tile_size
                        world_y = current_y * dungeon.tile_size
                        
                        if self.is_walkable(dungeon_id, world_x, world_y):
                            logging.info(f"Found valid spawn point at ({world_x}, {world_y}) after spiral search")
                            return (world_x, world_y)
            
            layer += 1
        
        # If still no valid point found, search the entire dungeon grid as a last resort
        logging.warning(f"Spiral search failed, performing full grid search for dungeon {dungeon_id}")
        for y in range(len(dungeon.tiles)):
            for x in range(len(dungeon.tiles[0])):
                if dungeon.tiles[y][x] == 0:  # If it's a floor tile
                    world_x = x * dungeon.tile_size
                    world_y = y * dungeon.tile_size
                    logging.info(f"Found valid spawn point at ({world_x}, {world_y}) after full grid search")
                    return (world_x, world_y)
        
        # This should never happen if the dungeon has at least one floor tile
        logging.error(f"CRITICAL: No valid spawn point found in dungeon {dungeon_id}")
        return (int(x), int(y))
    
    def _spawn_wild_pokemon(self, rooms: List[Room], tile_size: int, floor: int) -> List[WildPokemon]:
        """Spawn wild Pokémon in random rooms"""
        wild_pokemon = []
        pokemon_id_counter = 0
        
        for room in rooms[1:]:  # Skip the first room (player spawn room)
            # Decide how many Pokémon to spawn in this room (0-2)
            num_pokemon = random.randint(0, 2)
            
            for _ in range(num_pokemon):
                pokemon_x = random.randint(room.x + 1, room.x + room.width - 2) * tile_size
                pokemon_y = random.randint(room.y + 1, room.y + room.height - 2) * tile_size
                
                # Base level range starts at 1-3 for floor 1
                # Each floor increases the level range by 1-2 levels
                min_level = max(1, floor)
                max_level = min_level + 2 + floor
                
                # Set a random level within the range
                level = random.randint(min_level, max_level)

                # Choose Pokémon type based on level
                if level < 22:
                    pokemon_name = "zubat"
                    max_hp = 40 + (level * 2)  # Simple HP calculation
                else:
                    pokemon_name = "golbat"
                    max_hp = 75 + (level * 3)  # Simple HP calculation
                
                # Select random moves
                available_moves = self._get_available_moves(pokemon_name, level)
                num_moves = min(4, len(available_moves))
                selected_moves = random.sample(available_moves, num_moves) if available_moves else ["tackle"]
                
                wild_pokemon.append(WildPokemon(
                    id=f"wild_{pokemon_id_counter}",
                    name=pokemon_name,
                    level=level,
                    current_hp=max_hp,
                    max_hp=max_hp,
                    position=[pokemon_x, pokemon_y],
                    moves=selected_moves
                ))
                
                pokemon_id_counter += 1
        
        return wild_pokemon
    
    def _get_available_moves(self, pokemon_name: str, level: int) -> List[str]:
        """Get available moves for a Pokémon at a given level"""
        # This is a simplified version - in a real implementation, you would load this from JSON files
        if pokemon_name == "zubat":
            if level < 5:
                return ["tackle", "leech-life"]
            elif level < 10:
                return ["tackle", "leech-life", "supersonic"]
            elif level < 15:
                return ["tackle", "leech-life", "supersonic", "bite"]
            else:
                return ["leech-life", "supersonic", "bite", "air-cutter"]
        elif pokemon_name == "golbat":
            return ["leech-life", "supersonic", "bite", "air-cutter", "poison-fang", "air-slash"]
        else:
            return ["tackle"]  # Default fallback