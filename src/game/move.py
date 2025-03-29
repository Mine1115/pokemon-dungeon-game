import pygame
import json
import os
import random
from game.combat import calculate_damage

class Move:
    def __init__(self, name, move_type, power, accuracy, range_type, category, effects=None, pp=None, description=None):
        """
        Initialize a move with its properties.
        :param name: Name of the move (e.g., "Thunderbolt").
        :param move_type: Type of the move (e.g., "Electric").
        :param power: Power of the move (e.g., 90).
        :param accuracy: Accuracy of the move (e.g., 100 for 100% accuracy).
        :param range_type: "Ranged" or "Melee".
        :param category: "Physical", "Special", or "Status".
        :param effects: Dictionary of effects that trigger at different points (e.g., {"on_activate": func, "before_hit": func}).
        :param pp: Power Points of the move (number of times it can be used).
        :param description: Description of the move.
        """
        self.name = name
        self.move_type = move_type  # Type of the move (e.g., "Electric")
        self.power = power  # Power of the move
        self.accuracy = accuracy  # Accuracy of the move (percentage)
        self.range_type = range_type  # "Ranged" or "Melee"
        self.category = category  # "Physical", "Special", or "Status"
        self.effects = effects or {}
        self.pp = pp  # Power Points (number of times the move can be used)
        self.description = description  # Description of the move
        
    @classmethod
    def from_json(cls, move_name):
        """
        Create a Move instance from a JSON file in the predefined data folder.
        :param move_name: The name of the move (e.g., "thunderbolt").
        :return: A Move instance.
        """
        # Define the path to the data folder
        data_folder = os.path.join("data", "moves")
        # Convert move name to lowercase and replace spaces with hyphens for file naming
        file_name = move_name.lower().replace(" ", "-")
        file_path = os.path.join(data_folder, f"{file_name}.json")

        # Load the JSON file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Move data file not found: {file_path}")

        with open(file_path, "r") as file:
            data = json.load(file)

        # Create and return the Move instance
        return cls(
            name=data["name"],
            move_type=data["type"],
            power=data["power"],
            accuracy=data["accuracy"],
            range_type=data["range_type"],
            category=data["category"],
            effects=data.get("effects", {}),
            pp=data.get("pp"),
            description=data.get("description")
        )

    def trigger_effect(self, effect_type, attacker=None, defender=None, context=None):
        if not self.effects or effect_type not in self.effects:
            return None

        effect_context = {
            "attacker": attacker,
            "defender": defender,
            "move": self
        }
        if context:
            effect_context.update(context)
        
        if isinstance(self.effects[effect_type], dict):
            effect_data = self.effects[effect_type]
            
            # Handle healing effects
            if "heal_percent" in effect_data and context and "damage" in context:
                heal_amount = int(context["damage"] * effect_data["heal_percent"])
                if attacker and hasattr(attacker, "pokemon"):
                    attacker.pokemon.current_hp = min(
                        attacker.pokemon.current_hp + heal_amount,
                        attacker.pokemon.stats["HP"]
                    )
                    print(f"{attacker.pokemon.name} restored {heal_amount} HP!")
            
            # Handle status effects
            if defender and hasattr(defender, "pokemon"):
                if not hasattr(defender.pokemon, "status"):
                    defender.pokemon.status = None
                
                for status_type, chance in {
                    "paralysis": effect_data.get("paralysis_chance", 0),
                    "confusion": effect_data.get("confusion_chance", 0),
                    "poison": effect_data.get("poison_chance", 0),
                    "bad_poison": effect_data.get("bad_poison_chance", 0),
                    "sleep": effect_data.get("sleep_chance", 0),
                    "freeze": effect_data.get("freeze_chance", 0),
                    "burn": effect_data.get("burn_chance", 0)
                }.items():
                    if chance > 0 and random.randint(1, 100) <= chance:
                        defender.pokemon.status = status_type
                        
                        # Apply status-specific effects
                        if status_type == "paralysis":
                            if "Speed" in defender.pokemon.stats:
                                defender.pokemon.stats["Speed"] = max(1, int(defender.pokemon.stats["Speed"] * 0.5))
                            print(f"{defender.pokemon.name} was paralyzed!")
                        elif status_type == "burn":
                            if "Attack" in defender.pokemon.stats:
                                defender.pokemon.stats["Attack"] = max(1, int(defender.pokemon.stats["Attack"] * 0.5))
                            print(f"{defender.pokemon.name} was burned!")
                        else:
                            status_messages = {
                                "confusion": "became confused",
                                "poison": "was poisoned",
                                "bad_poison": "was badly poisoned",
                                "sleep": "fell asleep",
                                "freeze": "was frozen solid"
                            }
                            print(f"{defender.pokemon.name} {status_messages[status_type]}!")
                        break  # Only apply one status effect
                
                # Handle flinch
                if "flinch_chance" in effect_data:
                    if random.randint(1, 100) <= effect_data["flinch_chance"]:
                        print(f"{defender.pokemon.name} flinched!")
                
                # Handle stat changes
                if "stat_changes" in effect_data:
                    for stat, change in effect_data["stat_changes"].items():
                        if stat in defender.pokemon.stats:
                            defender.pokemon.stats[stat] = max(1, int(defender.pokemon.stats[stat] * (1 + change)))
                            direction = "raised" if change > 0 else "lowered"
                            print(f"{defender.pokemon.name}'s {stat} was {direction}!")
            
            # Handle special move effects
            if self.name == "Venoshock" and defender and hasattr(defender, "pokemon") and \
               hasattr(defender.pokemon, "status") and defender.pokemon.status in ["poison", "bad_poison"] and \
               context and "damage" in context:
                context["damage"] *= 2
                print(f"{self.name} did double damage because {defender.pokemon.name} is poisoned!")
                return context["damage"]
            
            elif (self.name == "Leech Life" or self.name == "Absorb") and attacker and defender and context and "damage" in context:
                heal_amount = int(context["damage"] * 0.5)  # Heal for 50% of damage dealt
                # Check if attacker is a player or wild Pokemon
                if hasattr(attacker, "pokemon"):
                    pokemon = attacker.pokemon
                else:
                    pokemon = attacker  # For wild Pokemon, attacker is the Pokemon itself
                
                pokemon.current_hp = min(
                    pokemon.current_hp + heal_amount,
                    pokemon.stats["HP"]
                )
                print(f"{pokemon.name} restored {heal_amount} HP!")


        
        elif callable(self.effects[effect_type]):
            return self.effects[effect_type](effect_context)
        
        return None

class Projectile:
    def __init__(self, position, direction, speed, move, owner):
        """
        Initialize a projectile.
        :param position: The starting position of the projectile (x, y).
        :param direction: The direction of the projectile as a (dx, dy) tuple.
        :param speed: The speed of the projectile.
        :param move: The move associated with the projectile.
        :param owner: The owner of the projectile (e.g., the player or an enemy).
        """
        self.position = list(position)
        self.direction = direction
        self.speed = speed
        self.move = move
        self.owner = owner
        self.size = 10  # Size of the projectile

    def update(self, dungeon):
        """
        Update the projectile's position and check for collisions.
        :param dungeon: The dungeon object for collision checks.
        """
        self.position[0] += self.direction[0] * self.speed
        self.position[1] += self.direction[1] * self.speed

        # Check if the projectile hits a wall
        if not dungeon.is_walkable(self.position[0], self.position[1]):
            # Trigger wall hit effect if the move has one
            if hasattr(self.move, 'trigger_effect'):
                self.move.trigger_effect("on_wall_hit", self.owner, None, {"position": self.position})
            return False  # Destroy the projectile

        # Import player module only when needed to avoid circular imports
        from game.player import Player
        
        # Check if this is a player projectile or an enemy projectile
        if isinstance(self.owner, Player):
            # Player projectile - check for collisions with enemies
            for wild in dungeon.wild_pokemon:
                wild_rect = pygame.Rect(wild["position"], (dungeon.tile_size, dungeon.tile_size))
                projectile_rect = pygame.Rect(self.position[0], self.position[1], self.size, self.size)
                if projectile_rect.colliderect(wild_rect):
                    # Deal damage to the enemy
                    damage = calculate_damage(self.owner.pokemon, wild["pokemon"], self.move)
                    wild["pokemon"].take_damage(damage)
                    print(f"Projectile dealt {damage} damage to {wild['pokemon'].name}!")
                    if wild["pokemon"].is_fainted():
                        print(f"{wild['pokemon'].name} fainted!")
                        # Award experience to the player's Pokémon and pass the screen
                        screen = pygame.display.get_surface()
                        self.owner.pokemon.gain_experience(defeated_pokemon=wild["pokemon"], screen=screen)
                        dungeon.wild_pokemon.remove(wild)
                    return False  # Destroy the projectile after hitting an enemy
        else:
            # Enemy projectile - check for collision with player
            from game.player import get_player_instance
            player = get_player_instance()
            if player:
                player_rect = player.get_collision_rect()
                projectile_rect = pygame.Rect(self.position[0], self.position[1], self.size, self.size)
                if projectile_rect.colliderect(player_rect):
                    # Deal damage to the player
                    damage = calculate_damage(self.owner, player.pokemon, self.move)
                    player.pokemon.take_damage(damage)
                    print(f"Enemy projectile dealt {damage} damage to {player.pokemon.name}!")
                    return False  # Destroy the projectile after hitting the player

        return True  # Keep the projectile alive

    def draw(self, screen, camera):
        """
        Draw the projectile on the screen.
        """
        screen_position = camera.apply(self.position)
        pygame.draw.circle(screen, (255, 255, 0), (int(screen_position[0]), int(screen_position[1])), self.size)