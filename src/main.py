import pygame
import asyncio
import threading
from game.hub import Hub
from game.player import Player
from game.camera import Camera
from game.dungeon import Dungeon
from game.title_screen import TitleScreen
from game.move import Move
from utils.settings import SCREEN_WIDTH, SCREEN_HEIGHT

async def main():
    pygame.init()  # Initialize Pygame
    pygame.font.init()  # Initialize Pygame font system

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Pokemon Dungeon Game")

    def generate_new_dungeon():
        nonlocal dungeon, player
        # For multiplayer, we'll use the server-generated dungeon
        if hasattr(player, 'network_client') and player.network_client.connected:
            if dungeon:
                floor = dungeon.floor + 1  # Increment the floor count
            else:
                floor = 1  # Start at floor 1
                
            # Request a new dungeon from the server
            player.network_client.enter_dungeon(floor)
            
            # The dungeon state will be received via socket events
            # and the player position will be updated accordingly
            return
        
        # For single player, generate locally
        if dungeon:
            floor = dungeon.floor + 1  # Increment the floor count
        else:
            floor = 1  # Start at floor 1
        dungeon = Dungeon(2000, 2000, 50, floor=floor)  # Generate a new dungeon floor
        player.position = list(dungeon.get_player_spawn())  # Spawn the player in the first room

    def transition_to_dungeon():
        nonlocal in_dungeon, screen, dungeon
        in_dungeon = True
        
        # For multiplayer, use server-side dungeon
        if hasattr(player, 'network_client') and player.network_client.connected:
            # Initialize a placeholder dungeon for multiplayer
            dungeon = Dungeon(2000, 2000, 50, floor=1)
            player.network_client.enter_dungeon(1)  # Start with floor 1
            # The dungeon state will be received via socket events
        else:
            # For single player, generate locally
            generate_new_dungeon()
        
        # Draw the initial state of the dungeon including XP bar
        screen.fill((0, 0, 0))  # Black background
        dungeon.display(screen, camera)  # Always display dungeon, whether multiplayer or single player
        player.draw(screen, camera)
        player.draw_hp_bar(screen)
        player.draw_xp_bar(screen)  # Ensure XP bar is drawn when first entering
        pygame.display.flip()  # Update the display immediately

    def start_game_with_pokemon(pokemon_name, selected_moves, multiplayer_enabled, username):
        nonlocal player, hub, camera, in_title_screen
        
        # Create player with selected Pokémon and set network client player ID
        player = Player(name=username, health=100, position=(500, 500), pokemon_name=pokemon_name)
        # No need to override pokemon as it's now properly initialized with pokemon_name
         
        # Clear default moves and add selected moves
        player.moves = []
        player.pokemon.current_moves = []
        for move in selected_moves:
            player.moves.append(move)
            player.pokemon.current_moves.append(move)
        
        player.selected_move = 0
        
        # Set the global player instance
        from game.player import set_player_instance
        set_player_instance(player)
        
        # Initialize network client for multiplayer
        if multiplayer_enabled:
            from game.network_client import NetworkClient
            network_client = NetworkClient()
            if network_client.connect_to_server():
                network_client.join_game(username, pokemon_name, player.position[0], player.position[1])
                player.network_client = network_client
            else:
                print("Failed to connect to multiplayer server")
        
        # Initialize hub and camera
        hub = Hub(transition_to_dungeon)
        camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Exit title screen
        in_title_screen = False

    # Initialize title screen
    title_screen = TitleScreen(screen, start_game_with_pokemon)
    in_title_screen = True
    
    # These will be initialized when the player selects a Pokémon
    player = None
    hub = None
    camera = None
    dungeon = None

    clock = pygame.time.Clock()
    running = True
    in_dungeon = False

    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        if in_title_screen:
            # Handle title screen
            if not title_screen.handle_events(events):
                running = False
            title_screen.draw()
            clock.tick(60)
            continue

        keys = pygame.key.get_pressed()

        if in_dungeon:
            # Check if the player's Pokémon has fainted
            if player.pokemon.is_fainted(): 
                print(f"Your {player.pokemon.name} fainted! Returning to the hub...")
                in_dungeon = False  # Exit the dungeon
                player.position = [500, 500]  # Reset player position to the hub
                player.pokemon.current_hp = player.pokemon.stats["HP"]  # Reset HP to full calculated value
                
                # Handle multiplayer dungeon exit
                if hasattr(player, 'network_client') and player.network_client.connected:
                    player.network_client.exit_dungeon()
                else:
                    dungeon.floor = 0  # Reset the floor count
                    
                continue  # Skip the rest of the dungeon logic

            # Handle multiplayer vs. single player dungeon logic
            if hasattr(player, 'network_client') and player.network_client.connected and player.network_client.in_dungeon:
                # Multiplayer: Use server-side dungeon data
                
                # Request periodic updates from the server less frequently to reduce network load
                if pygame.time.get_ticks() % 60 == 0:  # Update every 60 frames
                    await player.network_client.update_dungeon()
                
                # Initialize or update dungeon with server data more efficiently
                if dungeon is None or player.network_client.current_dungeon:
                    # Get dungeon data from network client
                    server_dungeon = player.network_client.current_dungeon
                    if server_dungeon:
                        if dungeon is None:
                            # Create new dungeon only if it doesn't exist
                            dungeon = Dungeon(server_dungeon.width, server_dungeon.height, server_dungeon.tile_size, floor=server_dungeon.floor)
                            # Set initial player position if needed
                            if not player.position or player.position == [0, 0]:
                                player.position = list(dungeon.get_player_spawn())
                        # Update only changed dungeon state
                        if hasattr(server_dungeon, 'tiles') and server_dungeon.tiles != dungeon.tiles:
                            dungeon.tiles = server_dungeon.tiles
                        if hasattr(server_dungeon, 'explored'):
                            # Merge explored tiles to maintain visibility
                            if not hasattr(dungeon, 'explored') or dungeon.explored is None:
                                dungeon.explored = server_dungeon.explored
                            else:
                                for y in range(len(server_dungeon.explored)):
                                    for x in range(len(server_dungeon.explored[y])):
                                        if server_dungeon.explored[y][x]:
                                            dungeon.explored[y][x] = True
                        if hasattr(server_dungeon, 'ladder_position'):
                            dungeon.ladder_position = server_dungeon.ladder_position
                        if hasattr(server_dungeon, 'enemy_projectiles'):
                            dungeon.enemy_projectiles = server_dungeon.enemy_projectiles
                
                # Check for interaction with the ladder
                player_rect = pygame.Rect(player.position, player.size)
                ladder_position = player.network_client.get_dungeon_ladder_position()
                tile_size = 50  # Default tile size
                if player.network_client.current_dungeon:
                    tile_size = player.network_client.current_dungeon.tile_size
                ladder_rect = pygame.Rect(ladder_position, (tile_size, tile_size))
                
                if player_rect.colliderect(ladder_rect):
                    print("Descending to the next floor...")
                    player.network_client.next_floor()
            else:
                # Single player: Use local dungeon logic
                # Update explored tiles
                dungeon.update_explored(player.position)

                # Update wild Pokémon behavior
                dungeon.update_wild_pokemon(player)

                # Check for interaction with the ladder
                player_rect = pygame.Rect(player.position, player.size)
                ladder_rect = pygame.Rect(dungeon.ladder_position, (dungeon.tile_size, dungeon.tile_size))
                if player_rect.colliderect(ladder_rect):
                    print("Descending to the next floor...")
                    generate_new_dungeon()

            # Update player projectiles
            if not hasattr(player, 'projectiles'):
                player.projectiles = []
            for projectile in player.projectiles[:]:
                if not projectile.update(dungeon):
                    player.projectiles.remove(projectile)
                    
            # Update enemy projectiles
            for projectile in dungeon.enemy_projectiles[:]:
                if not projectile.update(dungeon):
                    dungeon.enemy_projectiles.remove(projectile)

            # Display the dungeon
            screen.fill((0, 0, 0))  # Black background
            
            # Handle multiplayer vs. single player dungeon display
            if hasattr(player, 'network_client') and player.network_client.connected and player.network_client.in_dungeon:
                # Multiplayer: Display server-side dungeon
                if player.network_client.current_dungeon:
                    # Draw tiles based on server data
                    tiles = player.network_client.get_dungeon_tiles()
                    explored = player.network_client.get_dungeon_explored()
                    tile_size = player.network_client.current_dungeon.tile_size
                    
                    # Draw tiles
                    for y, row in enumerate(tiles):
                        for x, tile in enumerate(row):
                            # Only draw if explored
                            if y < len(explored) and x < len(explored[0]) and explored[y][x]:
                                # Calculate screen position
                                screen_x = x * tile_size - camera.offset_x
                                screen_y = y * tile_size - camera.offset_y
                                
                                # Only draw if on screen
                                if -tile_size <= screen_x <= SCREEN_WIDTH and -tile_size <= screen_y <= SCREEN_HEIGHT:
                                    color = (200, 200, 200) if tile == 0 else (50, 50, 50)  # Gray for floors, dark gray for walls
                                    pygame.draw.rect(screen, color, pygame.Rect(screen_x, screen_y, tile_size, tile_size))
                    
                    # Draw ladder
                    ladder_pos = player.network_client.get_dungeon_ladder_position()
                    ladder_screen_x = ladder_pos[0] - camera.offset_x
                    ladder_screen_y = ladder_pos[1] - camera.offset_y
                    if -tile_size <= ladder_screen_x <= SCREEN_WIDTH and -tile_size <= ladder_screen_y <= SCREEN_HEIGHT:
                        pygame.draw.rect(screen, (255, 215, 0), pygame.Rect(ladder_screen_x, ladder_screen_y, tile_size, tile_size))
                    
                    # Draw wild Pokémon
                    for pokemon in player.network_client.get_wild_pokemon():
                        pokemon_screen_x = pokemon.position[0] - camera.offset_x
                        pokemon_screen_y = pokemon.position[1] - camera.offset_y
                        if -tile_size <= pokemon_screen_x <= SCREEN_WIDTH and -tile_size <= pokemon_screen_y <= SCREEN_HEIGHT:
                            # Draw a simple representation of the Pokémon
                            pygame.draw.rect(screen, (255, 0, 0), pygame.Rect(pokemon_screen_x, pokemon_screen_y, tile_size, tile_size))
                            
                            # Draw HP bar above the Pokémon
                            hp_width = 40
                            hp_height = 5
                            hp_x = pokemon_screen_x + (tile_size - hp_width) // 2
                            hp_y = pokemon_screen_y - 10
                            
                            # Background (empty) bar
                            pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(hp_x, hp_y, hp_width, hp_height))
                            
                            # Filled portion based on HP percentage
                            hp_percentage = pokemon.current_hp / pokemon.max_hp
                            filled_width = int(hp_width * hp_percentage)
                            hp_color = (0, 255, 0) if hp_percentage > 0.5 else (255, 255, 0) if hp_percentage > 0.25 else (255, 0, 0)
                            pygame.draw.rect(screen, hp_color, pygame.Rect(hp_x, hp_y, filled_width, hp_height))
            else:
                # Single player: Display local dungeon
                dungeon.display(screen, camera)
            
            # Handle input and collision detection for both multiplayer and single player
            player.handle_input(keys, dungeon=dungeon)  # Always pass dungeon for collision detection
                
            camera.update(player.position)  # Update the camera to follow the player
            # Animation update is now handled in the player.draw method
            player.draw(screen, camera)

            # Draw projectiles
            for projectile in player.projectiles:
                projectile.draw(screen, camera)

            # Display the player's HP bar
            player.draw_hp_bar(screen)
    
            # Display the player's XP bar
            player.draw_xp_bar(screen)
    
            # Display the minimap in the top-right corner
            minimap_position = (screen.get_width() - 210, 10)  # Top-right corner with padding
            
            # Handle multiplayer vs. single player minimap display
            if hasattr(player, 'network_client') and player.network_client.connected and player.network_client.in_dungeon:
                # Multiplayer: Display server-side dungeon minimap
                if player.network_client.current_dungeon:
                    # Get dungeon data
                    tiles = player.network_client.get_dungeon_tiles()
                    explored = player.network_client.get_dungeon_explored()
                    
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
                                    screen,
                                    color,
                                    pygame.Rect(offset_x + x * minimap_tile_size, offset_y + y * minimap_tile_size, minimap_tile_size, minimap_tile_size)
                                )
                    
                    # Draw the ladder on the minimap if it's in an explored area
                    ladder_pos = player.network_client.get_dungeon_ladder_position()
                    ladder_grid_x = ladder_pos[0] // 50  # Assuming tile_size is 50
                    ladder_grid_y = ladder_pos[1] // 50
                    
                    if 0 <= ladder_grid_x < len(tiles[0]) and 0 <= ladder_grid_y < len(tiles):
                        if ladder_grid_y < len(explored) and ladder_grid_x < len(explored[0]) and explored[ladder_grid_y][ladder_grid_x]:
                            ladder_minimap_x = offset_x + ladder_grid_x * minimap_tile_size
                            ladder_minimap_y = offset_y + ladder_grid_y * minimap_tile_size
                            pygame.draw.rect(
                                screen,
                                (255, 215, 0),  # Gold color for the ladder
                                pygame.Rect(ladder_minimap_x, ladder_minimap_y, minimap_tile_size, minimap_tile_size)
                            )
                    
                    # Draw the player's position as a dot on the minimap
                    player_minimap_x = offset_x + (player.position[0] / 50) * minimap_tile_size  # Assuming tile_size is 50
                    player_minimap_y = offset_y + (player.position[1] / 50) * minimap_tile_size
                    pygame.draw.circle(
                        screen,
                        (255, 0, 0),  # Red color for the player dot
                        (int(player_minimap_x), int(player_minimap_y)),
                        max(2, minimap_tile_size // 4)  # Radius of the dot
                    )
            else:
                # Single player: Display local dungeon minimap
                dungeon.display_minimap(screen, minimap_size=200, player_position=player.position, position=minimap_position)

            # Display the player's moves
            player.draw_moves(screen)

            # Display the floor count
            if hasattr(player, 'network_client') and player.network_client.connected and player.network_client.in_dungeon:
                # Multiplayer: Display server-side dungeon floor count
                if player.network_client.current_dungeon:
                    floor = player.network_client.current_dungeon.floor
                    font = pygame.font.SysFont(None, 36)
                    text = font.render(f"Floor: {floor}", True, (255, 255, 255))
                    screen.blit(text, (20, 20))
            else:
                # Single player: Display local dungeon floor count
                dungeon.display_floor_count(screen)
            
        else:
            # Handle hub logic
            player.handle_input(keys, hub=hub)  # Pass the hub object
            camera.update(player.position)
            screen.fill((0, 199, 0))  # Green background
            hub.