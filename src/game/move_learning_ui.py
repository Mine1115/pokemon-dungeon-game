import pygame

class MoveLearningUI:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.Font(None, 36)
        self.selected_index = 0
        self.max_options = 5  # 4 current moves + 1 for "Don't learn"
        
        # Colors
        self.text_color = (255, 255, 255)
        self.selected_color = (255, 255, 0)
        self.background_color = (0, 0, 0, 200)  # Semi-transparent black
        
        # Create a surface for the menu background
        self.background_surface = pygame.Surface((screen_width, screen_height))
        self.background_surface.fill((0, 0, 0))
        self.background_surface.set_alpha(200)
    
    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % self.max_options
            elif event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % self.max_options
            elif event.key == pygame.K_RETURN:
                return self.selected_index
        return None
    
    def draw(self, screen, pokemon, new_move):
        # Draw semi-transparent background
        screen.blit(self.background_surface, (0, 0))
        
        # Draw title
        title_text = f"{pokemon.name} is trying to learn {new_move.name}"
        title_surface = self.font.render(title_text, True, self.text_color)
        screen.blit(title_surface, (self.screen_width // 2 - title_surface.get_width() // 2, 100))
        
        subtitle_text = "But it already knows four moves!"
        subtitle_surface = self.font.render(subtitle_text, True, self.text_color)
        screen.blit(subtitle_surface, (self.screen_width // 2 - subtitle_surface.get_width() // 2, 150))
        
        # Draw current moves
        y_position = 250
        for i, move in enumerate(pokemon.current_moves):
            color = self.selected_color if i == self.selected_index else self.text_color
            move_text = f"{i + 1}. {move.name}"
            move_surface = self.font.render(move_text, True, color)
            screen.blit(move_surface, (self.screen_width // 2 - move_surface.get_width() // 2, y_position))
            y_position += 50
        
        # Draw "Don't learn" option
        color = self.selected_color if 4 == self.selected_index else self.text_color
        dont_learn_text = f"5. Don't learn {new_move.name}"
        dont_learn_surface = self.font.render(dont_learn_text, True, color)
        screen.blit(dont_learn_surface, (self.screen_width // 2 - dont_learn_surface.get_width() // 2, y_position))