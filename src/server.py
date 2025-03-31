from flask import Flask, request
from flask_socketio import SocketIO, emit
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional
import logging
import uuid
from game.dungeon_manager import DungeonManager

# Configure logging
logging.basicConfig(level=logging.INFO)

@dataclass
class Player:
    id: str
    name: str  # Player's username
    x: float
    y: float
    pokemon: str  # Pokemon's name (not the player's name)
    direction_x: float = 1  # Default looking right
    direction_y: float = 0  # Default looking right
    dungeon_id: Optional[str] = None  # ID of the dungeon the player is in
    in_dungeon: bool = False  # Whether the player is in a dungeon or hub

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pokemon-dungeon-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store connected players
players: Dict[str, Player] = {}

# Initialize dungeon manager
dungeon_manager = DungeonManager()

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    # Remove player from the game
    player_id = None
    for pid, player in players.items():
        if player.id == request.sid:
            player_id = pid
            break
    
    if player_id:
        del players[player_id]
        emit('player_disconnected', {'player_id': player_id}, broadcast=True)

@socketio.on('player_join')
def handle_player_join(data):
    # Create new player with custom username
    new_player = Player(
        id=request.sid,
        name=data['name'],  # This will now be the custom username
        x=data['x'],
        y=data['y'],
        pokemon=data['pokemon'],
        direction_x=data.get('direction_x', 1),
        direction_y=data.get('direction_y', 0)
    )
    players[request.sid] = new_player
    
    # Log the new player joining
    logging.info(f"Player {new_player.name} joined with {new_player.pokemon}")
    
    # Send existing players to new player
    emit('players_state', {
        'players': [
            {
                'id': p.id,
                'name': p.name,
                'x': p.x,
                'y': p.y,
                'pokemon': p.pokemon,
                'direction_x': p.direction_x,
                'direction_y': p.direction_y
            } for p in players.values()
        ]
    })
    
    # Broadcast new player to all other players
    emit('player_joined', {
        'id': new_player.id,
        'name': new_player.name,
        'x': new_player.x,
        'y': new_player.y,
        'pokemon': new_player.pokemon,
        'direction_x': new_player.direction_x,
        'direction_y': new_player.direction_y
    }, broadcast=True, include_self=False)

@socketio.on('player_move')
def handle_player_move(data):
    try:
        player = players.get(request.sid)
        if player:
            new_x = data.get('x', player.x)
            new_y = data.get('y', player.y)
            new_direction_x = data.get('direction_x', player.direction_x)
            new_direction_y = data.get('direction_y', player.direction_y)
            
            # Check if movement is valid in dungeon
            valid_move = True
            if player.in_dungeon and player.dungeon_id:
                # Check if the move is valid in the dungeon
                valid_move = dungeon_manager.is_valid_move(
                    player.dungeon_id, 
                    new_x, 
                    new_y, 
                    50, # Player width - hardcoded for now
                    50  # Player height - hardcoded for now
                )
                
                # Update explored tiles in dungeon
                if valid_move:
                    dungeon_manager.update_explored(player.id, (new_x, new_y))
            
            if valid_move:
                # Update player position and direction
                player.x = new_x
                player.y = new_y
                player.direction_x = new_direction_x
                player.direction_y = new_direction_y
                
                # Broadcast the movement to all other players
                emit('player_moved', {
                    'id': player.id,
                    'x': player.x,
                    'y': player.y,
                    'direction_x': player.direction_x,
                    'direction_y': player.direction_y
                }, broadcast=True, include_self=False)
                
                #logging.info(f'Player {player.name} moved to position ({player.x}, {player.y})')
            else:
                # Send back the original position to the client
                emit('movement_rejected', {
                    'x': player.x,
                    'y': player.y
                }, room=request.sid)
        else:
            logging.warning(f'Player not found for session {request.sid}')
    except Exception as e:
        logging.error(f'Error handling player movement: {str(e)}')
        emit('error', {'message': 'Failed to update player position'}, room=request.sid)

@socketio.on('enter_dungeon')
def handle_enter_dungeon(data):
    try:
        player = players.get(request.sid)
        if player:
            # Create a new dungeon
            floor = data.get('floor', 1)
            dungeon_id = dungeon_manager.create_dungeon(2000, 2000, 50, floor)
            
            # Assign player to dungeon
            player.dungeon_id = dungeon_id
            player.in_dungeon = True
            dungeon_manager.assign_player_to_dungeon(player.id, dungeon_id)
            
            # Get spawn position and ensure it's valid
            spawn_x, spawn_y = dungeon_manager.get_player_spawn(dungeon_id)
            
            # Double-check that the spawn point is actually walkable
            if not dungeon_manager.is_walkable(dungeon_id, spawn_x, spawn_y):
                logging.warning(f"Spawn point ({spawn_x}, {spawn_y}) is not walkable! Finding alternative...")
                # Force a full search for a valid spawn point
                spawn_x, spawn_y = dungeon_manager._find_nearest_valid_spawn(dungeon_id, spawn_x, spawn_y)
                
                # Final validation check
                if not dungeon_manager.is_walkable(dungeon_id, spawn_x, spawn_y):
                    logging.error(f"CRITICAL: Still could not find valid spawn point in dungeon {dungeon_id}")
                    # Last resort: search the entire dungeon grid for any walkable tile
                    dungeon = dungeon_manager.dungeons[dungeon_id]
                    for y in range(len(dungeon.tiles)):
                        for x in range(len(dungeon.tiles[0])):
                            if dungeon.tiles[y][x] == 0:  # If it's a floor tile
                                spawn_x = x * dungeon.tile_size
                                spawn_y = y * dungeon.tile_size
                                break
                        if dungeon_manager.is_walkable(dungeon_id, spawn_x, spawn_y):
                            break
            
            # Update player position to the validated spawn point
            player.x = spawn_x
            player.y = spawn_y
            
            # Send dungeon data to player
            dungeon_state = dungeon_manager.get_dungeon_state(dungeon_id, player.id)
            # Add spawn point to dungeon state
            dungeon_state['spawn_point'] = (spawn_x, spawn_y)
            # Add room data for minimap functionality
            dungeon_state['rooms'] = [{
                'x': room.x,
                'y': room.y,
                'width': room.width,
                'height': room.height
            } for room in dungeon_manager.dungeons[dungeon_id].rooms]
            # Ensure enemy_projectiles is initialized
            if 'enemy_projectiles' not in dungeon_state:
                dungeon_state['enemy_projectiles'] = []
            emit('dungeon_state', {
                'dungeon_id': dungeon_id,
                'spawn_x': spawn_x,
                'spawn_y': spawn_y,
                'state': dungeon_state
            }, room=request.sid)
            
            logging.info(f'Player {player.name} entered dungeon {dungeon_id} at floor {floor} at position ({spawn_x}, {spawn_y})')
        else:
            logging.warning(f'Player not found for session {request.sid}')
    except Exception as e:
        logging.error(f'Error handling dungeon entry: {str(e)}')
        emit('error', {'message': 'Failed to enter dungeon'}, room=request.sid)

@socketio.on('exit_dungeon')
def handle_exit_dungeon():
    try:
        player = players.get(request.sid)
        if player and player.in_dungeon:
            player.in_dungeon = False
            player.dungeon_id = None
            
            # Reset player position to hub
            player.x = 500
            player.y = 500
            
            emit('exited_dungeon', {
                'x': player.x,
                'y': player.y
            }, room=request.sid)
            
            logging.info(f'Player {player.name} exited dungeon')
        else:
            logging.warning(f'Player not found or not in dungeon for session {request.sid}')
    except Exception as e:
        logging.error(f'Error handling dungeon exit: {str(e)}')
        emit('error', {'message': 'Failed to exit dungeon'}, room=request.sid)

@socketio.on('next_floor')
def handle_next_floor():
    try:
        player = players.get(request.sid)
        if player and player.in_dungeon and player.dungeon_id:
            # Get current dungeon info
            current_dungeon = dungeon_manager.dungeons.get(player.dungeon_id)
            if not current_dungeon:
                emit('error', {'message': 'Dungeon not found'}, room=request.sid)
                return
                
            # Create a new dungeon with increased floor
            new_floor = current_dungeon.floor + 1
            new_dungeon_id = dungeon_manager.create_dungeon(2000, 2000, 50, new_floor)
            
            # Assign player to new dungeon
            player.dungeon_id = new_dungeon_id
            dungeon_manager.assign_player_to_dungeon(player.id, new_dungeon_id)
            
            # Get spawn position and ensure it's valid
            spawn_x, spawn_y = dungeon_manager.get_player_spawn(new_dungeon_id)
            player.x = spawn_x
            player.y = spawn_y
            
            # Send new dungeon data to player
            dungeon_state = dungeon_manager.get_dungeon_state(new_dungeon_id, player.id)
            # Add spawn point to dungeon state
            dungeon_state['spawn_point'] = (spawn_x, spawn_y)
            # Add room data for minimap functionality
            dungeon_state['rooms'] = [{
                'x': room.x,
                'y': room.y,
                'width': room.width,
                'height': room.height
            } for room in dungeon_manager.dungeons[new_dungeon_id].rooms]
            emit('dungeon_state', {
                'dungeon_id': new_dungeon_id,
                'spawn_x': spawn_x,
                'spawn_y': spawn_y,
                'state': dungeon_state
            }, room=request.sid)
            
            logging.info(f'Player {player.name} advanced to floor {new_floor}')
        else:
            logging.warning(f'Player not found or not in dungeon for session {request.sid}')
    except Exception as e:
        logging.error(f'Error handling floor advancement: {str(e)}')
        emit('error', {'message': 'Failed to advance to next floor'}, room=request.sid)

@socketio.on('attack')
def handle_attack(data):
    try:
        player = players.get(request.sid)
        if player and player.in_dungeon and player.dungeon_id:
            # Process the attack
            attack_data = {
                'type': data.get('type', 'direct'),
                'position': (player.x, player.y),
                'direction': (player.direction_x, player.direction_y),
                'damage': data.get('damage', 10),
                'range': data.get('range', 50),
                'move_name': data.get('move_name', 'tackle')
            }
            
            # Handle the attack and get affected Pokémon
            affected_pokemon = dungeon_manager.handle_player_attack(
                player.dungeon_id, 
                player.id, 
                attack_data
            )
            
            # Send attack results to player
            emit('attack_results', {
                'affected_pokemon': affected_pokemon
            }, room=request.sid)
            
            # Update all players in the same dungeon about the state of wild Pokémon
            dungeon_players = [p for p in players.values() if p.dungeon_id == player.dungeon_id]
            for dungeon_player in dungeon_players:
                dungeon_state = dungeon_manager.get_dungeon_state(player.dungeon_id, dungeon_player.id)
                emit('dungeon_update', {
                    'wild_pokemon': dungeon_state['wild_pokemon']
                }, room=dungeon_player.id)
            
            logging.info(f'Player {player.name} attacked with {attack_data["move_name"]}')
        else:
            logging.warning(f'Player not found or not in dungeon for session {request.sid}')
    except Exception as e:
        logging.error(f'Error handling attack: {str(e)}')
        emit('error', {'message': 'Failed to process attack'}, room=request.sid)

@socketio.on('update_dungeon')
def handle_update_dungeon():
    try:
        player = players.get(request.sid)
        if player and player.in_dungeon and player.dungeon_id:
            # Get player positions in this dungeon
            dungeon_players = {p.id: (p.x, p.y) for p in players.values() if p.dungeon_id == player.dungeon_id}
            
            # Update wild Pokémon behavior
            dungeon_manager.update_wild_pokemon(player.dungeon_id, dungeon_players)
            
            # Send updated dungeon state to all players in this dungeon
            for dungeon_player in [p for p in players.values() if p.dungeon_id == player.dungeon_id]:
                dungeon_state = dungeon_manager.get_dungeon_state(player.dungeon_id, dungeon_player.id)
                emit('dungeon_update', {
                    'wild_pokemon': dungeon_state['wild_pokemon'],
                    'explored': dungeon_state['explored']
                }, room=dungeon_player.id)
        else:
            logging.warning(f'Player not found or not in dungeon for session {request.sid}')
    except Exception as e:
        logging.error(f'Error updating dungeon: {str(e)}')
        emit('error', {'message': 'Failed to update dungeon'}, room=request.sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)