from game.pokemon import Pokemon

# Define Pokémon with different experience groups
pikachu = Pokemon(
    name="Pikachu",
    types=["Electric"],
    base_stats={"HP": 35, "Attack": 55, "Defense": 40, "Special Attack": 50, "Special Defense": 50, "Speed": 90},
    experience_group="Medium Fast",
    abilities=[{"name": "Static", "trigger": "on_hit", "effect": lambda pokemon: print(f"{pokemon.name} paralyzed the attacker!")}],
    evolution={"level": 16, "to": "Raichu"}
)

bulbasaur = Pokemon(
    name="Bulbasaur",
    types=["Grass", "Poison"],
    base_stats={"HP": 45, "Attack": 49, "Defense": 49, "Special Attack": 65, "Special Defense": 65, "Speed": 45},
    experience_group="Medium Slow",
    abilities=[{"name": "Overgrow", "trigger": "on_low_hp", "effect": lambda pokemon: print(f"{pokemon.name}'s Grass-type moves are powered up!")}],
    evolution={"level": 16, "to": "Ivysaur"}
)

zubat = Pokemon(
    name="Zubat",
    types=["Flying", "Poison"],
    base_stats={"HP": 40, "Attack": 45, "Defense": 35, "Special Attack": 30, "Special Defense": 40, "Speed": 55},
    experience_group="Fast",
    abilities=[{"name": "Inner Focus", "trigger": "on_flinch", "effect": lambda pokemon: print(f"{pokemon.name} prevented flinching!")}],
    evolution={"level": 22, "to": "Golbat"}
)