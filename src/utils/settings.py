# Configuration settings for the Pokémon Dungeon Game

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Control mappings
KEYBOARD_CONTROLS = {
    'UP': 'w',
    'DOWN': 's',
    'LEFT': 'a',
    'RIGHT': 'd',
    'ATTACK': 'space',
    'USE_ITEM': 'e'
}

MOUSE_CONTROLS = {
    'LEFT_CLICK': 'left',
    'RIGHT_CLICK': 'right'
}

CONTROLLER_CONTROLS = {
    'MOVE_UP': 'stick_up',
    'MOVE_DOWN': 'stick_down',
    'MOVE_LEFT': 'stick_left',
    'MOVE_RIGHT': 'stick_right',
    'ATTACK': 'button_a',
    'USE_ITEM': 'button_b'
}

# Network settings
SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

# Game settings
MAX_PLAYERS = 4
DUNGEON_SIZE = (10, 10)  # Width, Height
ITEM_LIMIT = 10