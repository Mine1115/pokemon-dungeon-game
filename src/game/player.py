import pygame  # Import pygame to use its functions
import random
import asyncio
from game.pokemon import Pokemon
from game.combat import calculate_damage
from game.move import Projectile, Move
from utils.animation import SpriteAnimation

# Global variable to store the player instance
_player_instance = None

def set_player_instance(player):
    """Set the global player instance."""
    global _player_instance
    _player_instance = player

def get_player_instance():
    """Get the global player instance."""
    global _player_instance
    return _player_instance

class Player:
    def __init__(self, name, health, position, pokemon_name=None):
        self.name = name
        self.health = health
        self.position = list(position)
        self.size = (32, 32)  # Smaller size as requested
        self.collision_padding = 3
        
        # Use pokemon_name if provided, otherwise use name as fallback
        # This separates the player's username from their chosen Pokémon
        pokemon_to_load = pokemon_name.lower() if pokemon_name else name.lower()
        self.pokemon = Pokemon.from_json(pokemon_to_load)
        # Initialize XP to 0
        self.pokemon.experience = 0
        self.pokemon.level = 1
        self.cooldown = 0
        self.network_id = None  # Unique network ID for multiplayer
        
        # Load learnable moves from JSON
        self.pokemon.add_learnable_moves_from_json(pokemon_to_load)
        
        # Moves will be set by the title screen
        self.moves = []
        self.selected_move = 0
        self.projectiles = []
        self.last_direction = (1, 0)
        
        # Initialize sprite animation
        self.pokemon.animation.animation_state = "Idle"

    def get_collision_rect(self):
        """
        Get the player's collision rectangle with padding applied.
        """
        return pygame.Rect(
            self.position[0] + self.collision_padding,
            self.position[1] + self.collision_padding,
            self.size[0] - 2 * self.collision_padding,
            self.size[1] - 2 * self.collision_padding
        )

    def move(self, direction):
        if direction == "up":
            self.position[1] -= 1
        elif direction == "down":
            self.position[1] += 1
        elif direction == "left":
            self.position[0] -= 1
        elif direction == "right":
            self.position[0] += 1

    def attack(self, dungeon):
        """
        Perform an attack on nearby wild Pokémon or shoot a projectile.
        """
        if not dungeon or not self.moves:
            return  # No dungeon means no wild Pokémon to attack, or no moves available
            
        # Ensure selected_move is within bounds
        self.selected_move = min(self.selected_move, len(self.moves) - 1)
        move = self.moves[self.selected_move]
        
        if move.range_type == "Melee":
            # Melee attack logic (same as before)
            attack_range = self.get_collision_rect().inflate(40, 40)
            for wild in dungeon.wild_pokemon:
                wild_rect = pygame.Rect(wild["position"], (dungeon.tile_size, dungeon.tile_size))
                if attack_range.colliderect(wild_rect):
                    damage = calculate_damage(self.pokemon, wild["pokemon"], move)
                    wild["pokemon"].take_damage(damage)
                    print(f"Dealt {damage} damage to {wild['pokemon'].name}!")
                    if wild["pokemon"].is_fainted():
                        print(f"{wild['pokemon'].name} fainted!")
                        screen = pygame.display.get_surface()
                        self.pokemon.gain_experience(defeated_pokemon=wild["pokemon"], screen=screen)
                        dungeon.wild_pokemon.remove(wild)
                    return
        elif move.range_type == "Ranged":
            # Calculate diagonal direction if moving in two directions
            dx, dy = self.last_direction
            magnitude = (dx ** 2 + dy ** 2) ** 0.5
            if magnitude != 0:
                dx /= magnitude
                dy /= magnitude

            # Shoot a projectile from the center of the player
            player_center = (
                self.position[0] + self.size[0] // 2,
                self.position[1] + self.size[1] // 2
            )
            self.projectiles.append(Projectile(player_center, (dx, dy), 10, move, self))
            

    def use_item(self, item):
        if item in self.inventory:
            # Implement item usage logic here
            pass

    def link_moves(self, move1, move2):
        # Implement logic to link two moves together
        pass

    def add_move(self, move):
        self.moves.append(move)

    def add_item(self, item):
        self.inventory.append(item)

    def handle_input(self, keys, hub=None, dungeon=None):
        player_rect = self.get_collision_rect()
        dx, dy = 0, 0

        if keys[pygame.K_UP]:
            new_rect = player_rect.move(0, -5)
            if dungeon:
                if dungeon.is_walkable(new_rect.left, new_rect.top) and dungeon.is_walkable(new_rect.right, new_rect.top):
                    self.position[1] -= 5
                    dy = -1
            elif hub:
                self.position[1] -= 5
                dy = -1

        if keys[pygame.K_DOWN]:
            new_rect = player_rect.move(0, 5)
            if dungeon:
                if dungeon.is_walkable(new_rect.left, new_rect.bottom) and dungeon.is_walkable(new_rect.right, new_rect.bottom):
                    self.position[1] += 5
                    dy = 1
            elif hub:
                self.position[1] += 5
                dy = 1

        if keys[pygame.K_LEFT]:
            new_rect = player_rect.move(-5, 0)
            if dungeon:
                if dungeon.is_walkable(new_rect.left, new_rect.top) and dungeon.is_walkable(new_rect.left, new_rect.bottom):
                    self.position[0] -= 5
                    dx = -1
            elif hub:
                self.position[0] -= 5
                dx = -1

        if keys[pygame.K_RIGHT]:
            new_rect = player_rect.move(5, 0)
            if dungeon:
                if dungeon.is_walkable(new_rect.right, new_rect.top) and dungeon.is_walkable(new_rect.right, new_rect.bottom):
                    self.position[0] += 5
                    dx = 1
            elif hub:
                self.position[0] += 5
                dx = 1

        # Update last direction based on movement
        if dx != 0 or dy != 0:
            self.last_direction = (dx, dy)
            
            # Update animation state to Walk if not already walking
            if self.pokemon.animation.animation_name != "Walk" and self.cooldown == 0:
                self.pokemon.animation.set_animation("Walk")
                # No need to set animation_name as it's already set by set_animation method
        elif self.pokemon.animation.animation_name == "Walk" and self.cooldown == 0:
            # Return to Idle if not moving and not attacking
            self.pokemon.animation.set_animation("Idle")
            # No need to set animation_name as it's already set by set_animation method

        # Handle interactions in the hub
        if hub:
            self.check_interactions(hub)

        # Switch moves
        if keys[pygame.K_1]:
            self.selected_move = 0
        if keys[pygame.K_2]:
            self.selected_move = 1
        if keys[pygame.K_3] and len(self.moves) > 2:
            self.selected_move = 2
        if keys[pygame.K_4] and len(self.moves) > 3:
            self.selected_move = 3

        # Handle attack
        if keys[pygame.K_SPACE] and self.cooldown == 0:  # Spacebar to attack
            # Check if we're in multiplayer mode
            if hasattr(self, 'network_client') and self.network_client.connected and self.network_client.in_dungeon:
                # Send attack to server
                if self.selected_move < len(self.moves):
                    move = self.moves[self.selected_move]
                    damage = move.power if hasattr(move, 'power') else 10
                    attack_range = 50  # Default range
                    
                    # Determine attack type based on move category
                    attack_type = 'direct'
                    if hasattr(move, 'category') and move.category == 'Special':
                        attack_type = 'projectile'
                    
                    self.network_client.attack(move.name, damage, attack_range, attack_type)
            else:
                # Local attack
                self.attack(dungeon)
                
            self.cooldown = 30  # Cooldown in frames (e.g., 30 frames = 0.5 seconds at 60 FPS)
            
            # Set animation state to Attack
            #self.pokemon.animation.set_animation("Attack")
            #self.pokemon.animation_state = "Attack"

        # Reduce cooldown
        if self.cooldown > 0:
            self.cooldown -= 1

    def is_walkable(self, rect, dungeon):
        """
        Checks if the player's rectangle is walkable in the dungeon.
        """
        # Check all four corners of the rectangle
        for corner in [(rect.left, rect.top), (rect.right, rect.top), (rect.left, rect.bottom), (rect.right, rect.bottom)]:
            if not dungeon.is_walkable(corner[0], corner[1]):
                return False
        return True

    def check_interactions(self, hub):
        """
        Checks for interactions with objects in the hub.
        """
        player_rect = pygame.Rect(self.position, self.size)
        collision = hub.check_collision(player_rect)
        if collision and collision.get("interactable", False):
            self.interact(collision)

    def interact(self, obj):
        """
        Handles interaction with an object.
        """
        print(f"Interacting with {obj['name']}")
        if obj["name"] == "Dungeon Entrance":
            # Check if we're already in the process of entering a dungeon
            if hasattr(self, 'entering_dungeon') and self.entering_dungeon:
                return  # Skip this interaction to prevent double triggering
            
            # Check if we have a last_interaction attribute and if it's the same object
            # and if the interaction happened recently (within 1 second)
            current_time = pygame.time.get_ticks()
            if hasattr(self, 'last_interaction') and \
               self.last_interaction.get('name') == obj['name'] and \
               current_time - self.last_interaction.get('time', 0) < 1000:
                return  # Skip this interaction to prevent double triggering
            
            # Store this interaction
            self.last_interaction = {
                'name': obj['name'],
                'time': current_time
            }
            
            print("Entering the dungeon...")
            obj["action"]()  # Call the action associated with the object (e.g., transition to dungeon)

    def draw(self, screen, camera):
        """
        Draws the player on the screen, applying the camera offset using the animated sprite.
        """
        # Update the sprite direction based on last movement direction
        if self.last_direction != (0, 0):
            self.pokemon.animation.set_direction(self.last_direction)
        
        # Update animation state based on player actions, preventing flickering
        if self.last_direction != (0, 0) and self.pokemon.animation.animation_name != "Walk": #and self.cooldown == 0:
            self.pokemon.animation.set_animation("Walk")
            # No need to set animation_name as it's already set by set_animation method
        elif self.last_direction == (0, 0) and self.pokemon.animation.animation_name != "Idle": #and self.cooldown == 0:
            self.pokemon.animation.set_animation("Idle")
            # No need to set animation_name as it's already set by set_animation method
            
        # Update the animation
        self.pokemon.animation.update()
        
        # Get the current frame with default scale factor
        current_frame = self.pokemon.animation.get_current_frame(scale_factor=2.0)
        
        if current_frame:
            # Get the collision rectangle to scale the sprite properly
            collision_rect = self.get_collision_rect()
            collision_size = (collision_rect.width, collision_rect.height)
            
            # Calculate the position with offset to center the sprite on the collision box
            screen_position = camera.apply(self.position)
            # Use the sprite offset from the animation object instead of hardcoded values
            offset_x, offset_y = self.pokemon.animation.sprite_offset
            if offset_x == 0 and offset_y == 0:  # If no offset was set, use default values
                offset_x = -14  # Default offset values
                offset_y = -10
            screen_position = (screen_position[0] + offset_x, screen_position[1] + offset_y)
            
            # Draw the sprite - create a clean surface each time to prevent stacking frames
            screen.blit(current_frame, screen_position)
            
            # Uncomment to debug collision box
            # pygame.draw.rect(screen, (255, 0, 0), pygame.Rect(camera.apply((collision_rect.x, collision_rect.y)), collision_size), 1)
        else:
            # Fallback to rectangle if animation failed
            screen_position = camera.apply(self.position)
            pygame.draw.rect(screen, (255, 255, 0), pygame.Rect(screen_position, self.size))

    def draw_xp_bar(self, screen):
        """
        Draw the XP bar below the HP bar.
        """
        max_xp = self.pokemon.get_experience_to_next_level()
        current_xp = self.pokemon.experience
        
        # Ensure max_xp is at least 1 to avoid division by zero
        if max_xp == 0:
            max_xp = 1
            current_xp = 0
        
        xp_ratio = current_xp / max_xp
        bar_width = 200
        bar_height = 10
        
        # Draw the background of the XP bar
        pygame.draw.rect(screen, (50, 50, 50), (10, 40, bar_width, bar_height))
        # Draw the current XP
        pygame.draw.rect(screen, (0, 191, 255), (10, 40, int(bar_width * xp_ratio), bar_height))
        
        # Draw the text for current XP
        font = pygame.font.Font(None, 18)
        xp_text = font.render(f"XP: {current_xp}/{max_xp}", True, (255, 255, 255))
        screen.blit(xp_text, (10 + bar_width + 10, 40))
        
        # Draw the level display (moved down to avoid overlap with floor number)
        level_font = pygame.font.Font(None, 24)
        level_text = level_font.render(f"Level: {self.pokemon.level}", True, (255, 255, 255))
        screen.blit(level_text, (10, 100))

    def draw_hp_bar(self, screen):
        """
        Draw the HP bar for the player's Pokémon at the top-left corner of the screen.
        """
        max_hp = self.pokemon.stats["HP"]
        current_hp = self.pokemon.current_hp
        hp_ratio = current_hp / max_hp
        bar_width = 200
        bar_height = 20
        hp_color = (255, 0, 0) if hp_ratio < 0.3 else (255, 255, 0) if hp_ratio < 0.7 else (0, 255, 0)

        # Draw the background of the HP bar
        pygame.draw.rect(screen, (50, 50, 50), (10, 10, bar_width, bar_height))
        # Draw the current HP
        pygame.draw.rect(screen, hp_color, (10, 10, int(bar_width * hp_ratio), bar_height))

        # Draw the text for current HP
        font = pygame.font.Font(None, 24)
        hp_text = font.render(f"{current_hp}/{max_hp} HP", True, (255, 255, 255))
        screen.blit(hp_text, (10 + bar_width + 10, 10))

    def draw_moves(self, screen):
        """
        Draw all four move slots and highlight the selected move.
        """
        font = pygame.font.Font(None, 24)
        move_box_width = 150
        move_box_height = 40
        padding = 10
        start_x = 10
        start_y = screen.get_height() - (move_box_height + padding) * 4 - 10  # Always show 4 slots

        # Use Pokemon's current_moves list instead of self.moves
        moves = self.pokemon.current_moves
        
        # Ensure selected_move is within bounds
        if len(moves) > 0:
            self.selected_move = min(self.selected_move, len(moves) - 1)
        else:
            self.selected_move = 0

        for i in range(4):  # Always draw 4 move boxes
            # Highlight the selected move
            color = (0, 255, 0) if i == self.selected_move and i < len(moves) else (255, 255, 255)
            pygame.draw.rect(
                screen,
                color,
                pygame.Rect(start_x, start_y + i * (move_box_height + padding), move_box_width, move_box_height),
                2  # Border thickness
            )

            # Draw the move name or "Empty" for unused slots
            if i < len(moves):
                move_text = font.render(moves[i].name, True, (255, 255, 255))
            else:
                move_text = font.render("Empty", True, (128, 128, 128))  # Gray color for empty slots
            screen.blit(move_text, (start_x + 10, start_y + i * (move_box_height + padding) + 10))

        # Keep self.moves in sync with pokemon's moves
        self.moves = moves