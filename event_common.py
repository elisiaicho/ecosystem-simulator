from __future__ import annotations

import math


TERRESTRIAL_NAMES = {
    "penguin",
    "polarbear",
    "arcticfox",
    "articfox",
    "reindeer",
}

MARINE_NAMES = {
    "seal",
    "orca",
    "arcticcod",
    "articcod",
    "krill",
}


def animal_name(animal) -> str:
    return str(
        getattr(animal, "name", getattr(animal, "SPECIES", ""))
    ).strip().lower()


def class_name(animal) -> str:
    return type(animal).__name__.strip().lower()


def habitat_name(animal) -> str:
    return str(
        getattr(animal, "habitat", getattr(animal, "HABITAT", ""))
    ).strip().lower()


def is_alive(animal) -> bool:
    return bool(getattr(animal, "is_alive", True))


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def normalized_cold_resistance(animal) -> float:
    # Accept both 0~1 and 0~100 style inputs so existing animal code still works.
    value = getattr(animal, "cold_resistance", 0.0)
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0

    if value > 1.0:
        value /= 100.0

    return clamp(value, 0.0, 1.0)


def apply_damage(animal, damage: float) -> None:
    # Prefer the animal's own combat logic, but fall back to raw hp editing if needed.
    damage = max(0.0, float(damage))
    if damage <= 0.0:
        return

    if hasattr(animal, "take_damage"):
        animal.take_damage(damage)
        return

    hp = getattr(animal, "hp", None)
    if hp is None:
        return

    animal.hp = hp - damage
    if animal.hp <= 0:
        animal.hp = 0
        animal.is_alive = False


def is_krill(animal) -> bool:
    name = animal_name(animal)
    cls = class_name(animal)
    return (
        name == "krill"
        or cls == "krill"
        or str(getattr(animal, "SPECIES", "")).strip().lower() == "krill"
        or hasattr(animal, "swarm_size")
    )


def is_terrestrial(animal, sea_line=None, terrain=None) -> bool:
    if not is_alive(animal):
        return False

    name = animal_name(animal)
    cls = class_name(animal)
    habitat = habitat_name(animal)

    if habitat in {"terrestrial", "ice"}:
        return True
    if habitat in {"marine", "water"}:
        return False
    if habitat == "any":
        x = float(getattr(animal, "x", 0.0))
        y = float(getattr(animal, "y", 0.0))
        if terrain is not None and hasattr(terrain, "is_ice_at"):
            return bool(terrain.is_ice_at(x, y))
        if sea_line is not None:
            return y < float(sea_line)
    if name in TERRESTRIAL_NAMES or cls in TERRESTRIAL_NAMES:
        return True

    return hasattr(animal, "territory_range") or hasattr(animal, "home_x")


def is_marine(animal, sea_line=None, terrain=None) -> bool:
    if not is_alive(animal):
        return False

    name = animal_name(animal)
    cls = class_name(animal)
    habitat = habitat_name(animal)

    if habitat in {"marine", "water"}:
        return True
    if habitat in {"terrestrial", "ice"}:
        return False
    if habitat == "any":
        x = float(getattr(animal, "x", 0.0))
        y = float(getattr(animal, "y", 0.0))
        if terrain is not None and hasattr(terrain, "is_ice_at"):
            return not bool(terrain.is_ice_at(x, y))
        if sea_line is not None:
            return y >= float(sea_line)
    if name in MARINE_NAMES or cls in MARINE_NAMES:
        return True

    return hasattr(animal, "oxygen") or hasattr(animal, "optimum_watertemp")


def resolve_animals(subject):
    if hasattr(subject, "animals"):
        return list(getattr(subject, "animals", []))
    return list(subject)


def krill_amount(animal) -> float:
    for attr_name in ("swarm_size", "size"):
        if not hasattr(animal, attr_name):
            continue
        try:
            return max(0.0, float(getattr(animal, attr_name)))
        except (TypeError, ValueError):
            return 0.0
    return 1.0


def infer_world_width(animals, default: float = 1000.0) -> float:
    xs = [float(getattr(animal, "x", 0.0)) for animal in animals if is_alive(animal)]
    if not xs:
        return default
    return max(max(xs) + 1.0, 1.0)


def infer_world_height(animals, default: float = 1000.0) -> float:
    ys = [float(getattr(animal, "y", 0.0)) for animal in animals if is_alive(animal)]
    if not ys:
        return default
    return max(max(ys) + 1.0, 1.0)


def infer_sea_line(animals, default: float | None = None) -> float:
    if default is not None:
        return float(default)

    ys = [float(getattr(animal, "y", 0.0)) for animal in animals if is_alive(animal)]
    if not ys:
        return 500.0

    # When no explicit sea line is provided, split the known map height in half.
    return max(1.0, infer_world_height(animals) / 2.0)


def distance(animal, x: float, y: float) -> float:
    dx = float(getattr(animal, "x", 0.0)) - x
    dy = float(getattr(animal, "y", 0.0)) - y
    return math.hypot(dx, dy)
