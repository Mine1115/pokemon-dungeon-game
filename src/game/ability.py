class Ability:
    """
    Class representing a Pokémon ability with various trigger points.
    """
    def __init__(self, name, description, trigger_type, effect_function):
        """
        Initialize an ability.
        :param name: The name of the ability (e.g., "Static", "Intimidate").
        :param description: A description of what the ability does.
        :param trigger_type: When the ability triggers (e.g., "on_activate", "before_hit", "on_hit", "on_wall_hit").
        :param effect_function: The function that implements the ability's effect.
        """
        self.name = name
        self.description = description
        self.trigger_type = trigger_type
        self.effect_function = effect_function

    def activate(self, pokemon, context=None):
        """
        Activate the ability.
        :param pokemon: The Pokémon using the ability.
        :param context: Additional context data for the ability (e.g., attacker, defender, move).
        :return: Any modified values from the ability effect.
        """
        print(f"{pokemon.name}'s ability {self.name} activated!")
        if callable(self.effect_function):
            return self.effect_function(pokemon, context)
        return None

# Example ability effect functions
def static_effect(pokemon, context):
    """
    Static ability: May paralyze on contact.
    :param pokemon: The Pokémon with the ability.
    :param context: Contains attacker information.
    """
    if context and "attacker" in context:
        # 30% chance to paralyze the attacker
        import random
        if random.random() < 0.3:
            attacker = context["attacker"]
            print(f"{attacker.name} is paralyzed by Static!")
            # Apply paralysis status effect
            # This would be implemented in a status effect system
    return None

def intimidate_effect(pokemon, context):
    """
    Intimidate ability: Lowers opponent's Attack when entering battle.
    :param pokemon: The Pokémon with the ability.
    :param context: Contains opponent information.
    """
    if context and "opponents" in context:
        for opponent in context["opponents"]:
            # Lower opponent's Attack stat by one stage
            print(f"{opponent.name}'s Attack was lowered by Intimidate!")
            # This would modify the opponent's attack stat
            # Implementation depends on how stat stages are handled
    return None

def speed_boost_effect(pokemon, context):
    """
    Speed Boost ability: Increases Speed at the end of each turn.
    :param pokemon: The Pokémon with the ability.
    :param context: Not used for this ability.
    """
    # Increase the Pokémon's Speed stat
    pokemon.base_stats["Speed"] += 1
    print(f"{pokemon.name}'s Speed increased due to Speed Boost!")
    return None

# Dictionary of predefined abilities
ABILITIES = {
    "Static": {
        "name": "Static",
        "description": "May paralyze on contact.",
        "trigger": "on_hit",
        "effect": static_effect
    },
    "Intimidate": {
        "name": "Intimidate",
        "description": "Lowers opponent's Attack when entering battle.",
        "trigger": "on_activate",
        "effect": intimidate_effect
    },
    "Speed Boost": {
        "name": "Speed Boost",
        "description": "Increases Speed at the end of each turn.",
        "trigger": "on_turn_end",
        "effect": speed_boost_effect
    }
}