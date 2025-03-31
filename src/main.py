import pygame
import asyncio
import threading
from game.hub import Hub
from game.player import Player
from game.camera import Camera
from game.dungeon import Dungeon
from game.title_screen import TitleScreen
from game.move import Move
from game.single_player_loop import SinglePlayerLoop
from game.multiplayer_loop import MultiplayerLoop
from utils.settings import SCREEN_WIDTH, SCREEN_HEIGHT

async def main():
    pygame.init()  # Initialize Pygame
    pygame.font.init()  # Initialize Pygame font system

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Pokemon Dungeon Game")

    def start_game_with_pokemon(pokemon_name, selected_moves, multiplayer_enabled, username):
        nonlocal player, in_title_screen, game_loop
        
        # Create player with selected Pokémon
        player = Player(name=username, health=100, position=(500, 500), pokemon_name=pokemon_name)
        
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
        
        # Initialize the appropriate game loop based on multiplayer setting
        if multiplayer_enabled:
            # Initialize network client for multiplayer
            from game.network_client import NetworkClient
            network_client = NetworkClient()
            if network_client.connect_to_server():
                network_client.join_game(username, pokemon_name, player.position[0], player.position[1])
                player.network_client = network_client
                # Create multiplayer game loop
                game_loop = MultiplayerLoop(screen, player)
            else:
                print("Failed to connect to multiplayer server")
                # Fall back to single player if connection fails
                game_loop = SinglePlayerLoop(screen, player)
        else:
            # Create single player game loop
            game_loop = SinglePlayerLoop(screen, player)
        
        # Exit title screen
        in_title_screen = False

    # Initialize title screen
    title_screen = TitleScreen(screen, start_game_with_pokemon)
    in_title_screen = True
    
    # These will be initialized when the player selects a Pokémon
    player = None
    camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)  # Initialize camera
    dungeon = None
    game_loop = None  # Initialize game_loop variable
    
    # Define the function to generate a new dungeon
    def generate_new_dungeon():
        nonlocal dungeon, player
        if dungeon:
            floor = dungeon.floor + 1  # Increment the floor count
        else:
            floor = 1  # Start at floor 1
            
        dungeon = Dungeon(2000, 2000, 50, floor=floor)  # Generate a new dungeon floor
        spawn_point = dungeon.get_player_spawn()
        if spawn_point and player:
            player.position = list(spawn_point)  # Spawn the player in the first room
    
    # Initialize hub with the transition function
    hub = Hub(lambda: setattr(locals(), 'in_dungeon', True) or generate_new_dungeon())

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
                    # Don't use await since update_dungeon is not an async function
                    player.network_client.update_dungeon()
                
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
                                if hasattr(server_dungeon, 'spawn_point'):
                                    # Validate that the spawn point is on a walkable tile
                                    spawn_x, spawn_y = server_dungeon.spawn_point
                                    if dungeon.is_walkable(spawn_x, spawn_y):
                                        player.position = list(server_dungeon.spawn_point)
                                    else:
                                        # Find a valid spawn point if the server-provided one is invalid
                                        valid_spawn = dungeon.find_nearest_valid_spawn(spawn_x, spawn_y)
                                        player.position = list(valid_spawn)
                                        print(f"Found valid spawn point at {valid_spawn}")
                                else:
                                    # Use local spawn point finding logic
                                    spawn_point = dungeon.get_player_spawn()
                                    if spawn_point:
                                        player.position = list(spawn_point)
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
                    # Ensure we have a valid spawn point before transitioning
                    if player.network_client.current_dungeon:
                        spawn_point = player.network_client.current_dungeon.get_player_spawn()
                        if spawn_point:
                            player.position = list(spawn_point)
                    player.network_client.next_floor()
            else:
                # Single player: Use local dungeon logic
                # Update explored tiles
                dungeon.update_explored(player.position)

                # Update wild Pokémon behavior
                dungeon.update_wild_pokemon(player)
                
                # Update wild Pokémon from server in multiplayer mode
                if hasattr(player, 'network_client') and player.network_client.connected:
                    server_wild_pokemon = player.network_client.get_wild_pokemon()
                    if server_wild_pokemon and dungeon:
                        dungeon.wild_pokemon = server_wild_pokemon

                # Check for interaction with the ladder
                player_rect = pygame.Rect(player.position, player.size)
                ladder_rect = pygame.Rect(dungeon.ladder_position, (dungeon.tile_size, dungeon.tile_size))
                if player_rect.colliderect(ladder_rect):
                    print("Descending to the next floor...")
                    # Store current position to prevent spawning in walls
                    old_position = list(player.position)
                    generate_new_dungeon()
                    # Validate spawn position
                    if not dungeon.is_walkable(player.position[0], player.position[1]):
                        # Try to find a valid spawn point
                        spawn_point = dungeon.get_player_spawn()
                        if spawn_point:
                            player.position = list(spawn_point)
                        else:
                            # If no valid spawn point found, reset to previous position
                            player.position = old_position

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
            
            # Handle dungeon display
            if dungeon:
                # In multiplayer mode, only use server dungeon data
                if hasattr(player, 'network_client') and player.network_client.connected:
                    if player.network_client.current_dungeon:
                        dungeon.display(screen, camera)
                else:
                    # Single player mode
                    dungeon.display(screen, camera)
            else:
                # If dungeon isn't initialized yet, draw a loading message
                font = pygame.font.SysFont(None, 36)
                loading_text = font.render("Loading dungeon...", True, (255, 255, 255))
                text_rect = loading_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
                screen.blit(loading_text, text_rect)
                
            # Handle input and collision detection
            player.handle_input(keys, dungeon=dungeon)  # Pass dungeon for collision detection
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
            try:
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
            except Exception as e:
                # If anything fails during rendering, show an error message instead of a black screen
                print(f"Error rendering dungeon: {e}")
                font = pygame.font.SysFont(None, 36)
                error_text = font.render("Error rendering dungeon", True, (255, 0, 0))
                text_rect = error_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
                screen.blit(error_text, text_rect)
                
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
            hub.display(screen, camera)  # Display the hub
            
            # Update player position on the server if in multiplayer mode
            if hasattr(player, 'network_client') and player.network_client.connected:
                # Send position update to server
                player.network_client.update_position(player.position[0], player.position[1], 
                                                     player.last_direction[0], player.last_direction[1])
                
                # Display other players in the hub
                other_players = player.network_client.get_other_players()
                for other_player in other_players:
                    # Only display players who are not in a dungeon and not the local player
                    if not other_player.in_dungeon and other_player.id != player.network_client.player_id:
                        hub.draw_other_player(screen, camera, other_player, player.network_client.player_id)
            
            player.draw(screen, camera)  # Draw the player
            
            # Check for interactions with hub objects
            player.check_interactions(hub)
            
        # Update the display
        pygame.display.flip()
        clock.tick(60)  # Maintain 60 FPS

# Run the main function using asyncio
if __name__ == "__main__":
    asyncio.run(main())