import random
from game.type_chart import get_type_effectiveness

def calculate_stats(pokemon):
    """
    Calculate a Pokémon's stats based on Gen 3+ formula.
    :param pokemon: The Pokémon instance.
    :return: Dictionary of calculated stats.
    """
    calculated_stats = {}
    
    # HP calculation: (2 * Base + IV + EV/4) * Level/100 + Level + 10
    # For simplicity, we'll assume IVs are 0 and EVs are 0
    calculated_stats["HP"] = int((2 * pokemon.base_stats["HP"]) * pokemon.level / 100 + pokemon.level + 10)
    
    # Other stats: (2 * Base + IV + EV/4) * Level/100 + 5 * Nature
    # For simplicity, we'll assume nature is neutral (multiplier of 1.0)
    for stat in ["Attack", "Defense", "Special Attack", "Special Defense", "Speed"]:
        calculated_stats[stat] = int((2 * pokemon.base_stats[stat]) * pokemon.level / 100 + 5)
    
    return calculated_stats

def calculate_damage(attacker, defender, move):
    """
    Calculate the damage dealt by a move using Gen 5+ formula.
    :param attacker: The attacking Pokémon (instance of Pokemon).
    :param defender: The defending Pokémon (instance of Pokemon).
    :param move: The move being used (instance of Move).
    :return: The damage dealt.
    """
    # Check if attacker can move due to status conditions
    if hasattr(attacker, 'pokemon') and hasattr(attacker.pokemon, 'apply_status_effects'):
        if not attacker.pokemon.apply_status_effects():
            return 0  # Cannot move due to status effect
    elif hasattr(attacker, 'apply_status_effects'):
        if not attacker.apply_status_effects():
            return 0  # Cannot move due to status effect
    
    # Trigger any move effects that happen before the hit
    if hasattr(move, 'trigger_effect'):
        move.trigger_effect("before_hit", attacker, defender)
    
    # Trigger any abilities that activate before being hit
    if hasattr(defender, 'trigger_ability'):
        defender.trigger_ability("before_hit", {"attacker": attacker, "move": move})
    
    if move.category == "Status":
        print(f"{move.name} is a status move and does no damage.")
        # Apply status effects for status moves
        if hasattr(move, 'trigger_effect'):
            move.trigger_effect("on_hit", attacker, defender, {"damage": 0})
        return 0  # Status moves do not deal damage

    if random.randint(1, 100) > move.accuracy:
        print(f"{move.name} missed!")
        return 0  # Move missed

    # Get calculated stats
    attacker_stats = calculate_stats(attacker)
    defender_stats = calculate_stats(defender)
    
    # Determine which stats to use based on the move's category
    if move.category == "Physical":
        attack_stat = attacker_stats["Attack"]
        defense_stat = defender_stats["Defense"]
    elif move.category == "Special":
        attack_stat = attacker_stats["Special Attack"]
        defense_stat = defender_stats["Special Defense"]
    else:
        raise ValueError(f"Unknown move category: {move.category}")

    # Gen 5+ damage formula: 
    # ((2 * Level / 5 + 2) * Power * A/D / 50 + 2) * Modifiers
    
    # Base damage calculation
    base_damage = ((2 * attacker.level / 5 + 2) * move.power * attack_stat / defense_stat / 50 + 2)
    
    # Modifiers
    # STAB (Same Type Attack Bonus)
    stab = 1.5 if move.move_type in attacker.types else 1.0
    
    # Type effectiveness
    effectiveness = get_type_effectiveness(move.move_type, defender.types)
    
    # Critical hit (1/16 chance for a critical hit)
    is_critical = random.randint(1, 16) == 1
    critical = 1.5 if is_critical else 1.0
    if is_critical:
        print("A critical hit!")
    
    # Random factor (between 0.85 and 1.0)
    random_factor = random.uniform(0.85, 1.0)
    
    # Apply all modifiers
    damage = base_damage * stab * effectiveness * critical * random_factor
    
    # Trigger any move effects that happen on hit
    if hasattr(move, 'trigger_effect'):
        move.trigger_effect("on_hit", attacker, defender, {"damage": damage})
    
    # Trigger any abilities that activate on being hit
    if hasattr(defender, 'trigger_ability'):
        defender.trigger_ability("on_hit", {"attacker": attacker, "move": move, "damage": damage})
    
    # Ensure Pokémon always take at least 1 damage unless they're immune to the attack type
    if effectiveness > 0 and damage < 1:
        damage = 1
    
    print(f"{move.name} dealt {damage:.2f} damage!")
    return int(damage)