import pygame
import xml.etree.ElementTree as ET
import os

class SpriteAnimation:
    def __init__(self, pokemon_name, animation_name="Idle", sprite_offset=(0, 0)):
        """
        Initialize a sprite animation for a Pokémon.
        
        Args:
            pokemon_name (str): The name of the Pokémon (e.g., "Pikachu", "Zubat")
            animation_name (str): The name of the animation to use (e.g., "Idle", "Walk", "Attack")
            sprite_offset (tuple): Offset (x, y) for fine-tuning sprite positioning
        """
        self.pokemon_name = pokemon_name
        self.animation_name = animation_name
        self.frame_index = 0
        self.animation_timer = 0
        self.animations = {}
        self.current_animation = None
        self.sprite_sheet = None
        self.direction = "right"  # Default direction (right, left, up, down)
        self.last_animation_state = ""  # Track the last animation state to prevent flickering
        if sprite_offset == (0, 0):
            if self.pokemon_name == "Pikachu":
                self.sprite_offset = (-18, -26)
            elif self.pokemon_name == "Zubat":
                self.sprite_offset = (17, 41)
            elif self.pokemon_name == "Bulbasaur":
                self.sprite_offset = (-18, -26)
            elif self.pokemon_name == "Charmander":
                self.sprite_offset = (-18, -26)
            elif self.pokemon_name == "Squirtle":
                self.sprite_offset = (-18, -26)
        else:
            self.sprite_offset = sprite_offset  # Offset for fine-tuning sprite positioning
        
        # Load the animation data and sprite sheet
        self.load_animation_data()
        
    def load_animation_data(self):
        """
        Load animation data from the AnimData.xml file for the Pokémon.
        """
        base_path = os.path.join(os.getcwd(), f"assets/pokemon/{self.pokemon_name}")
        xml_path = os.path.join(base_path, "AnimData.xml")
        
        try:
            # Parse the XML file
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Get all animations
            for anim in root.findall('./Anims/Anim'):
                name = anim.find('Name').text
                
                # Check if this animation is a copy of another
                copy_of = anim.find('CopyOf')
                if copy_of is not None:
                    # This animation is a copy of another, we'll handle it later
                    continue
                
                # Get animation properties
                frame_width = int(anim.find('FrameWidth').text)
                frame_height = int(anim.find('FrameHeight').text)
                
                # Get frame durations
                durations = []
                for duration in anim.findall('./Durations/Duration'):
                    durations.append(int(duration.text))
                
                # Load the sprite sheet for this animation
                sprite_sheet_path = os.path.join(base_path, f"{name}-Anim.png")
                sprite_sheet = pygame.image.load(sprite_sheet_path)
                
                # Calculate total frames based on durations
                total_frames = len(durations)
                if total_frames == 0:
                    total_frames = sprite_sheet.get_width() // frame_width
                
                # Don't scale the sprite sheet - use it as is
                # The original sprite sheets already contain all the frames needed
                
                # Get hit frame and rush frame data for attack animations
                hit_frame = anim.find('HitFrame')
                rush_frame = anim.find('RushFrame')
                return_frame = anim.find('ReturnFrame')
                
                # Store the animation data
                self.animations[name] = {
                    'sprite_sheet': sprite_sheet,
                    'frame_width': frame_width,
                    'frame_height': frame_height,
                    'durations': durations,
                    'total_frames': total_frames,
                    #'hit_frame': int(hit_frame.text) if hit_frame is not None else None,
                    #'rush_frame': int(rush_frame.text) if rush_frame is not None else None,
                    #'return_frame': int(return_frame.text) if return_frame is not None else None
                }
            
            # Handle animations that are copies of others
            for anim in root.findall('./Anims/Anim'):
                copy_of = anim.find('CopyOf')
                if copy_of is not None:
                    name = anim.find('Name').text
                    original_name = copy_of.text
                    if original_name in self.animations:
                        self.animations[name] = self.animations[original_name].copy()
            
            # Set the current animation
            if self.animation_name in self.animations:
                self.current_animation = self.animations[self.animation_name]
            elif len(self.animations) > 0:
                # Default to the first animation if the requested one doesn't exist
                self.animation_name = next(iter(self.animations))
                self.current_animation = self.animations[self.animation_name]
            
        except Exception as e:
            print(f"Error loading animation data for {self.pokemon_name}: {e}")
    
    def update(self, dt=1):
        """
        Update the animation frame based on the elapsed time.
        
        Args:
            dt (float): Delta time in frames (default is 1 frame)
        """
        if not self.current_animation:
            return
        
        # Increment the animation timer
        self.animation_timer += dt
        
        # Check if it's time to advance to the next frame
        if self.animation_timer >= self.current_animation['durations'][self.frame_index]:
            self.animation_timer = 0
            self.frame_index = (self.frame_index + 1) % self.current_animation['total_frames']
    
    def set_direction(self, direction_vector):
        """
        Set the direction of the sprite based on movement vector.
        
        Args:
            direction_vector (tuple): A tuple containing (dx, dy) movement direction
        """
        dx, dy = direction_vector
        
        # Store the previous direction to detect changes
        previous_direction = self.direction
        
        # Handle diagonal movement
        if dx > 0 and dy > 0:
            self.direction = "down_right"
        elif dx > 0 and dy < 0:
            self.direction = "up_right"
        elif dx < 0 and dy > 0:
            self.direction = "down_left"
        elif dx < 0 and dy < 0:
            self.direction = "up_left"
        elif dx > 0:
            self.direction = "right"
        elif dx < 0:
            self.direction = "left"
        elif dy > 0:
            self.direction = "down"
        elif dy < 0:
            self.direction = "up"
            
        # If direction changed to up or side, we might need to change animation
        if previous_direction != self.direction and self.direction in ["up", "left", "right"]:
            # We'll handle the animation change in get_current_frame
            pass
    
    def set_animation(self, animation_name):
        """
        Change the current animation.
        
        Args:
            animation_name (str): The name of the animation to switch to
        """
        # Only change animation if it's different from the current one and not the same as the last animation state
        # This prevents flickering when rapidly switching between animation states
        if animation_name in self.animations and (animation_name != self.animation_name or animation_name != self.last_animation_state):
            self.last_animation_state = self.animation_name
            self.animation_name = animation_name
            self.current_animation = self.animations[animation_name]
            
            # Only reset frame index and timer when changing to a completely different animation
            # This prevents flickering during attack animations
            if self.last_animation_state != animation_name:
                self.frame_index = 0
                self.animation_timer = 0
    
    def get_current_frame(self, scale_factor=2.0):
        """
        Get the current frame of the animation as a surface.
        
        Args:
            scale_factor (float): Factor to scale the sprite (default is 2.0)
                                  Higher values make sprites larger
        
        Returns:
            pygame.Surface: The current frame as a surface
        """
        if not self.current_animation:
            return None
        
        # Calculate the position of the frame in the sprite sheet
        frame_width = self.current_animation['frame_width']
        frame_height = self.current_animation['frame_height']
        sprite_sheet = self.current_animation['sprite_sheet']
        sprite_sheet_path = os.path.join("assets/pokemon", self.pokemon_name)
        
        # Create a new surface for the frame with alpha channel to ensure transparency
        frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
        
        # Calculate the position of the frame in the sprite sheet
        frame_x = self.frame_index * frame_width
        frame_y = 0
        
        # Handle directional animations for walking and other directional animations
        if self.animation_name in ["Walk", "Idle"]:
            # Calculate the row based on direction
            direction_to_row = {
                "down": 0,        # First row for down animation
                "down_right": 1, # Second row for down-right animation
                "right": 2,      # Third row for right animation
                "up_right": 3,   # Fourth row for up-right animation
                "up": 4,         # Fifth row for up animation
                "up_left": 5,    # Sixth row for up-left animation
                "left": 6,       # Seventh row for left animation
                "down_left": 7   # Eighth row for down-left animation
            }
            frame_y = frame_height * direction_to_row.get(self.direction, 0)  # Default to down if direction not found
            
            # Blit the frame from the walk animation sprite sheet
            frame.blit(sprite_sheet, (0, 0), (frame_x, frame_y, frame_width, frame_height))
            
            # Load and apply wall animation if available
            wall_anim_path = os.path.join(os.path.dirname(sprite_sheet_path), "Walk-Anim.png")
            if os.path.exists(wall_anim_path):
                wall_sprite_sheet = pygame.image.load(wall_anim_path)
                # Wall animation is typically on the same row as the direction
                frame.blit(wall_sprite_sheet, (0, 0), (frame_x, frame_y, frame_width, frame_height))
            
            # Scale the frame to match collider size with the provided scale factor
            collider_size = (int(frame_width * scale_factor), int(frame_height * scale_factor))  # Default size with scale factor
            if hasattr(self, 'collider_size'):
                collider_size = (int(self.collider_size[0] * scale_factor / 2), int(self.collider_size[1] * scale_factor / 2))
            scaled_frame = pygame.transform.smoothscale(frame, collider_size)
            return scaled_frame

        # For side views (left/right), we'll use the normal animation frames but flip horizontally for left
        
        # We'll flip the sprite horizontally if facing left
        flip_horizontal = self.direction == "left"
        
        # Clear the frame surface before drawing to prevent stacking
        frame.fill((0, 0, 0, 0))  # Fill with transparent color
        
        # Extract the frame from the sprite sheet
        frame.blit(sprite_sheet, (0, 0), (frame_x, frame_y, frame_width, frame_height))
        
        # Flip the frame horizontally if facing left
        if flip_horizontal:
            frame = pygame.transform.flip(frame, True, False)
        
        # Scale the frame to match collider size with the provided scale factor
        collider_size = (int(frame_width * scale_factor), int(frame_height * scale_factor))  # Default size with scale factor
        if hasattr(self, 'collider_size'):
            collider_size = (int(self.collider_size[0] * scale_factor / 2), int(self.collider_size[1] * scale_factor / 2))
        scaled_frame = pygame.transform.smoothscale(frame, collider_size)
        
        return scaled_frame