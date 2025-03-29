from game.move import Move

# Example moves loaded from JSON files
try:
    thunderbolt = Move.from_json("thunderbolt")
    tackle = Move.from_json("tackle")
    growl = Move.from_json("growl")
    thunder_shock = Move.from_json("thunder-shock")
    quick_attack = Move.from_json("quick-attack")
except FileNotFoundError as e:
    print(f"Warning: {e}")
    # Fallback to hardcoded moves if JSON files are not found
    thunderbolt = Move("Thunderbolt", "Electric", 90, 100, "Ranged", "Special")
    tackle = Move("Tackle", "Normal", 40, 100, "Melee", "Physical")
    growl = Move("Growl", "Normal", 0, 100, "Ranged", "Status")  # Status move