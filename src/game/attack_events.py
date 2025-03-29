# Attack event system for handling different trigger points in attack sequences

class AttackEvent:
    """
    Class representing an event that can occur during an attack sequence.
    """
    def __init__(self, name, description, effect_function):
        """
        Initialize an attack event.
        :param name: The name of the event (e.g., "Recoil Damage").
        :param description: A description of what the event does.
        :param effect_function: The function that implements the event's effect.
        """
        self.name = name
        self.description = description
        self.effect_function = effect_function

    def trigger(self, context):
        """
        Trigger the attack event.
        :param context: Context data for the event (e.g., attacker, defender, move, damage).
        :return: Any modified values from the event effect.
        """
        if callable(self.effect_function):
            return self.effect_function(context)
        return None

# Example attack event effect functions
def recoil_damage_effect(context):
    """
    Recoil damage effect: Attacker takes a percentage of the damage dealt as recoil.
    :param context: Contains attacker, damage information.
    """
    if "attacker" in context and "damage" in context:
        attacker = context["attacker"]
        damage = context["damage"]
        recoil_amount = int(damage * 0.33)  # 33% recoil damage
        attacker.take_damage(recoil_amount)
        print(f"{attacker.name} took {recoil_amount} recoil damage!")
    return None

def flinch_effect(context):
    """
    Flinch effect: May cause the target to flinch.
    :param context: Contains defender information.
    """
    if "defender" in context:
        import random
        if random.random() < 0.3:  # 30% chance to flinch
            defender = context["defender"]
            print(f"{defender.name} flinched!")
            # Apply flinch status effect
            # This would be implemented in a status effect system
    return None

def stat_boost_effect(context):
    """
    Stat boost effect: Boosts a stat of the attacker.
    :param context: Contains attacker information.
    """
    if "attacker" in context and "stat" in context and "boost" in context:
        attacker = context["attacker"]
        stat = context["stat"]
        boost = context["boost"]
        if stat in attacker.base_stats:
            attacker.base_stats[stat] += boost
            print(f"{attacker.name}'s {stat} increased by {boost}!")
    return None

def wall_bounce_effect(context):
    """
    Wall bounce effect: Special effect when a projectile hits a wall.
    :param context: Contains position information.
    """
    if "position" in context:
        position = context["position"]
        print(f"Attack hit wall at position {position}!")
        # Could create an area effect, spawn additional projectiles, etc.
    return None

# Dictionary of predefined attack events
ATTACK_EVENTS = {
    "on_activate": {
        "stat_boost": AttackEvent(
            "Stat Boost", 
            "Boosts a stat when the move is activated.", 
            stat_boost_effect
        )
    },
    "before_hit": {
        "intimidate": AttackEvent(
            "Intimidate", 
            "May lower target's attack before hit.", 
            lambda context: print(f"{context['defender'].name} was intimidated!")
        )
    },
    "on_hit": {
        "recoil": AttackEvent(
            "Recoil Damage", 
            "User takes recoil damage on hit.", 
            recoil_damage_effect
        ),
        "flinch": AttackEvent(
            "Flinch", 
            "May cause the target to flinch.", 
            flinch_effect
        )
    },
    "on_wall_hit": {
        "bounce": AttackEvent(
            "Wall Bounce", 
            "Special effect when hitting a wall.", 
            wall_bounce_effect
        )
    }
}

# Function to create a move effect dictionary
def create_move_effects(on_activate=None, before_hit=None, on_hit=None, on_wall_hit=None):
    """
    Create a dictionary of move effects for different trigger points.
    :param on_activate: Effect to trigger when the move is activated.
    :param before_hit: Effect to trigger before the move hits.
    :param on_hit: Effect to trigger when the move hits.
    :param on_wall_hit: Effect to trigger when the move hits a wall.
    :return: Dictionary of effects.
    """
    effects = {}
    if on_activate:
        effects["on_activate"] = on_activate
    if before_hit:
        effects["before_hit"] = before_hit
    if on_hit:
        effects["on_hit"] = on_hit
    if on_wall_hit:
        effects["on_wall_hit"] = on_wall_hit
    return effects