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
        # Apply the camera offset to a position
        return position[0] - self.offset_x, position[1] - self.offset_y