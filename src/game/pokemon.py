import json
import os
import random
from utils.animation import SpriteAnimation

EXPERIENCE_GROUPS = {
    "Erratic": lambda level: (
        (level ** 3 * (100 - level)) // 50 if level <= 50 else
        (level ** 3 * (150 - level)) // 100 if level <= 68 else
        (level ** 3 * ((1911 - 10 * level) // 3)) // 500 if level <= 98 else
        (level ** 3 * (160 - level)) // 100
    ),
    "Fast": lambda level: (4 * level ** 3) // 5,
    "Medium Fast": lambda level: level ** 3,
    "Medium Slow": lambda level: ((6 / 5) * level ** 3) - (15 * level ** 2) + (100 * level) - 140,
    "Slow": lambda level: (5 * level ** 3) // 4,
    "Fluctuating": lambda level: (
        (level ** 3 * (24 + ((level + 1) // 3))) // 50 if level <= 15 else
        (level ** 3 * (14 + level)) // 50 if level <= 36 else
        (level ** 3 * (32 + (level // 2))) // 50
    )
}

class Pokemon:
    def __init__(self, name, types, base_stats, experience_group, basexp, abilities=None, evolution=None, sprite_offset=(0, 0)):
        """
        Initialize a Pokémon with its name, typing, base stats, experience group, abilities, and evolution details.
        :param name: Name of the Pokémon (e.g., "Pikachu").
        :param types: A list of types (e.g., ["Electric"] or ["Fire", "Flying"]).
        :param base_stats: A dictionary of base stats (e.g., {"HP": 35, "Attack": 55, "Defense": 40, "Special Attack": 50, "Special Defense": 50, "Speed": 90}).
        :param experience_group: The experience group (e.g., "Fast", "Medium", "Slow").
        :param abilities: A list of abilities (e.g., ["Static", "Lightning Rod"]).
        :param evolution: A dictionary defining how the Pokémon evolves (e.g., {"level": 16, "to": "Raichu"}).
        """
        self.name = name
        self.types = types  # List of types (e.g., ["Electric"])
        self.base_stats = base_stats  # Base stats dictionary
        self.experience_group = experience_group  # Determines how fast the Pokémon levels up
        self.level = 1  # Start at level 1
        self.experience = 0  # Start with 0 XP
        self.abilities = abilities or []  # List of abilities
        self.evolution = evolution  # Evolution details
        self.learnable_moves = {}  # Moves the Pokémon can learn at specific levels (e.g., {5: "Thunder Shock", 10: "Quick Attack"})
        self.current_moves = []  # Moves the Pokémon currently knows
        self.basexp = basexp  # Base experience yield
        self.animation = SpriteAnimation(name, "Idle", sprite_offset=sprite_offset)
        self.status = None  # Current status condition (None, "paralysis", "confusion", "poison", "bad_poison", "sleep", "freeze", "burn")
        self.status_counter = 0  # Counter for status effects that last a certain number of turns
        
        # Add Individual Values (IVs) - randomized stats that make each Pokémon unique
        # IVs range from 0 to 31 for each stat
        self.ivs = {
            "HP": random.randint(0, 31),
            "Attack": random.randint(0, 31),
            "Defense": random.randint(0, 31),
            "Special Attack": random.randint(0, 31),
            "Special Defense": random.randint(0, 31),
            "Speed": random.randint(0, 31)
        }
        
        # Add Effort Values (EVs) - stats gained from defeating other Pokémon
        # EVs start at 0 and can go up to 255 per stat, with a total maximum of 510
        self.evs = {
            "HP": 0,
            "Attack": 0,
            "Defense": 0,
            "Special Attack": 0,
            "Special Defense": 0,
            "Speed": 0
        }
        
        # Add nature - affects stat growth (increases one stat by 10%, decreases another by 10%)
        # For simplicity, we'll use a neutral nature by default
        self.nature = {
            "name": "Hardy",  # Example of a neutral nature
            "increase": None,
            "decrease": None
        }
        
        # Calculate initial stats based on base stats, IVs, EVs, and level
        self.stats = self.calculate_stats()
        self.current_hp = self.stats["HP"]  # Start with full HP

    @classmethod
    def from_json(cls, pokemon_name):
        """
        Create a Pokémon instance from a JSON file in the predefined data folder.
        :param pokemon_name: The name of the Pokémon (e.g., "pikachu").
        :return: A Pokémon instance.
        """
        # Define the path to the data folder
        data_folder = os.path.join("data", "pokemon")
        file_path = os.path.join(data_folder, f"{pokemon_name.lower()}.json")

        # Load the JSON file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Pokémon data file not found: {file_path}")

        with open(file_path, "r") as file:
            data = json.load(file)

        # Create and return the Pokémon instance
        return cls(
            name=data["name"],
            types=data["types"],
            base_stats=data["base_stats"],
            basexp=data["basexp"],
            experience_group=data["experience_group"],
            abilities=data.get("abilities", []),
            evolution=data.get("evolution", None)            
        )

    def add_learnable_moves_from_json(self, pokemon_name):
        """
        Load learnable moves from a JSON file in the predefined data folder and add them to the Pokémon.
        :param pokemon_name: The name of the Pokémon (e.g., "pikachu").
        """
        # Define the path to the data folder
        data_folder = os.path.join("data", "pokemon")
        file_path = os.path.join(data_folder, f"{pokemon_name.lower()}.json")

        # Load the JSON file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Pokémon data file not found: {file_path}")

        with open(file_path, "r") as file:
            data = json.load(file)

        # Update the learnable moves
        self.learnable_moves.update(data.get("learnable_moves", {}))

    def take_damage(self, damage):
        """
        Reduce the Pokémon's HP by the damage taken.
        :param damage: The amount of damage to subtract from HP.
        """
        self.current_hp -= damage
        if self.current_hp < 0:
            self.current_hp = 0  # Prevent negative HP

    def is_fainted(self):
        """
        Check if the Pokémon has fainted (HP <= 0).
        """
        return self.current_hp <= 0

    def gain_experience(self, xp=None, defeated_pokemon=None, screen=None):
        """
        Gain experience points and level up if enough XP is accumulated.
        Can either directly provide XP amount or calculate it from a defeated Pokémon.
        :param xp: The amount of experience points to gain (optional).
        :param defeated_pokemon: The defeated Pokémon to calculate XP from (optional).
        :param screen: Pygame screen surface for UI rendering (optional).
        """
        if defeated_pokemon:
            # Calculate XP based on Gen 7+ formula
            # Formula: (a * b * e * L * p * f) / (7 * s)
            # a = base experience yield of the defeated Pokémon
            # b = 1 for wild Pokémon, 1.5 for trainer's Pokémon
            # e = 1.5 if holding Lucky Egg, 1 otherwise
            # L = level of the defeated Pokémon
            # p = 1.2 if Pokémon has high affection, 1 otherwise
            # f = 1 for normal battle
            # s = number of Pokémon that participated in battle
            
            base_yield = defeated_pokemon.basexp
            b_multiplier = 1.5  # Wild Pokémon battle
            e_multiplier = 1  # No Lucky Egg
            p_multiplier = 1  # No affection bonus
            f_multiplier = 1  # Normal battle
            s_divider = 1     # Single battle participant
            
            xp = round(int((base_yield * b_multiplier * e_multiplier * defeated_pokemon.level * p_multiplier * f_multiplier) / (7 * s_divider)))
            
            print(f"Gained {xp} XP from defeating {defeated_pokemon.name}!")
        
        if xp:
            self.experience += xp
            print(f"Current XP: {self.experience}/{self.get_experience_to_next_level()}")
            
            while self.experience >= self.get_experience_to_next_level():
                self.level_up(screen)

    def get_experience_to_next_level(self):
        """
        Calculate the experience required to reach the next level based on the experience group.
        """
        if self.experience_group in EXPERIENCE_GROUPS:
            return int(EXPERIENCE_GROUPS[self.experience_group](self.level))
        else:
            raise ValueError(f"Unknown experience group: {self.experience_group}")

    def calculate_stats(self):
        """
        Calculate a Pokémon's stats based on the standard Pokémon game formula.
        Formula: ((2 * Base + IV + EV/4) * Level/100 + 5) * Nature
        HP Formula: ((2 * Base + IV + EV/4) * Level/100 + Level + 10)
        :return: Dictionary of calculated stats.
        """
        calculated_stats = {}
        
        # HP calculation: (2 * Base + IV + EV/4) * Level/100 + Level + 10
        calculated_stats["HP"] = int(((2 * self.base_stats["HP"] + self.ivs["HP"] + self.evs["HP"] // 4) * self.level / 100) + self.level + 10)
        
        # Other stats: (2 * Base + IV + EV/4) * Level/100 + 5 * Nature
        for stat in ["Attack", "Defense", "Special Attack", "Special Defense", "Speed"]:
            # Calculate the base value
            base_value = ((2 * self.base_stats[stat] + self.ivs[stat] + self.evs[stat] // 4) * self.level / 100) + 5
            
            # Apply nature modifier (10% increase or decrease)
            if self.nature["increase"] == stat:
                base_value *= 1.1
            elif self.nature["decrease"] == stat:
                base_value *= 0.9
                
            calculated_stats[stat] = int(base_value)
        
        return calculated_stats
    
    def learn_move(self, new_move, screen=None):
        """
        Learn a new move. If the Pokémon already knows four moves,
        prompt the user to choose which move to replace using Pygame UI.
        :param new_move: The name of the move to learn or Move object.
        :param screen: Pygame screen surface for UI rendering (optional).
        :return: True if a move was learned, False otherwise.
        """
        from game.move import Move
        from game.move_learning_ui import MoveLearningUI
        from utils.settings import SCREEN_WIDTH, SCREEN_HEIGHT
        import pygame
        
        # Convert string move name to Move object if necessary
        if isinstance(new_move, str):
            try:
                move_obj = Move.from_json(new_move.lower().replace(" ", "-"))
            except FileNotFoundError:
                print(f"Could not find move data for {new_move}")
                return False
        else:
            move_obj = new_move
            
        if len(self.current_moves) < 4:
            self.current_moves.append(move_obj)
            return True
        
        # If no screen is provided, skip the learning process
        if screen is None:
            return False
            
        # Initialize move learning UI
        ui = MoveLearningUI(SCREEN_WIDTH, SCREEN_HEIGHT)
        clock = pygame.time.Clock()
        
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                    
                choice = ui.handle_input(event)
                if choice is not None:
                    if 0 <= choice <= 3:
                        forgotten_move = self.current_moves[choice]
                        self.current_moves[choice] = move_obj
                        return True
                    elif choice == 4:  # Don't learn the new move
                        return False
            
            # Draw the move learning UI
            ui.draw(screen, self, move_obj)
            pygame.display.flip()
            clock.tick(60)
                #except ValueError:
                #    print("Please enter a valid number.")

    def level_up(self, screen=None):
        """
        Level up the Pokémon, increasing its stats and learning new moves if applicable.
        :param screen: Pygame screen surface for UI rendering (optional).
        """
        self.experience = self.experience - self.get_experience_to_next_level()
        self.level += 1
        print(f"{self.name} leveled up to level {self.level}!")

        old_max_hp = self.stats["HP"]

        # Recalculate stats based on the new level
        self.stats = self.calculate_stats()
        self.current_hp = self.current_hp + (self.stats["HP"] - old_max_hp)  # Restore HP to full on level up

        # Learn new moves
        if str(self.level) in self.learnable_moves:
            # Get the list of moves for this level
            new_moves = self.learnable_moves[str(self.level)]
            for move_name in new_moves:
                self.learn_move(move_name, screen)

        # Check for evolution
        if self.evolution and self.evolution.get("level") == self.level:
            self.evolve()

    def evolve(self):
        """
        Evolve the Pokémon if it meets the evolution criteria.
        """
        if self.evolution:
            print(f"{self.name} is evolving into {self.evolution['to']}!")
            self.animation.pokemon_name = self.evolution["to"]
            self.animation.load_animation_data()
            self.from_json(self.evolution["to"])
            # Optionally, update stats, types, and other attributes here

    def trigger_ability(self, trigger_event, context=None):
        """
        Trigger abilities based on specific events.
        :param trigger_event: The event that triggers the ability (e.g., "on_activate", "before_hit", "on_hit", "on_wall_hit", "on_faint").
        :param context: Additional context data for the ability (e.g., attacker, defender, move).
        :return: Any modified values from the ability effect.
        """
        result = None
        for ability in self.abilities:
            if isinstance(ability, dict) and ability.get("trigger") == trigger_event:
                print(f"{self.name}'s ability {ability['name']} activated!")
                if callable(ability.get("effect")):
                    result = ability["effect"](self, context)
        return result

    def add_learnable_move(self, level, move):
        """
        Add a move that the Pokémon can learn at a specific level.
        :param level: The level at which the move is learned.
        :param move: The name of the move.
        """
        self.learnable_moves[level] = move
        
    def set_level(self, new_level):
        """
        Set the Pokémon's level and adjust experience points accordingly.
        :param new_level: The new level to set for the Pokémon.
        """
        if new_level < 1 or new_level > 100:
            raise ValueError("Level must be between 1 and 100")
        
        # Set the new level
        self.level = new_level
        
        # Set experience to match the start of the current level
        self.experience = 0
        
        # Recalculate stats based on the new level
        self.stats = self.calculate_stats()
        
        # Restore HP to full
        self.current_hp = self.stats["HP"]
        
        print(f"{self.name}'s level set to {new_level}!")
        print(f"Experience: {self.experience}/{self.get_experience_to_next_level()}")
    
    def apply_status_effects(self):
        """
        Apply the effects of the Pokémon's current status condition.
        This should be called at the beginning of each turn.
        :return: True if the Pokémon can act this turn, False otherwise.
        """
        if self.status is None:
            return True  # No status effect, can act normally
        
        # Handle poison damage
        if self.status == "poison":
            damage = max(1, int(self.stats["HP"] * 0.125))  # 1/8 of max HP
            self.take_damage(damage)
            print(f"{self.name} took {damage} damage from poison!")
        
        # Handle bad poison (toxic) damage - increases each turn
        elif self.status == "bad_poison":
            self.status_counter += 1
            damage = max(1, int(self.stats["HP"] * 0.0625 * self.status_counter))  # Starts at 1/16, increases each turn
            self.take_damage(damage)
            print(f"{self.name} took {damage} damage from toxic poison!")
        
        # Handle burn damage
        elif self.status == "burn":
            damage = max(1, int(self.stats["HP"] * 0.0625))  # 1/16 of max HP
            self.take_damage(damage)
            print(f"{self.name} took {damage} damage from its burn!")
        
        # Handle paralysis (30% chance of not moving)
        elif self.status == "paralysis":
            if random.randint(1, 100) <= 30:
                print(f"{self.name} is paralyzed and can't move!")
                return False
        
        # Handle sleep
        elif self.status == "sleep":
            if self.status_counter <= 0:
                # Initialize sleep counter (1-3 turns)
                self.status_counter = random.randint(1, 3)
            
            self.status_counter -= 1
            if self.status_counter > 0:
                print(f"{self.name} is fast asleep!")
                return False
            else:
                print(f"{self.name} woke up!")
                self.status = None
        
        # Handle freeze (20% chance of thawing each turn)
        elif self.status == "freeze":
            if random.randint(1, 100) <= 20:
                print(f"{self.name} thawed out!")
                self.status = None
            else:
                print(f"{self.name} is frozen solid!")
                return False
        
        # Handle confusion (50% chance of hurting itself)
        elif self.status == "confusion":
            if self.status_counter <= 0:
                # Initialize confusion counter (1-4 turns)
                self.status_counter = random.randint(1, 4)
            
            self.status_counter -= 1
            if self.status_counter > 0:
                print(f"{self.name} is confused!")
                if random.randint(1, 100) <= 50:
                    # Calculate self-damage
                    attack = self.stats["Attack"]
                    defense = self.stats["Defense"]
                    damage = max(1, int((attack * 40 / defense) / 50 + 2))
                    self.take_damage(damage)
                    print(f"{self.name} hurt itself in confusion for {damage} damage!")
                    return False
            else:
                print(f"{self.name} snapped out of confusion!")
                self.status = None
        
        return True  # Can act this turn
    
    def cure_status(self):
        """
        Cure all status conditions.
        """
        if self.status:
            old_status = self.status
            self.status = None
            self.status_counter = 0
            
            # Restore stats if they were modified by status
            if old_status == "paralysis":
                # Restore Speed if it was reduced by paralysis
                self.stats = self.calculate_stats()
            elif old_status == "burn":
                # Restore Attack if it was reduced by burn
                self.stats = self.calculate_stats()
            
            print(f"{self.name} was cured of {old_status}!")