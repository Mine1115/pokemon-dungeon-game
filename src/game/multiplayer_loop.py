import pygame
from game.dungeon import Dungeon
from game.hub import Hub
from game.camera import Camera
from utils.settings import SCREEN_WIDTH, SCREEN_HEIGHT

class MultiplayerLoop:
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
        
    def transition_to_dungeon(self):
        """Handle transition from hub to dungeon for multiplayer"""
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
        
        # Initialize a placeholder dungeon for multiplayer
        self.dungeon = Dungeon(2000, 2000, 50, floor=1)
        # Request a dungeon from the server
        self.player.network_client.enter_dungeon(1)  # Start with floor 1
        
        # Draw the initial state of the dungeon
        self.screen.fill((0, 0, 0))  # Black background
        self.dungeon.display(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        self.player.draw_hp_bar(self.screen)
        self.player.draw_xp_bar(self.screen)
        pygame.display.flip()
    
    def handle_dungeon_logic(self, keys):
        """Handle all dungeon-related logic for multiplayer"""
        # Check if the player's Pokémon has fainted
        if self.player.pokemon.is_fainted():
            print(f"Your {self.player.pokemon.name} fainted! Returning to the hub...")
            self.in_dungeon = False  # Exit the dungeon
            self.player.position = [500, 500]  # Reset player position to the hub
            self.player.pokemon.current_hp = self.player.pokemon.stats["HP"]  # Reset HP to full
            self.player.network_client.exit_dungeon()
            return
        
        # Request periodic updates from the server less frequently to reduce network load
        if pygame.time.get_ticks() % 60 == 0:  # Update every 60 frames
            self.player.network_client.update_dungeon()
        
        # Initialize or update dungeon with server data
        if self.dungeon is None or self.player.network_client.current_dungeon:
            # Get dungeon data from network client
            server_dungeon = self.player.network_client.current_dungeon
            if server_dungeon:
                if self.dungeon is None:
                    # Create new dungeon only if it doesn't exist
                    self.dungeon = Dungeon(server_dungeon.width, server_dungeon.height, server_dungeon.tile_size, floor=server_dungeon.floor)
                    # Set initial player position if needed
                    if not self.player.position or self.player.position == [0, 0]:
                        if hasattr(server_dungeon, 'spawn_point'):
                            # Validate that the spawn point is on a walkable tile
                            spawn_x, spawn_y = server_dungeon.spawn_point
                            if self.dungeon.is_walkable(spawn_x, spawn_y):
                                self.player.position = list(server_dungeon.spawn_point)
                            else:
                                # Find a valid spawn point if the server-provided one is invalid
                                valid_spawn = self.dungeon.find_nearest_valid_spawn(spawn_x, spawn_y)
                                self.player.position = list(valid_spawn)
                                print(f"Found valid spawn point at {valid_spawn}")
                        else:
                            # Use local spawn point finding logic
                            spawn_point = self.dungeon.get_spawn_point()
                            if spawn_point:
                                self.player.position = list(spawn_point)
                # Update only changed dungeon state
                if hasattr(server_dungeon, 'tiles') and server_dungeon.tiles != self.dungeon.tiles:
                    self.dungeon.tiles = server_dungeon.tiles
                if hasattr(server_dungeon, 'explored'):
                    # Merge explored tiles to maintain visibility
                    if not hasattr(self.dungeon, 'explored') or self.dungeon.explored is None:
                        self.dungeon.explored = server_dungeon.explored
                    else:
                        for y in range(len(server_dungeon.explored)):
                            for x in range(len(server_dungeon.explored[y])):
                                if server_dungeon.explored[y][x]:
                                    self.dungeon.explored[y][x] = True
                if hasattr(server_dungeon, 'ladder_position'):
                    self.dungeon.ladder_position = server_dungeon.ladder_position
                if hasattr(server_dungeon, 'enemy_projectiles'):
                    self.dungeon.enemy_projectiles = server_dungeon.enemy_projectiles
                if hasattr(server_dungeon, 'wild_pokemon'):
                    self.dungeon.wild_pokemon = server_dungeon.wild_pokemon
        
        # Check for interaction with the ladder
        player_rect = pygame.Rect(self.player.position, self.player.size)
        ladder_position = self.player.network_client.get_dungeon_ladder_position()
        tile_size = 50  # Default tile size
        if self.player.network_client.current_dungeon:
            tile_size = self.player.network_client.current_dungeon.tile_size
        ladder_rect = pygame.Rect(ladder_position, (tile_size, tile_size))
        
        if player_rect.colliderect(ladder_rect):
            print("Descending to the next floor...")
            # Ensure we have a valid spawn point before transitioning
            if self.player.network_client.current_dungeon:
                spawn_point = self.player.network_client.current_dungeon.get_player_spawn()
                if spawn_point:
                    self.player.position = list(spawn_point)
            self.player.network_client.next_floor()

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
        
        # Handle dungeon display
        if self.dungeon:
            self.dungeon.display(self.screen, self.camera)
        else:
            # If dungeon isn't initialized yet, draw a loading message
            font = pygame.font.SysFont(None, 36)
            loading_text = font.render("Loading dungeon...", True, (255, 255, 255))
            text_rect = loading_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
            self.screen.blit(loading_text, text_rect)
        
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
        
        # Display server-side dungeon minimap
        try:
            # Get dungeon data
            tiles = self.player.network_client.get_dungeon_tiles()
            explored = self.player.network_client.get_dungeon_explored()
            
            # Calculate minimap tile size
            minimap_size = 200
            minimap_tile_size = minimap_size // len(tiles) if tiles else 1
            offset_x, offset_y = minimap_position
            
            # Draw minimap tiles
            for y, row in enumerate(tiles):
                for x, tile in enumerate(row):
                    if y < len(explored) and x < len(explored[0]):
                        if explored[y][x]:
                            color = (200, 200, 200) if tile == 0 else (50, 50, 50)  # Gray for floors, dark gray for walls
                        else:
                            color = (0, 0, 0)  # Black for unexplored tiles
                            
                        pygame.draw.rect(
                            self.screen,
                            color,
                            pygame.Rect(offset_x + x * minimap_tile_size, offset_y + y * minimap_tile_size, minimap_tile_size, minimap_tile_size)
                        )
            
            # Draw the ladder on the minimap if it's in an explored area
            ladder_pos = self.player.network_client.get_dungeon_ladder_position()
            ladder_grid_x = ladder_pos[0] // 50  # Assuming tile_size is 50
            ladder_grid_y = ladder_pos[1] // 50
            
            if 0 <= ladder_grid_x < len(tiles[0]) and 0 <= ladder_grid_y < len(tiles):
                if ladder_grid_y < len(explored) and ladder_grid_x < len(explored[0]) and explored[ladder_grid_y][ladder_grid_x]:
                    ladder_minimap_x = offset_x + ladder_grid_x * minimap_tile_size
                    ladder_minimap_y = offset_y + ladder_grid_y * minimap_tile_size
                    pygame.draw.rect(
                        self.screen,
                        (255, 215, 0),  # Gold color for the ladder
                        pygame.Rect(ladder_minimap_x, ladder_minimap_y, minimap_tile_size, minimap_tile_size)
                    )
            
            # Draw the player's position as a dot on the minimap
            player_minimap_x = offset_x + (self.player.position[0] / 50) * minimap_tile_size  # Assuming tile_size is 50
            player_minimap_y = offset_y + (self.player.position[1] / 50) * minimap_tile_size
            pygame.draw.circle(
                self.screen,
                (255, 0, 0),  # Red color for the player dot
                (int(player_minimap_x), int(player_minimap_y)),
                max(2, minimap_tile_size // 4)  # Radius of the dot
            )
        except Exception as e:
            print(f"Error rendering minimap: {e}")
        
        # Display the player's moves
        self.player.draw_moves(self.screen)

        # Display the floor count
        if self.player.network_client.current_dungeon:
            floor = self.player.network_client.current_dungeon.floor
            font = pygame.font.SysFont(None, 36)
            text = font.render(f"Floor: {floor}", True, (255, 255, 255))
            self.screen.blit(text, (20, 20))
    
    def handle_hub_logic(self, keys):
        """Handle all hub-related logic for multiplayer"""
        self.player.handle_input(keys, hub=self.hub)
        self.camera.update(self.player.position)
        self.screen.fill((0, 199, 0))  # Green background
        self.hub.display(self.screen, self.camera)
        
        # Display other players in the hub
        other_players = self.player.network_client.get_other_players()
        for other_player in other_players:
            # Only display players who are not in a dungeon and not the local player
            if not other_player.in_dungeon and other_player.id != self.player.network_client.player_id:
                self.hub.draw_other_player(self.screen, self.camera, other_player, self.player.network_client.player_id)
        
        self.player.draw(self.screen, self.camera)
        
        # Check for interactions with hub objects
        self.player.check_interactions(self.hub)
        
        # Update player position on the server
        self.player.network_client.update_position(self.player.position[0], self.player.position[1], 
                                                 self.player.last_direction[0], self.player.last_direction[1])
    
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