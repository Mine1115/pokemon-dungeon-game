def load_image(file_path):
    """Load an image from the specified file path."""
    import pygame
    try:
        image = pygame.image.load(file_path)
        return image
    except pygame.error as e:
        print(f"Unable to load image: {file_path}. Error: {e}")
        return None

def load_sound(file_path):
    """Load a sound from the specified file path."""
    import pygame
    try:
        sound = pygame.mixer.Sound(file_path)
        return sound
    except pygame.error as e:
        print(f"Unable to load sound: {file_path}. Error: {e}")
        return None

def save_game_state(game_state, file_path):
    """Save the current game state to a file."""
    import json
    with open(file_path, 'w') as f:
        json.dump(game_state, f)

def load_game_state(file_path):
    """Load the game state from a file."""
    import json
    try:
        with open(file_path, 'r') as f:
            game_state = json.load(f)
            return game_state
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Unable to load game state from {file_path}. Error: {e}")
        return None

def combine_moves(move1, move2):
    """Combine two moves into a single action."""
    return f"{move1} + {move2}"