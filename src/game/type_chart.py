TYPE_CHART = {
    "Normal": {"Rock": 0.5, "Ghost": 0, "Steel": 0.5},
    "Fire": {"Fire": 0.5, "Water": 0.5, "Grass": 2, "Ice": 2, "Bug": 2, "Rock": 0.5, "Dragon": 0.5, "Steel": 2},
    "Water": {"Fire": 2, "Water": 0.5, "Grass": 0.5, "Ground": 2, "Rock": 2, "Dragon": 0.5},
    "Electric": {"Water": 2, "Electric": 0.5, "Grass": 0.5, "Ground": 0, "Flying": 2, "Dragon": 0.5},
    "Grass": {"Fire": 0.5, "Water": 2, "Grass": 0.5, "Poison": 0.5, "Ground": 2, "Flying": 0.5, "Bug": 0.5, "Rock": 2, "Dragon": 0.5, "Steel": 0.5},
    # Add more types as needed...
}

def get_type_effectiveness(move_type, target_types):
    """
    Calculate the type effectiveness multiplier for a move against a target Pokémon.
    :param move_type: The type of the move (e.g., "Fire").
    :param target_types: A list of the target Pokémon's types (e.g., ["Grass", "Flying"]).
    :return: The effectiveness multiplier (e.g., 2 for super effective, 0.5 for not very effective).
    """
    multiplier = 1.0
    for target_type in target_types:
        if target_type in TYPE_CHART.get(move_type, {}):
            multiplier *= TYPE_CHART[move_type][target_type]
    return multiplier