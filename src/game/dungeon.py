import pygame
import random
import numpy as np
import math
from dataclasses import dataclass
from game.pokemon import Pokemon
from game.move_examples import tackle
from game.combat import calculate_damage
from utils.animation import SpriteAnimation

@dataclass
class Room:
    x: int
    y: int
    width: int
    height: int

class Dungeon:
    def __init__(self, width, height, tile_size, floor=1, dungeon_state=None):
        if dungeon_state:
            # Initialize from server state
            self.width = dungeon_state["width"]
            self.height = dungeon_state["height"]
            self.tile_size = dungeon_state["tile_size"]
            self.floor = dungeon_state["floor"]
            self.tiles = dungeon_state["tiles"]
            self.rooms = [Room(r.x, r.y, r.width, r.height) for r in dungeon_state.get("rooms", [])]
            self.ladder_position = dungeon_state["ladder_position"]
            self.enemy_projectiles = []
            self.wild_pokemon = []
            self.explored = dungeon_state.get("explored", [])
            self.is_multiplayer = True
        else:
            # Local generation for single player
            self.width = width
            self.height = height
            self.tile_size = tile_size
            self.floor = floor
            self.tiles, self.rooms = self._generate_dungeon()
            self.ladder_position = self._place_ladder()
            self.enemy_projectiles = []
            self.wild_pokemon = []
            # Initialize all tiles as explored for single player to fix visibility issue
            self.explored = [[True for _ in range(width // tile_size)] for _ in range(height // tile_size)]
            self.is_multiplayer = False

    def _generate_dungeon(self):
        # Initialize tiles array with walls (1)
        width_tiles = self.width // self.tile_size
        height_tiles = self.height // self.tile_size
        tiles = [[1 for _ in range(width_tiles)] for _ in range(height_tiles)]
        
        # Store rooms for spawn point and ladder placement
        self.rooms = []
        
        # Generate rooms with proper spacing
        rooms = []
        num_rooms = random.randint(8, 15)  # Number of rooms to attempt to create
        
        for _ in range(num_rooms):
            for attempt in range(5):  # Try up to 5 times to place each room
                room_width = random.randint(4, 8)
                room_height = random.randint(4, 8)
                # Leave 1-tile spacing around the edges
                x = random.randint(1, width_tiles - room_width - 2)
                y = random.randint(1, height_tiles - room_height - 2)
                
                # Check if the room overlaps with existing rooms or is too close (less than 1 tile apart)
                overlaps = False
                for room in rooms:
                    if (
                        x - 1 < room.x + room.width and
                        x + room_width + 1 > room.x and
                        y - 1 < room.y + room.height and
                        y + room_height + 1 > room.y
                    ):
                        overlaps = True
                        break
                
                if not overlaps:
                    # Room placement is valid, create it
                    new_room = Room(x, y, room_width, room_height)
                    rooms.append(new_room)
                    
                    # Carve out the room in the grid
                    for i in range(y, y + room_height):
                        for j in range(x, x + room_width):
                            tiles[i][j] = 0  # Floor
                    break  # Exit the retry loop if room placed successfully
        
        # Connect rooms with corridors using a better path generation algorithm
        for i in range(len(rooms)-1):
            room1 = rooms[i]
            room2 = rooms[i+1]
            # Use center points of rooms
            x1 = room1.x + room1.width // 2
            y1 = room1.y + room1.height // 2
            x2 = room2.x + room2.width // 2
            y2 = room2.y + room2.height // 2
            
            # Randomly decide whether to go horizontal first or vertical first
            if random.random() < 0.5:
                # Horizontal corridor first, then vertical
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    tiles[y1][x] = 0
                
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    tiles[y][x2] = 0
            else:
                # Vertical corridor first, then horizontal
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    tiles[y][x1] = 0
                
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    tiles[y2][x] = 0
        
        self.rooms = rooms
        return tiles, rooms

    def _place_ladder(self):
        # For multiplayer, use a random valid position
        if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
            # Find a random walkable tile
            width_tiles = self.width // self.tile_size
            height_tiles = self.height // self.tile_size
            valid_positions = []
            for y in range(height_tiles):
                for x in range(width_tiles):
                    if self.tiles[y][x] == 0:  # If it's a floor tile
                        valid_positions.append((x, y))
            if valid_positions:
                x, y = random.choice(valid_positions)
                return (x * self.tile_size, y * self.tile_size)
        
        # For single player, place in the last room (farthest from spawn)
        if self.rooms and len(self.rooms) > 1:
            # Skip the first room (player spawn) and use the last room
            last_room = self.rooms[-1]
            
            # Try to place ladder in center of last room
            center_x = last_room.x + last_room.width // 2
            center_y = last_room.y + last_room.height // 2
            
            # Verify the center is walkable
            if self.is_walkable(center_x * self.tile_size, center_y * self.tile_size):
                return (center_x * self.tile_size, center_y * self.tile_size)
            
            # If center is not walkable, find a valid position in the room
            for y in range(last_room.y, last_room.y + last_room.height):
                for x in range(last_room.x, last_room.x + last_room.width):
                    if self.tiles[y][x] == 0:  # If it's a floor tile
                        return (x * self.tile_size, y * self.tile_size)
        
        # If no rooms or couldn't find valid position in last room, try any room except the first
        if self.rooms and len(self.rooms) > 1:
            for room in self.rooms[1:]:  # Skip the first room
                for y in range(room.y, room.y + room.height):
                    for x in range(room.x, room.x + room.width):
                        if self.tiles[y][x] == 0:  # If it's a floor tile
                            return (x * self.tile_size, y * self.tile_size)
        
        # Final fallback: find any walkable tile
        width_tiles = self.width // self.tile_size
        height_tiles = self.height // self.tile_size
        valid_positions = []
        for y in range(height_tiles):
            for x in range(width_tiles):
                if self.tiles[y][x] == 0:  # If it's a floor tile
                    valid_positions.append((x, y))
        
        if valid_positions:
            x, y = random.choice(valid_positions)
            return (x * self.tile_size, y * self.tile_size)
        
        # Absolute last resort: random position
        x = random.randint(0, width_tiles - 1)
        y = random.randint(0, height_tiles - 1)
        return (x * self.tile_size, y * self.tile_size)

    def update_from_server_state(self, dungeon_state):
        """Update the dungeon state from server data"""
        self.tiles = dungeon_state["tiles"]
        self.ladder_position = dungeon_state["ladder_position"]
        self.explored = dungeon_state.get("explored", [])
        
        # Update rooms data for minimap functionality
        if "rooms" in dungeon_state:
            self.rooms = [Room(r["x"], r["y"], r["width"], r["height"]) for r in dungeon_state["rooms"]]
        
        # Update wild Pokémon from server state
        self.wild_pokemon = []
        for pokemon_data in dungeon_state.get("wild_pokemon", []):
            pokemon = Pokemon.from_json(pokemon_data["name"].lower())
            pokemon.level = pokemon_data["level"]
            pokemon.current_hp = pokemon_data["current_hp"]
            pokemon.stats["HP"] = pokemon_data["max_hp"]
            
            self.wild_pokemon.append({
                "pokemon": pokemon,
                "position": pokemon_data["position"],
                "animation_state": pokemon_data["animation_state"],
                "animation": SpriteAnimation(pokemon.name, pokemon_data["animation_state"])
            })

    def is_tile_explored(self, grid_x, grid_y):
        """Check if a tile has been explored by the player"""
        if not self.explored:
            return True  # If no exploration data, show everything
        if 0 <= grid_y < len(self.explored) and 0 <= grid_x < len(self.explored[0]):
            return self.explored[grid_y][grid_x]
        return False
        
    def update_explored(self, player_position):
        """Update the explored tiles around the player's position"""
        # For single player, we've already set all tiles to explored in __init__
        # This is just a placeholder method to satisfy the call in main.py
        pass

    def is_walkable(self, x, y):
        # Convert x and y to integers to avoid TypeError
        grid_x = int(x // self.tile_size)
        grid_y = int(y // self.tile_size)
        if 0 <= grid_x < len(self.tiles[0]) and 0 <= grid_y < len(self.tiles):
            return self.tiles[grid_y][grid_x] == 0
        return False
        
    def get_spawn_point(self):
        """Get a safe spawn point for the player"""
        if self.is_multiplayer:
            # In multiplayer, use the spawn point from server
            return None
            
        # In single player, spawn in the first room
        if self.rooms:
            first_room = self.rooms[0]
            # Try center of first room
            center_x = (first_room.x + first_room.width // 2) * self.tile_size
            center_y = (first_room.y + first_room.height // 2) * self.tile_size
            
            if self.is_walkable(center_x, center_y):
                return center_x, center_y
            
            # If center is not walkable, try other positions in the room
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    test_x = center_x + (dx * self.tile_size)
                    test_y = center_y + (dy * self.tile_size)
                    if self.is_walkable(test_x, test_y):
                        return test_x, test_y
            
            # If no walkable spot found, search the entire first room systematically
            for ry in range(first_room.y, first_room.y + first_room.height):
                for rx in range(first_room.x, first_room.x + first_room.width):
                    world_x = rx * self.tile_size
                    world_y = ry * self.tile_size
                    if self.is_walkable(world_x, world_y):
                        return world_x, world_y
                
            # If still no walkable spot found, find nearest valid spawn using spiral search
            return self.find_nearest_valid_spawn(center_x, center_y)
                        
        raise ValueError("No walkable spawn point found in dungeon")

    def find_nearest_valid_spawn(self, x, y):
        """Find the nearest valid (walkable) spawn point using a spiral search pattern."""
        # Convert to tile coordinates
        center_x = int(x // self.tile_size)
        center_y = int(y // self.tile_size)
        
        # Spiral pattern: right, down, left, up
        dx = [1, 0, -1, 0]
        dy = [0, 1, 0, -1]
        
        # Start from the center and spiral outward
        current_x = center_x
        current_y = center_y
        layer = 1
        
        # Check the center point first
        world_x = center_x * self.tile_size
        world_y = center_y * self.tile_size
        if self.is_walkable(world_x, world_y):
            return (world_x, world_y)
        
        # Spiral outward to find a valid spawn point
        while layer < 50:  # Increased search radius to ensure finding a valid point
            for direction in range(4):
                steps = layer if direction % 2 == 0 else layer
                
                for _ in range(steps):
                    current_x += dx[direction]
                    current_y += dy[direction]
                    
                    # Check bounds
                    if (0 <= current_x < len(self.tiles[0]) and 
                        0 <= current_y < len(self.tiles)):
                        # Convert back to world coordinates
                        world_x = current_x * self.tile_size
                        world_y = current_y * self.tile_size
                        
                        if self.is_walkable(world_x, world_y):
                            print(f"Found valid spawn point at ({world_x}, {world_y})")
                            return (world_x, world_y)
            
            layer += 1
        
        # If no valid point found, try a more aggressive approach - check every tile
        print("Spiral search failed, checking all tiles")
        for y_idx in range(len(self.tiles)):
            for x_idx in range(len(self.tiles[0])):
                if self.tiles[y_idx][x_idx] == 0:  # If it's a floor tile
                    world_x = x_idx * self.tile_size
                    world_y = y_idx * self.tile_size
                    print(f"Found valid spawn point at ({world_x}, {world_y})")
                    return (world_x, world_y)
        
        # If still no valid point found, return original coordinates (shouldn't happen)
        print("WARNING: No valid spawn point found in entire dungeon!")
        return (x, y)
        
    def is_valid_move(self, rect):
        """
        Check if a move is valid by checking all four corners of the rectangle.
        :param rect: The pygame.Rect to check.
        :return: True if the move is valid, False otherwise.
        """
        # Check all four corners of the rectangle
        corners = [
            (rect.left, rect.top),     # Top-left
            (rect.right, rect.top),    # Top-right
            (rect.left, rect.bottom),  # Bottom-left
            (rect.right, rect.bottom)  # Bottom-right
        ]
        
        # Check if all corners are walkable
        for corner in corners:
            if not self.is_walkable(corner[0], corner[1]):
                return False
                
        return True



    def display_minimap(self, screen, minimap_size, player_position, position=(10, 10)):
        """
        Draws the minimap on the screen, including the player's position as a dot.
        Only shows explored areas with fog of war for unexplored regions.
        :param screen: The Pygame screen to draw on.
        :param minimap_size: The size of the minimap in pixels.
        :param player_position: The player's position in the dungeon.
        :param position: The (x, y) position to draw the minimap on the screen.
        """
        minimap_tile_size = minimap_size // len(self.tiles)  # Scale the minimap to fit
        offset_x, offset_y = position  # Position of the minimap on the screen

        # Draw all tiles with fog of war
        for y, row in enumerate(self.tiles):
            for x, tile in enumerate(row):
                if self.is_tile_explored(x, y):
                    # Show explored tiles
                    color = (200, 200, 200) if tile == 0 else (50, 50, 50)  # Gray for floors, dark gray for walls
                else:
                    # Dark fog for unexplored areas
                    color = (20, 20, 20)
                pygame.draw.rect(
                    screen,
                    color,
                    pygame.Rect(offset_x + x * minimap_tile_size, offset_y + y * minimap_tile_size, minimap_tile_size, minimap_tile_size)
                )
        
        # Draw the ladder on the minimap only if it's in an explored area
        ladder_grid_x = self.ladder_position[0] // self.tile_size
        ladder_grid_y = self.ladder_position[1] // self.tile_size
        if (0 <= ladder_grid_x < len(self.tiles[0]) and 
            0 <= ladder_grid_y < len(self.tiles) and 
            self.is_tile_explored(ladder_grid_x, ladder_grid_y)):
            ladder_minimap_x = offset_x + ladder_grid_x * minimap_tile_size
            ladder_minimap_y = offset_y + ladder_grid_y * minimap_tile_size
            pygame.draw.rect(
                screen,
                (255, 215, 0),  # Gold color for the ladder (same as in the main display)
                pygame.Rect(ladder_minimap_x, ladder_minimap_y, minimap_tile_size, minimap_tile_size)
            )

        # Draw the player's position as a dot on the minimap
        player_minimap_x = offset_x + (player_position[0] / self.tile_size) * minimap_tile_size
        player_minimap_y = offset_y + (player_position[1] / self.tile_size) * minimap_tile_size
        pygame.draw.circle(
            screen,
            (255, 0, 0),  # Red color for the player dot
            (int(player_minimap_x), int(player_minimap_y)),  # Position of the dot
            max(2, minimap_tile_size // 4)  # Radius of the dot (scaled to minimap size)
        )

    def spawn_wild_pokemon(self):
        """
        Spawn wild Pokémon in random rooms with levels that scale with dungeon floor.
        """
        
        wild_pokemon = []
        for room in self.rooms[1:]:  # Skip the first room (player spawn room)
            pokemon_x = random.randint(room[0] + 1, room[0] + room[2] - 2) * self.tile_size
            pokemon_y = random.randint(room[1] + 1, room[1] + room[3] - 2) * self.tile_size
            
            # Base level range starts at 1-3 for floor 1
            # Each floor increases the level range by 1-2 levels
            min_level = max(1, self.floor)
            max_level = min_level + 2 + self.floor
            
            # Set a random level within the range
            level = random.randint(min_level, max_level)

            # Create the Pokémon with a random level that scales with floor number
            if level < 22:
                pokemon = Pokemon.from_json("zubat")
            else:
                pokemon = Pokemon.from_json("golbat")

            pokemon.level = level

            # Load learnable moves from JSON
            if level < 22:
                pokemon.add_learnable_moves_from_json("zubat")
            else:
                pokemon.add_learnable_moves_from_json("golbat")
            
            # Assign random moves that can be learned at or below the current level
            available_moves = []
            for level_str, moves in pokemon.learnable_moves.items():
                if int(level_str) <= pokemon.level:
                    available_moves.extend(moves)
            
            # Select up to 4 random moves from available moves
            if available_moves:
                num_moves = min(4, len(available_moves))
                selected_move_names = random.sample(available_moves, num_moves)
                
                # Load the selected moves
                from game.move import Move
                for move_name in selected_move_names:
                    try:
                        move = Move.from_json(move_name.lower().replace(" ", "-"))
                        pokemon.current_moves.append(move)
                    except FileNotFoundError:
                        print(f"Could not find move data for {move_name}")
            
            # Recalculate stats based on the new level
            pokemon.stats = pokemon.calculate_stats()
            pokemon.current_hp = pokemon.stats["HP"]  # Set current HP to max HP
            
            wild_pokemon.append({
                "pokemon": pokemon,
                "position": [pokemon_x, pokemon_y],
                "cooldown": 0,  # Cooldown timer for attacks
                "animation_state": "Idle",  # Track animation state separately from the actual animation
                "animation": SpriteAnimation(pokemon.name, "Idle")#, sprite_offset=(-40, 0))  # Create animation object for wild Pokemon
            })
        return wild_pokemon

    def update_wild_pokemon(self, player):
        """
        Update the behavior of wild Pokémon (movement and attacks).
        """
        for wild in self.wild_pokemon:
            # Get the enemy's collision rectangle
            wild_rect = get_enemy_collision_rect(wild["position"], self.tile_size)
            # Get the player's collision rectangle
            player_rect = player.get_collision_rect()

            # Add a speed attribute to control movement speed
            speed = 2  # Slow down enemy movement (default is 2 pixels per frame)
            
            # Calculate HP percentage to determine if the Pokémon should retreat
            hp_percentage = wild["pokemon"].current_hp / wild["pokemon"].stats["HP"]
            is_retreating = hp_percentage < 0.3  # Retreat when HP is below 30%
            
            # Initialize moved variable in the wild Pokémon's dictionary if it doesn't exist
            if "moved" not in wild:
                wild["moved"] = False
            
            # Reset moved state at the start of each update
            wild["moved"] = False
            
            # Initialize last_direction if it doesn't exist
            if "last_direction" not in wild:
                wild["last_direction"] = (0, 0)
            
            # Check line of sight (LOS) using the center of the enemy and player
            enemy_center = (wild["position"][0] + (self.tile_size * 0.6)/2, wild["position"][1] + (self.tile_size * 0.6)/2)
            player_center = (player.position[0] + player.size[0] // 2, player.position[1] + player.size[1] // 2)
            
            # Calculate direction to/from player regardless of line of sight
            dx = player.position[0] - wild["position"][0]
            dy = player.position[1] - wild["position"][1]
            
            # Normalize the direction vector
            magnitude = (dx ** 2 + dy ** 2) ** 0.5
            if magnitude != 0:
                dx = (dx / magnitude) * speed
                dy = (dy / magnitude) * speed
                
                # If retreating, reverse the direction
                if is_retreating:
                    dx = -dx
                    dy = -dy
                    
                # Store the normalized direction for animation
                wild["last_direction"] = (dx/speed, dy/speed)
            
            # Initialize wandering state and timer if they don't exist
            if "wander_timer" not in wild:
                wild["wander_timer"] = 0
                wild["wander_direction"] = (0, 0)
            
            # Update wander timer
            wild["wander_timer"] = max(0, wild["wander_timer"] - 1)
            
            # Check if we have line of sight to the player
            has_los = self.has_line_of_sight(enemy_center, player_center)
            
            # Handle wandering behavior when no line of sight
            if not has_los:
                # Choose new random direction when timer expires
                if wild["wander_timer"] == 0:
                    angle = random.uniform(0, 2 * math.pi)
                    wild["wander_direction"] = (math.cos(angle), math.sin(angle))
                    wild["wander_timer"] = random.randint(30, 90)  # Random duration between direction changes
                
                # Apply wandering movement
                wander_dx = wild["wander_direction"][0] * speed
                wander_dy = wild["wander_direction"][1] * speed
                
                # Try to move in the wandering direction
                new_rect = wild_rect.move(wander_dx, wander_dy)
                if self.is_valid_move(new_rect):
                    wild["position"][0] += wander_dx
                    wild["position"][1] += wander_dy
                    wild["moved"] = True
                    wild["last_direction"] = (wander_dx/speed, wander_dy/speed)
                else:
                    # If blocked, reset timer to choose new direction next frame
                    wild["wander_timer"] = 0
                
                # Set animation to Walk when moving
                if wild["moved"] and wild["animation_state"] != "Walk" and wild["cooldown"] == 0:
                    wild["animation"].set_animation("Walk")
                    wild["animation_state"] = "Walk"
            
            # Chase or flee if there's line of sight
            if has_los:
                # Try multiple movement options in order of preference
                moved = False
                
                # 1. Try diagonal movement first (most direct path)
                new_rect_diag = wild_rect.move(dx, dy)
                if self.is_valid_move(new_rect_diag):
                    wild["position"][0] += dx
                    wild["position"][1] += dy
                    wild["moved"] = True
                    
                    # Set animation to Walk when moving
                    if wild["animation_state"] != "Walk" and wild["cooldown"] == 0:
                        wild["pokemon"].animation.set_animation("Walk")
                        wild["animation_state"] = "Walk"
                
                if not wild["moved"]:
                    # 2. Try horizontal movement
                    new_rect_x = wild_rect.move(dx, 0)
                    if self.is_valid_move(new_rect_x):
                        wild["position"][0] += dx
                        wild["moved"] = True
                    
                    # 3. Try vertical movement
                    new_rect_y = wild_rect.move(0, dy)
                    if self.is_valid_move(new_rect_y):
                        wild["position"][1] += dy
                        wild["moved"] = True
                
                if not wild["moved"]:
                    # 4. Try perpendicular movement to avoid obstacles
                    for perpendicular in [(dy, -dx), (-dy, dx)]:
                        alt_dx, alt_dy = perpendicular
                        alt_rect = wild_rect.move(alt_dx, alt_dy)
                        if self.is_valid_move(alt_rect):
                            wild["position"][0] += alt_dx
                            wild["position"][1] += alt_dy
                            wild["moved"] = True
                            break
                    
                    # 5. If still stuck, try small random movements
                    if not wild["moved"]:
                        for _ in range(8):  # Try 8 different directions
                            rand_dx = random.uniform(-1, 1) * speed
                            rand_dy = random.uniform(-1, 1) * speed
                            rand_rect = wild_rect.move(rand_dx, rand_dy)
                            if self.is_valid_move(rand_rect):
                                wild["position"][0] += rand_dx
                                wild["position"][1] += rand_dy
                                wild["moved"] = True
                                break

            # Attack the player if in range or has line of sight
            attack_range = 200  # Range for ranged attacks in pixels
            distance_to_player = ((player_center[0] - enemy_center[0])**2 + (player_center[1] - enemy_center[1])**2)**0.5
            
            if wild["cooldown"] == 0 and (wild_rect.colliderect(player_rect) or (has_los and distance_to_player < attack_range)):
                # Select a move to use
                if wild["pokemon"].current_moves:
                    # Analyze battle situation
                    player_hp_percent = player.pokemon.current_hp / player.pokemon.stats["HP"] * 100
                    wild_hp_percent = wild["pokemon"].current_hp / wild["pokemon"].stats["HP"] * 100
                    
                    # Filter moves by category
                    status_moves = [m for m in wild["pokemon"].current_moves if m.category == "Status"]
                    damage_moves = [m for m in wild["pokemon"].current_moves if m.category != "Status"]
                    
                    # Choose move based on battle situation
                    if status_moves and (
                        # Use status moves more often when:
                        (wild_hp_percent > 70 and random.random() < 0.4) or  # Healthy enemy
                        (player_hp_percent < 30 and random.random() < 0.3) or  # Low player HP
                        (wild_hp_percent < 30 and random.random() < 0.2)  # Low enemy HP
                    ):
                        move = random.choice(status_moves)
                    elif damage_moves:
                        move = random.choice(damage_moves)
                    else:
                        move = random.choice(wild["pokemon"].current_moves)

                    # Handle different move types
                    if move.category == "Status":
                        # Status moves can be used at any range if there's line of sight
                        if has_los:
                            damage = calculate_damage(wild["pokemon"], player.pokemon, move)
                            print(f"{wild['pokemon'].name} used {move.name}!")
                            wild["cooldown"] = 90  # Longer cooldown for status moves
                    elif move.range_type == "Melee" and wild_rect.colliderect(player_rect):
                        # Melee attack - only if in direct contact
                        damage = calculate_damage(wild["pokemon"], player.pokemon, move)
                        player.pokemon.take_damage(damage)
                        print(f"{wild['pokemon'].name} used {move.name} and dealt {damage} damage to {player.pokemon.name}!")
                        wild["cooldown"] = 30  # 0.5 seconds at 60 FPS

                    elif move.range_type == "Ranged" and has_los:
                        # Ranged attack - can be used at a distance if there's line of sight
                        dx = player_center[0] - enemy_center[0]
                        dy = player_center[1] - enemy_center[1]
                        magnitude = (dx**2 + dy**2)**0.5
                        if magnitude > 0:
                            dx /= magnitude
                            dy /= magnitude
                        
                        # Create a projectile
                        from game.move import Projectile
                        self.enemy_projectiles.append(Projectile(enemy_center, (dx, dy), 8, move, wild["pokemon"]))
                        print(f"{wild['pokemon'].name} used {move.name}!")
                        wild["cooldown"] = 60  # 1 second at 60 FPS
                    
                    # Set cooldown based on move type (ranged attacks have longer cooldown)
                    if move.range_type == "Ranged":
                        wild["cooldown"] = 180  # 3 seconds at 60 FPS
                    else:
                        wild["cooldown"] = 120  # 2 seconds at 60 FPS
                else:
                    # Fallback to a basic attack if no moves are available
                    if wild_rect.colliderect(player_rect):
                        # Create a basic tackle move
                        from game.move import Move
                        tackle = Move("Tackle", "Normal", 40, 100, "Melee", "Physical")
                        
                        damage = calculate_damage(wild["pokemon"], player.pokemon, tackle)
                        player.pokemon.take_damage(damage)
                        print(f"{wild['pokemon'].name} used Tackle and dealt {damage} damage to {player.pokemon.name}!")
                        wild["cooldown"] = 120  # Cooldown in frames (e.g., 2 seconds at 60 FPS)
                        
                        # Set animation state to Attack
                        #wild["pokemon"].animation.set_animation("Attack")
                        #wild["animation_state"] = "Attack"
            elif wild["cooldown"] > 0:
                # Reduce cooldown
                wild["cooldown"] -= 1
                
            # Update animation based on movement
            if wild["moved"] and wild["animation_state"] != "Walk" and wild["cooldown"] == 0:
                wild["pokemon"].animation.set_animation("Walk")
                wild["animation_state"] = "Walk"
            elif not wild["moved"] and wild["animation_state"] == "Walk" and wild["cooldown"] == 0:
                wild["pokemon"].animation.set_animation("Idle")
                wild["animation_state"] = "Idle"

    def has_line_of_sight(self, start, end):
        """
        Check if there is a clear line of sight (LOS) between two points.
        :param start: The starting position (x, y) of the enemy (center of the sprite).
        :param end: The ending position (x, y) of the player (center of the sprite).
        :return: True if there is a clear LOS, False otherwise.
        """
        # Convert start and end to grid coordinates
        x1, y1 = int(start[0] // self.tile_size), int(start[1] // self.tile_size)
        x2, y2 = int(end[0] // self.tile_size), int(end[1] // self.tile_size)
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            if not (0 <= x1 < len(self.tiles[0]) and 0 <= y1 < len(self.tiles)):
                return False  # Out of bounds
            if self.tiles[y1][x1] == 1:  # Wall tile
                return False
            if (x1, y1) == (x2, y2):
                return True  # Reached the target
            e2 = err * 2
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def display_hp_bar(self, screen, position, current_hp, max_hp, bar_width, bar_height):
        """
        Draw an HP bar above a Pokémon.
        :param screen: The Pygame screen to draw on.
        :param position: The (x, y) position of the Pokémon.
        :param current_hp: The current HP of the Pokémon.
        :param max_hp: The maximum HP of the Pokémon.
        :param bar_width: The width of the HP bar.
        :param bar_height: The height of the HP bar.
        """
        x, y = position
        hp_ratio = current_hp / max_hp
        hp_color = (255, 0, 0) if hp_ratio < 0.3 else (255, 255, 0) if hp_ratio < 0.7 else (0, 255, 0)

        # Draw the background of the HP bar
        pygame.draw.rect(screen, (50, 50, 50), (x, y - bar_height - 5, bar_width, bar_height))
        # Draw the current HP
        pygame.draw.rect(screen, hp_color, (x, y - bar_height - 5, int(bar_width * hp_ratio), bar_height))
        
        # Draw the HP text
        font = pygame.font.Font(None, 14)  # Smaller font for enemy HP
        hp_text = font.render(f"{current_hp}/{max_hp}", True, (255, 255, 255))
        screen.blit(hp_text, (x, y - bar_height - 20))  # Position above the HP bar

    def display(self, screen, camera):
        # Draw the dungeon relative to the camera
        # Only process tiles that are potentially visible on screen to improve performance
        start_x = max(0, int(camera.offset_x // self.tile_size))
        end_x = min(len(self.tiles[0]), int((camera.offset_x + screen.get_width()) // self.tile_size) + 1)
        start_y = max(0, int(camera.offset_y // self.tile_size))
        end_y = min(len(self.tiles), int((camera.offset_y + screen.get_height()) // self.tile_size) + 1)
        
        # Draw only the visible portion of the dungeon
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                # Make sure we're within bounds
                if y < len(self.tiles) and x < len(self.tiles[0]):
                    tile = self.tiles[y][x]
                    
                    # Use high contrast colors for better visibility
                    color = (50, 50, 50) if tile == 1 else (200, 200, 200)  # Dark gray for walls, light gray for floors
                    
                    # Draw the tile - always render regardless of exploration status
                    screen_x = x * self.tile_size - camera.offset_x
                    screen_y = y * self.tile_size - camera.offset_y
                    pygame.draw.rect(
                        screen,
                        color,
                        pygame.Rect(screen_x, screen_y, self.tile_size, self.tile_size)
                    )
        
        # Draw enemy projectiles
        for projectile in self.enemy_projectiles:
            projectile.draw(screen, camera)

        # Draw the ladder only if it's on screen
        ladder_screen_x = self.ladder_position[0] - camera.offset_x
        ladder_screen_y = self.ladder_position[1] - camera.offset_y
        if -self.tile_size <= ladder_screen_x <= screen.get_width() and -self.tile_size <= ladder_screen_y <= screen.get_height():
            pygame.draw.rect(
                screen,
                (255, 215, 0),  # Gold color for the ladder
                pygame.Rect(ladder_screen_x, ladder_screen_y, self.tile_size, self.tile_size)
            )

        # Draw wild Pokémon with animations
        for wild in self.wild_pokemon:
            # Get the collision rectangle for the enemy
            wild_rect = get_enemy_collision_rect(wild["position"], self.tile_size)

            # Adjust the rectangle for the camera offset
            screen_rect = wild_rect.move(-camera.offset_x, -camera.offset_y)
            
            # Calculate direction vector based on movement
            if "last_direction" in wild:
                wild["pokemon"].animation.set_direction(wild["last_direction"])
            
            # Update animation state based on movement
            if "moved" in wild and wild["moved"] and wild["animation_state"] != "Walk":
                wild["pokemon"].animation.set_animation("Walk")
                wild["animation_state"] = "Walk"
            elif ("moved" not in wild or not wild["moved"]) and wild["animation_state"] != "Idle":
                wild["pokemon"].animation.set_animation("Idle")
                wild["animation_state"] = "Idle"
                
            # Update the animation
            wild["pokemon"].animation.update()
            
            # Get the current frame with a larger scale factor (2.5) for enemy sprites
            current_frame = wild["pokemon"].animation.get_current_frame(scale_factor=2)
            
            if current_frame:
                # Get the collision rectangle size
                collision_size = (wild_rect.width, wild_rect.height)
                
                # Use the sprite offset if available, otherwise use default centering
                #if hasattr(wild["pokemon"].animation, 'sprite_offset'):
                #    offset_x, offset_y = wild["pokemon"].animation.sprite_offset
                #else:
                    # Calculate offset to center the sprite on the collision box
                offset_x, offset_y = wild["animation"].sprite_offset[0], wild["animation"].sprite_offset[1]
                
                # Adjust position to center the larger sprite
                screen_rect = screen_rect.move(-offset_x, -offset_y)
                screen.blit(current_frame, screen_rect)
                
                # Uncomment to debug collision box
                # pygame.draw.rect(screen, (255, 0, 0), screen_rect, 1)
            else:
                # Fallback to rectangle if animation failed
                pygame.draw.rect(
                    screen,
                    (0, 0, 255),  # Blue color for wild Pokémon
                    screen_rect
                )

            # Draw HP bar
            self.display_hp_bar(
                screen,
                (screen_rect.x, screen_rect.y),
                wild["pokemon"].current_hp,
                wild["pokemon"].stats["HP"],
                bar_width=screen_rect.width,
                bar_height=5
            )

    def display_floor_count(self, screen):
        """
        Display the current floor count on the screen.
        """
        font = pygame.font.Font(None, 36)
        floor_text = font.render(f"Floor: {self.floor}", True, (255, 255, 255))
        screen.blit(floor_text, (10, 80))  # Display near the top-left corner with more space for level display

def get_enemy_collision_rect(enemy_position, tile_size):
    """
    Get the enemy's collision rectangle, centered on its position.
    :param enemy_position: The top-left position of the enemy as (x, y).
    :param tile_size: The size of the tile (used as a reference for scaling).
    :return: A pygame.Rect representing the enemy's collision rectangle.
    """
    collision_size = tile_size * 0.6  # Reduce the size to 60% of the tile size
    offset = 0  # (tile_size - collision_size) / 2  # Center the smaller rectangle
    return pygame.Rect(
        int(enemy_position[0] + offset),  # Offset to center the collider horizontally
        int(enemy_position[1] + offset),  # Offset to center the collider vertically
        int(collision_size),              # Width of the collider
        int(collision_size)               # Height of the collider
    )