import pygame
import os
import json
from game.move import Move
from game.pokemon import Pokemon
from utils.settings import SCREEN_WIDTH, SCREEN_HEIGHT

class TitleScreen:
    def __init__(self, screen, transition_to_game_callback):
        """
        Initialize the title screen with selection options for Pokémon and moves.
        
        :param screen: Pygame screen surface
        :param transition_to_game_callback: Callback function to transition to the game with selected Pokémon
        """
        self.screen = screen
        self.transition_to_game_callback = transition_to_game_callback
        self.font_large = pygame.font.SysFont(None, 72)
        self.font_medium = pygame.font.SysFont(None, 48)
        self.font_small = pygame.font.SysFont(None, 32)
        self.font_tiny = pygame.font.SysFont(None, 24)
        
        # State management
        self.state = "title"  # "title", "pokemon_selection", "move_selection", "username_input"
        
        # Load available starter Pokémon
        self.available_pokemon = self._load_available_pokemon()
        self.selected_pokemon_index = 0
        
        # Move selection
        self.selected_moves = []
        self.move_selection_index = 0
        self.available_moves = []
        
        # Username input
        self.username = "Player"
        self.username_active = False
        self.username_input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 20, 300, 40)
        
        # Multiplayer toggle
        self.multiplayer_enabled = False
        
        # Colors
        self.title_color = (255, 255, 0)  # Yellow
        self.text_color = (255, 255, 255)  # White
        self.selected_color = (255, 215, 0)  # Gold
        self.button_color = (70, 130, 180)  # Steel Blue
        self.button_hover_color = (100, 149, 237)  # Cornflower Blue
        self.input_inactive_color = (100, 100, 100)  # Gray
        self.input_active_color = (200, 200, 200)  # Light Gray
        
        # Buttons
        self.play_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 50, 200, 50)
        self.multiplayer_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 120, 200, 50)
        self.back_button_rect = pygame.Rect(50, SCREEN_HEIGHT - 70, 100, 40)
        self.confirm_button_rect = pygame.Rect(SCREEN_WIDTH - 150, SCREEN_HEIGHT - 70, 100, 40)
        
        # Background
        self.background_color = (25, 25, 112)  # Midnight Blue
        
    def _load_available_pokemon(self):
        """
        Load available starter Pokémon from the data folder.
        
        :return: List of Pokémon data dictionaries
        """
        pokemon_data = []
        data_folder = os.path.join("data", "pokemon")
        
        # List of starter Pokémon to show
        starter_pokemon = ["bulbasaur", "charmander", "squirtle", "pikachu"]
        
        for pokemon_name in starter_pokemon:
            file_path = os.path.join(data_folder, f"{pokemon_name}.json")
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    data = json.load(file)
                    # Add the file name to the data for easy reference
                    data["file_name"] = pokemon_name
                    pokemon_data.append(data)
        
        return pokemon_data
    
    def _load_pokemon_moves(self, pokemon_name):
        """
        Load level 1 moves for the selected Pokémon.
        
        :param pokemon_name: Name of the Pokémon
        :return: List of Move objects
        """
        # Create a temporary Pokémon instance to get its learnable moves
        pokemon = Pokemon.from_json(pokemon_name)
        pokemon.add_learnable_moves_from_json(pokemon_name)
        
        moves = []
        if "1" in pokemon.learnable_moves and pokemon.learnable_moves["1"]:
            level_1_moves = pokemon.learnable_moves["1"]
            for move_name in level_1_moves:
                try:
                    move = Move.from_json(move_name.lower().replace(" ", "-"))
                    moves.append(move)
                except FileNotFoundError:
                    print(f"Could not find move data for {move_name}")
        
        return moves
    
    def handle_events(self, events):
        """
        Handle user input events.
        
        :param events: List of pygame events
        :return: True if the game should continue, False if it should exit
        """
        for event in events:
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
                mouse_pos = pygame.mouse.get_pos()
                
                if self.state == "title":
                    # Check if username input box was clicked
                    if self.username_input_rect.collidepoint(mouse_pos):
                        self.username_active = True
                    else:
                        self.username_active = False
                        
                    if self.play_button_rect.collidepoint(mouse_pos):
                        self.state = "pokemon_selection"
                    elif self.multiplayer_button_rect.collidepoint(mouse_pos):
                        self.multiplayer_enabled = not self.multiplayer_enabled
                
                elif self.state == "pokemon_selection":
                    if self.back_button_rect.collidepoint(mouse_pos):
                        self.state = "title"
                    elif self.confirm_button_rect.collidepoint(mouse_pos):
                        # Load the selected Pokémon's moves
                        selected_pokemon = self.available_pokemon[self.selected_pokemon_index]
                        self.available_moves = self._load_pokemon_moves(selected_pokemon["file_name"])
                        
                        # If the Pokémon has more than 2 moves at level 1, go to move selection
                        if len(self.available_moves) > 2:
                            self.state = "move_selection"
                            self.selected_moves = []
                            self.move_selection_index = 0
                        else:
                            # If 2 or fewer moves, select all available moves
                            self.selected_moves = self.available_moves[:2]
                            self._start_game()
                    
                    # Check if clicked on a Pokémon option
                    for i, pokemon in enumerate(self.available_pokemon):
                        pokemon_rect = pygame.Rect(
                            SCREEN_WIDTH // 2 - 150,
                            150 + i * 80,
                            300,
                            60
                        )
                        if pokemon_rect.collidepoint(mouse_pos):
                            self.selected_pokemon_index = i
                
                elif self.state == "move_selection":
                    if self.back_button_rect.collidepoint(mouse_pos):
                        self.state = "pokemon_selection"
                    elif self.confirm_button_rect.collidepoint(mouse_pos) and len(self.selected_moves) == 2:
                        self._start_game()
                    
                    # Check if clicked on a move option
                    for i, move in enumerate(self.available_moves):
                        move_rect = pygame.Rect(
                            SCREEN_WIDTH // 2 - 200,
                            150 + i * 60,
                            400,
                            50
                        )
                        if move_rect.collidepoint(mouse_pos):
                            # Toggle move selection
                            if move in self.selected_moves:
                                self.selected_moves.remove(move)
                            elif len(self.selected_moves) < 2:
                                self.selected_moves.append(move)
            
            if event.type == pygame.KEYDOWN:
                # Handle username input when active
                if self.state == "title" and self.username_active:
                    if event.key == pygame.K_BACKSPACE:
                        self.username = self.username[:-1]
                    elif event.key == pygame.K_RETURN:
                        self.username_active = False
                    elif len(self.username) < 15:  # Limit username length
                        # Only allow alphanumeric characters and spaces
                        if event.unicode.isalnum() or event.unicode == " ":
                            self.username += event.unicode
                
                elif self.state == "pokemon_selection":
                    if event.key == pygame.K_UP:
                        self.selected_pokemon_index = max(0, self.selected_pokemon_index - 1)
                    elif event.key == pygame.K_DOWN:
                        self.selected_pokemon_index = min(len(self.available_pokemon) - 1, self.selected_pokemon_index + 1)
                    elif event.key == pygame.K_RETURN:
                        # Load the selected Pokémon's moves
                        selected_pokemon = self.available_pokemon[self.selected_pokemon_index]
                        self.available_moves = self._load_pokemon_moves(selected_pokemon["file_name"])
                        
                        # If the Pokémon has more than 2 moves at level 1, go to move selection
                        if len(self.available_moves) > 2:
                            self.state = "move_selection"
                            self.selected_moves = []
                            self.move_selection_index = 0
                        else:
                            # If 2 or fewer moves, select all available moves
                            self.selected_moves = self.available_moves[:2]
                            self._start_game()
                
                elif self.state == "move_selection":
                    if event.key == pygame.K_UP:
                        self.move_selection_index = max(0, self.move_selection_index - 1)
                    elif event.key == pygame.K_DOWN:
                        self.move_selection_index = min(len(self.available_moves) - 1, self.move_selection_index + 1)
                    elif event.key == pygame.K_SPACE:
                        # Toggle move selection
                        move = self.available_moves[self.move_selection_index]
                        if move in self.selected_moves:
                            self.selected_moves.remove(move)
                        elif len(self.selected_moves) < 2:
                            self.selected_moves.append(move)
                    elif event.key == pygame.K_RETURN and len(self.selected_moves) == 2:
                        self._start_game()
        
        return True
    
    def _start_game(self):
        """
        Start the game with the selected Pokémon and moves.
        """
        selected_pokemon = self.available_pokemon[self.selected_pokemon_index]
        self.transition_to_game_callback(selected_pokemon["file_name"], self.selected_moves, self.multiplayer_enabled, self.username)
    
    def draw(self):
        """
        Draw the title screen based on the current state.
        """
        # Fill the background
        self.screen.fill(self.background_color)
        
        if self.state == "title":
            self._draw_title_screen()
        elif self.state == "pokemon_selection":
            self._draw_pokemon_selection()
        elif self.state == "move_selection":
            self._draw_move_selection()
        
        pygame.display.flip()
    
    def _draw_title_screen(self):
        """
        Draw the main title screen.
        """
        # Draw title
        title_text = self.font_large.render("Pokémon Dungeon Game", True, self.title_color)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Draw subtitle
        subtitle_text = self.font_medium.render("Mystery Dungeon Adventure", True, self.text_color)
        subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, 170))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Draw username input field
        username_label = self.font_small.render("Your Name:", True, self.text_color)
        self.screen.blit(username_label, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 50))
        
        # Draw the input box
        input_color = self.input_active_color if self.username_active else self.input_inactive_color
        pygame.draw.rect(self.screen, input_color, self.username_input_rect, border_radius=5)
        
        # Render the username text
        username_text = self.font_small.render(self.username, True, self.text_color)
        # Center the text in the input box
        text_x = self.username_input_rect.x + 10
        text_y = self.username_input_rect.y + (self.username_input_rect.height - username_text.get_height()) // 2
        self.screen.blit(username_text, (text_x, text_y))
        
        # Draw play button
        pygame.draw.rect(self.screen, self.button_color, self.play_button_rect, border_radius=10)
        play_text = self.font_medium.render("Play", True, self.text_color)
        play_text_rect = play_text.get_rect(center=self.play_button_rect.center)
        self.screen.blit(play_text, play_text_rect)
        
        # Draw multiplayer toggle button
        button_color = self.button_hover_color if self.multiplayer_enabled else self.button_color
        pygame.draw.rect(self.screen, button_color, self.multiplayer_button_rect, border_radius=10)
        multiplayer_text = self.font_medium.render(f"Multiplayer: {'On' if self.multiplayer_enabled else 'Off'}", True, self.text_color)
        multiplayer_text_rect = multiplayer_text.get_rect(center=self.multiplayer_button_rect.center)
        self.screen.blit(multiplayer_text, multiplayer_text_rect)
        
        # Draw instructions
        instructions_text = self.font_tiny.render("Enter your name and press Play to start your adventure!", True, self.text_color)
        instructions_rect = instructions_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        self.screen.blit(instructions_text, instructions_rect)
    
    def _draw_pokemon_selection(self):
        """
        Draw the Pokémon selection screen.
        """
        # Draw title
        title_text = self.font_medium.render("Choose Your Pokémon", True, self.title_color)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title_text, title_rect)
        
        # Draw Pokémon options
        for i, pokemon in enumerate(self.available_pokemon):
            # Create a rectangle for the Pokémon option
            pokemon_rect = pygame.Rect(
                SCREEN_WIDTH // 2 - 150,
                150 + i * 80,
                300,
                60
            )
            
            # Highlight selected Pokémon
            color = self.selected_color if i == self.selected_pokemon_index else self.button_color
            pygame.draw.rect(self.screen, color, pokemon_rect, border_radius=10)
            
            # Try to load and display Pokémon sprite
            try:
                # Create a temporary animation object to get the sprite
                from utils.animation import SpriteAnimation
                temp_animation = SpriteAnimation(pokemon["file_name"], "Idle")
                sprite = temp_animation.get_current_frame()
                if sprite:
                    # Scale sprite to fit nicely
                    sprite = pygame.transform.scale(sprite, (48, 48))
                    sprite_rect = sprite.get_rect(midleft=(pokemon_rect.left + 20, pokemon_rect.centery))
                    self.screen.blit(sprite, sprite_rect)
            except Exception as e:
                print(f"Could not load sprite for {pokemon['name']}: {e}")
            
            # Draw Pokémon name
            name_text = self.font_small.render(pokemon["name"], True, self.text_color)
            name_rect = name_text.get_rect(midleft=(pokemon_rect.left + 80, pokemon_rect.centery - 10))
            self.screen.blit(name_text, name_rect)
            
            # Draw Pokémon type(s)
            types_text = self.font_tiny.render(", ".join(pokemon["types"]), True, self.text_color)
            types_rect = types_text.get_rect(midleft=(pokemon_rect.left + 80, pokemon_rect.centery + 15))
            self.screen.blit(types_text, types_rect)
        
        # Draw back button
        pygame.draw.rect(self.screen, self.button_color, self.back_button_rect, border_radius=5)
        back_text = self.font_small.render("Back", True, self.text_color)
        back_text_rect = back_text.get_rect(center=self.back_button_rect.center)
        self.screen.blit(back_text, back_text_rect)
        
        # Draw confirm button
        pygame.draw.rect(self.screen, self.button_color, self.confirm_button_rect, border_radius=5)
        confirm_text = self.font_small.render("Select", True, self.text_color)
        confirm_text_rect = confirm_text.get_rect(center=self.confirm_button_rect.center)
        self.screen.blit(confirm_text, confirm_text_rect)
        
        # Draw instructions
        instructions_text = self.font_tiny.render("Use arrow keys to navigate, Enter to select", True, self.text_color)
        instructions_rect = instructions_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20))
        self.screen.blit(instructions_text, instructions_rect)
    
    def _draw_move_selection(self):
        """
        Draw the move selection screen.
        """
        # Draw title
        title_text = self.font_medium.render("Choose Two Starting Moves", True, self.title_color)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title_text, title_rect)
        
        # Draw selected Pokémon info
        selected_pokemon = self.available_pokemon[self.selected_pokemon_index]
        pokemon_text = self.font_small.render(f"Pokémon: {selected_pokemon['name']}", True, self.text_color)
        pokemon_rect = pokemon_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(pokemon_text, pokemon_rect)
        
        # Draw move options
        for i, move in enumerate(self.available_moves):
            # Create a rectangle for the move option
            move_rect = pygame.Rect(
                SCREEN_WIDTH // 2 - 200,
                150 + i * 60,
                400,
                50
            )
            
            # Highlight selected moves and current selection
            if move in self.selected_moves:
                color = self.selected_color
            elif i == self.move_selection_index:
                color = self.button_hover_color
            else:
                color = self.button_color
            
            pygame.draw.rect(self.screen, color, move_rect, border_radius=10)
            
            # Draw move name
            name_text = self.font_small.render(move.name, True, self.text_color)
            name_rect = name_text.get_rect(midleft=(move_rect.left + 20, move_rect.centery))
            self.screen.blit(name_text, name_rect)
            
            # Draw move type and power
            if move.power > 0:
                details_text = self.font_tiny.render(
                    f"Type: {move.move_type} | Power: {move.power} | {move.category}",
                    True, self.text_color
                )
            else:
                details_text = self.font_tiny.render(
                    f"Type: {move.move_type} | Status | {move.category}",
                    True, self.text_color
                )
            details_rect = details_text.get_rect(midright=(move_rect.right - 20, move_rect.centery))
            self.screen.blit(details_text, details_rect)
        
        # Draw back button
        pygame.draw.rect(self.screen, self.button_color, self.back_button_rect, border_radius=5)
        back_text = self.font_small.render("Back", True, self.text_color)
        back_text_rect = back_text.get_rect(center=self.back_button_rect.center)
        self.screen.blit(back_text, back_text_rect)
        
        # Draw confirm button (only enabled if 2 moves are selected)
        confirm_color = self.button_color if len(self.selected_moves) == 2 else (100, 100, 100)
        pygame.draw.rect(self.screen, confirm_color, self.confirm_button_rect, border_radius=5)
        confirm_text = self.font_small.render("Confirm", True, self.text_color)
        confirm_text_rect = confirm_text.get_rect(center=self.confirm_button_rect.center)
        self.screen.blit(confirm_text, confirm_text_rect)
        
        # Draw selection count
        count_text = self.font_small.render(f"Selected: {len(self.selected_moves)}/2", True, self.text_color)
        count_rect = count_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
        self.screen.blit(count_text, count_rect)
        
        # Draw instructions
        instructions_text = self.font_tiny.render("Use arrow keys to navigate, Space to select/deselect, Enter to confirm", True, self.text_color)
        instructions_rect = instructions_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20))
        self.screen.blit(instructions_text, instructions_rect)