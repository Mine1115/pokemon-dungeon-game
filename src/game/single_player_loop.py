import pygame
from game.dungeon import Dungeon
from game.hub import Hub
from game.camera import Camera
from utils.settings import SCREEN_WIDTH, SCREEN_HEIGHT

class SinglePlayerLoop:
    def __init__(self, screen, player):
        self.screen = screen
        self.player = player
        self.dungeon = None
        self.hub = Hub(self.transition_to_dungeon)
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.in_dungeon = False
        self.clock = pygame.time.Clock()
        
        # Set player position in hub
        self.player.position = [500, 500]
        
    def generate_new_dungeon(self):
        """Generate a new dungeon floor for single player mode"""
        if self.dungeon:
            floor = self.dungeon.floor + 1  # Increment the floor count
        else:
            floor = 1  # Start at floor 1
            
        self.dungeon = Dungeon(2000, 2000, 50, floor=floor)  # Generate a new dungeon floor
        self.player.position = list(self.dungeon.get_spawn_point())  # Spawn the player in the first room
    
    def transition_to_dungeon(self):
        """Handle transition from hub to dungeon"""
        # Only transition if not already in dungeon
        if self.in_dungeon:
            return
            
        # Set a flag on the player to prevent rapid re-entry
        self.player.entering_dungeon = True
        
        # Move player away from the entrance to prevent immediate re-interaction
        if self.player.last_direction[0] != 0 or self.player.last_direction[1] != 0:
            # Move player in the direction they were facing
            self.player.position[0] += self.player.last_direction[0] * 50
            self.player.position[1] += self.player.last_direction[1] * 50
        else:
            # Default movement if no direction (move down)
            self.player.position[1] += 50
            
        self.in_dungeon = True
        
        # Generate the dungeon
        self.generate_new_dungeon()
        
        # Draw the initial state of the dungeon
        self.screen.fill((0, 0, 0))  # Black background
        self.dungeon.display(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        self.player.draw_hp_bar(self.screen)
        self.player.draw_xp_bar(self.screen)
        pygame.display.flip()
    
    def handle_dungeon_logic(self, keys):
        """Handle all dungeon-related logic for single player"""
        # Check if the player's Pokémon has fainted
        if self.player.pokemon.is_fainted():
            print(f"Your {self.player.pokemon.name} fainted! Returning to the hub...")
            self.in_dungeon = False  # Exit the dungeon
            self.player.position = [500, 500]  # Reset player position to the hub
            self.player.pokemon.current_hp = self.player.pokemon.stats["HP"]  # Reset HP to full
            self.dungeon.floor = 0  # Reset the floor count
            return
        
        # Update explored tiles
        self.dungeon.update_explored(self.player.position)

        # Update wild Pokémon behavior
        self.dungeon.update_wild_pokemon(self.player)
        
        # Check for interaction with the ladder
        player_rect = pygame.Rect(self.player.position, self.player.size)
        ladder_rect = pygame.Rect(self.dungeon.ladder_position, (self.dungeon.tile_size, self.dungeon.tile_size))
        if player_rect.colliderect(ladder_rect):
            print("Descending to the next floor...")
            # Store current position to prevent spawning in walls
            old_position = list(self.player.position)
            self.generate_new_dungeon()
            # Validate spawn position
            if not self.dungeon.is_walkable(self.player.position[0], self.player.position[1]):
                # Try to find a valid spawn point
                spawn_point = self.dungeon.get_spawn_point()
                if spawn_point:
                    self.player.position = list(spawn_point)
                else:
                    # If no valid spawn point found, reset to previous position
                    self.player.position = old_position

        # Update player projectiles
        if not hasattr(self.player, 'projectiles'):
            self.player.projectiles = []
        for projectile in self.player.projectiles[:]:
            if not projectile.update(self.dungeon):
                self.player.projectiles.remove(projectile)
                
        # Update enemy projectiles
        for projectile in self.dungeon.enemy_projectiles[:]:
            if not projectile.update(self.dungeon):
                self.dungeon.enemy_projectiles.remove(projectile)

        # Display the dungeon
        self.screen.fill((0, 0, 0))  # Black background
        self.dungeon.display(self.screen, self.camera)
        
        # Handle input and collision detection
        self.player.handle_input(keys, dungeon=self.dungeon)
        self.camera.update(self.player.position)
        self.player.draw(self.screen, self.camera)
            
        # Draw projectiles
        for projectile in self.player.projectiles:
            projectile.draw(self.screen, self.camera)

        # Display the player's HP bar
        self.player.draw_hp_bar(self.screen)

        # Display the player's XP bar
        self.player.draw_xp_bar(self.screen)
        
        # Display the minimap in the top-right corner
        minimap_position = (self.screen.get_width() - 210, 10)
        self.dungeon.display_minimap(self.screen, minimap_size=200, player_position=self.player.position, position=minimap_position)
        
        # Display the player's moves
        self.player.draw_moves(self.screen)

        # Display the floor count
        self.dungeon.display_floor_count(self.screen)
    
    def handle_hub_logic(self, keys):
        """Handle all hub-related logic"""
        self.player.handle_input(keys, hub=self.hub)
        self.camera.update(self.player.position)
        self.screen.fill((0, 199, 0))  # Green background
        self.hub.display(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        
        # Check for interactions with hub objects
        self.player.check_interactions(self.hub)
    
    def run_frame(self, keys, events):
        """Run a single frame of the game loop"""
        if self.in_dungeon:
            self.handle_dungeon_logic(keys)
        else:
            self.handle_hub_logic(keys)
            
        # Update the display
        pygame.display.flip()
        self.clock.tick(60)  # Maintain 60 FPS
        
        return True  # Continue running