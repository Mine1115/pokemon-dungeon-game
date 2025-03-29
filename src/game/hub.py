import pygame
from game.mission_board import MissionBoard

class Hub:
    def __init__(self, transition_to_dungeon_callback):
        self.transition_to_dungeon_callback = transition_to_dungeon_callback
        self.color = (100, 100, 100)  # Example: Gray hub background
        self.mission_board = MissionBoard()
        self.width = 2000  # Example: Hub width
        self.height = 2000  # Example: Hub height
        self.portal_position = (1000, 500)  # Position of the dungeon portal
        self.portal_rect = pygame.Rect(self.portal_position[0], self.portal_position[1], 50, 50)
        # Dictionary to store animations for other players
        self.other_player_animations = {}

        # List of objects in the hub
        self.objects = [
            {"name": "Shop", "position": (300, 300), "size": (100, 100), "color": (255, 0, 0), "interactable": True, "collidable": True},
            {"name": "Mission Board", "position": (500, 800), "size": (150, 100), "color": (0, 0, 255), "interactable": True, "collidable": True},
            {"name": "Tree", "position": (700, 400), "size": (50, 50), "color": (0, 255, 0), "interactable": False, "collidable": True},
            {"name": "Decoration", "position": (1000, 600), "size": (200, 200), "color": (255, 255, 0), "interactable": False, "collidable": False},  # Example non-collidable object
            {"name": "Dungeon Entrance", "position": (1500, 1500), "size": (100, 100), "color": (128, 0, 128), "interactable": True, "collidable": True, "action": transition_to_dungeon_callback},  # Dungeon entrance
        ]

    def check_collision(self, player_rect):
        for obj in self.objects:
            if not obj.get("collidable", True):  # Skip non-collidable objects
                continue
            obj_rect = pygame.Rect(obj["position"], obj["size"])
            if player_rect.colliderect(obj_rect):
                return obj  # Return the object the player collided with
        return None

    def display(self, screen, camera):
        # Draw the hub background with camera offset
        pygame.draw.rect(
            screen,
            self.color,
            pygame.Rect(-camera.offset_x, -camera.offset_y, self.width, self.height)
        )

        # Draw all objects in the hub
        for obj in self.objects:
            obj_position = (obj["position"][0] - camera.offset_x, obj["position"][1] - camera.offset_y)
            pygame.draw.rect(screen, obj["color"], pygame.Rect(obj_position, obj["size"]))
            
        # Draw the portal
        portal_screen_pos = (self.portal_position[0] - camera.offset_x, self.portal_position[1] - camera.offset_y)
        pygame.draw.rect(screen, (0, 0, 255), pygame.Rect(portal_screen_pos[0], portal_screen_pos[1], 50, 50))

    def draw_other_player(self, screen, camera, other_player, player_id):
        """Draw another player in the hub area.
        
        Args:
            screen: Pygame screen surface
            camera: Camera instance for position calculations
            other_player: NetworkPlayer instance containing position and info
        """
        # Skip rendering if this is the local player
        if hasattr(other_player, 'id') and hasattr(other_player, 'network_client') and other_player.id == player_id:
            return
            
        # Calculate screen position
        screen_pos = (other_player.x - camera.offset_x, other_player.y - camera.offset_y)
        
        # Get or create animation for this player
        if other_player.id not in self.other_player_animations:
            from utils.animation import SpriteAnimation
            # Create a new animation for this player's Pokémon
            self.other_player_animations[other_player.id] = SpriteAnimation(other_player.pokemon, "Idle")
        
        # Update the animation and direction
        animation = self.other_player_animations[other_player.id]
        # Update direction based on last_direction from network data
        if hasattr(other_player, 'direction_x') and hasattr(other_player, 'direction_y'):
            animation.set_direction((other_player.direction_x, other_player.direction_y))
        animation.update()
        
        # Get the current frame
        current_frame = animation.get_current_frame(scale_factor=2.0)
        
        if current_frame:
            # Apply sprite offset
            # Get sprite offset from the animation instance
            offset_x, offset_y = getattr(animation, 'sprite_offset', (-14, -10))  # Default offset if not set
            adjusted_pos = (screen_pos[0] + offset_x, screen_pos[1] + offset_y)
            
            # Draw the sprite
            screen.blit(current_frame, adjusted_pos)
        else:
            # Fallback to a colored rectangle if animation failed
            pygame.draw.rect(screen, (0, 255, 0), pygame.Rect(screen_pos, (32, 32)))
        
        # Draw player name above sprite
        font = pygame.font.SysFont(None, 24)
        name_text = font.render(other_player.name, True, (255, 255, 255))
        name_pos = (screen_pos[0] + 16 - name_text.get_width() // 2, screen_pos[1] - 20)
        screen.blit(name_text, name_pos)