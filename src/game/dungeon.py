import pygame
import random
import numpy as np
import math
from game.pokemon import Pokemon
from game.move_examples import tackle
from game.combat import calculate_damage
from utils.animation import SpriteAnimation

class Dungeon:
    def __init__(self, width, height, tile_size, floor=1):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.floor = floor  # Track the current floor
        self.tiles, self.rooms = self.generate_dungeon()  # Generate tiles and store rooms
        self.explored = [[False for _ in range(self.width // self.tile_size)] for _ in range(self.height // self.tile_size)]  # Track explored tiles
        self.ladder_position = self.place_ladder()  # Place the ladder in a random room
        self.enemy_projectiles = []  # List of projectiles fired by wild Pokémon
        
        self.wild_pokemon = self.spawn_wild_pokemon()  # Spawn wild Pokémon

    def generate_dungeon(self):
        # Initialize the dungeon grid with walls (1)
        tiles = [[1 for _ in range(self.width // self.tile_size)] for _ in range(self.height // self.tile_size)]

        # Generate random rooms with spacing
        num_rooms = random.randint(8, 15)  # Number of rooms
        rooms = []
        for _ in range(num_rooms):
            for attempt in range(5):  # Try up to 5 times to place the room
                room_width = random.randint(3, 8)  # Room width in tiles
                room_height = random.randint(3, 8)  # Room height in tiles
                room_x = random.randint(1, (self.width // self.tile_size) - room_width - 2)  # Leave 1-tile spacing
                room_y = random.randint(1, (self.height // self.tile_size) - room_height - 2)  # Leave 1-tile spacing

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

    def place_ladder(self):
        """
        Place the ladder in a random room.
        """
        random_room = random.choice(self.rooms)
        ladder_x = random.randint(random_room[0] + 1, random_room[0] + random_room[2] - 2) * self.tile_size
        ladder_y = random.randint(random_room[1] + 1, random_room[1] + random_room[3] - 2) * self.tile_size
        return ladder_x, ladder_y

    def get_player_spawn(self):
        # Choose the center of the first room as the spawn point
        first_room = self.rooms[0]
        spawn_x = (first_room[0] + first_room[2] // 2) * self.tile_size
        spawn_y = (first_room[1] + first_room[3] // 2) * self.tile_size
        return spawn_x, spawn_y

    def is_walkable(self, x, y):
        # Convert x and y to integers to avoid TypeError
        grid_x = int(x // self.tile_size)
        grid_y = int(y // self.tile_size)
        if 0 <= grid_x < len(self.tiles[0]) and 0 <= grid_y < len(self.tiles):
            return self.tiles[grid_y][grid_x] == 0
        return False
        
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

    def update_explored(self, player_position):
        """
        Mark the tile the player is currently on as explored.
        If the player enters a room, mark the entire room as explored.
        """
        grid_x = player_position[0] // self.tile_size
        grid_y = player_position[1] // self.tile_size

        if 0 <= grid_x < len(self.explored[0]) and 0 <= grid_y < len(self.explored):
            self.explored[grid_y][grid_x] = True

        # Check if the player is in a room and mark the entire room as explored
        for room in self.rooms:
            room_x, room_y, room_width, room_height = room
            if room_x <= grid_x < room_x + room_width and room_y <= grid_y < room_y + room_height:
                for y in range(room_y, room_y + room_height):
                    for x in range(room_x, room_x + room_width):
                        self.explored[y][x] = True
                break

    def display_minimap(self, screen, minimap_size, player_position, position=(10, 10)):
        """
        Draws the minimap on the screen, including the player's position as a dot.
        :param screen: The Pygame screen to draw on.
        :param minimap_size: The size of the minimap in pixels.
        :param player_position: The player's position in the dungeon.
        :param position: The (x, y) position to draw the minimap on the screen.
        """
        minimap_tile_size = minimap_size // len(self.tiles)  # Scale the minimap to fit
        offset_x, offset_y = position  # Position of the minimap on the screen

        for y, row in enumerate(self.tiles):
            for x, tile in enumerate(row):
                if self.explored[y][x]:
                    color = (200, 200, 200) if tile == 0 else (50, 50, 50)  # Gray for floors, dark gray for walls
                else:
                    color = (0, 0, 0)  # Black for unexplored tiles
                pygame.draw.rect(
                    screen,
                    color,
                    pygame.Rect(offset_x + x * minimap_tile_size, offset_y + y * minimap_tile_size, minimap_tile_size, minimap_tile_size)
                )
        
        # Draw the ladder on the minimap if it's in an explored area
        ladder_grid_x = self.ladder_position[0] // self.tile_size
        ladder_grid_y = self.ladder_position[1] // self.tile_size
        if 0 <= ladder_grid_x < len(self.tiles[0]) and 0 <= ladder_grid_y < len(self.tiles):
            if self.explored[ladder_grid_y][ladder_grid_x]:
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
        for y, row in enumerate(self.tiles):
            for x, tile in enumerate(row):
                color = (0, 0, 0) if tile == 1 else (200, 200, 200)  # Black for walls, gray for floors
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

        # Draw the ladder
        ladder_screen_x = self.ladder_position[0] - camera.offset_x
        ladder_screen_y = self.ladder_position[1] - camera.offset_y
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