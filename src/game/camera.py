class Camera:
    def __init__(self, width, height):
        self.offset_x = 0
        self.offset_y = 0
        self.width = width
        self.height = height

    def update(self, player_position):
        # Center the camera on the player
        self.offset_x = player_position[0] - self.width // 2
        self.offset_y = player_position[1] - self.height // 2

    def apply(self, position):
        """Convert world coordinates to screen coordinates."""
        # Ensure the position is properly offset and visible on screen
        screen_x = position[0] - self.offset_x
        screen_y = position[1] - self.offset_y
        return (int(screen_x), int(screen_y))  # Convert to integers to prevent floating point rendering issues