from __future__ import annotations

import random

from event import Event
from event_common import (
    apply_damage,
    clamp,
    distance,
    infer_sea_line,
    infer_world_width,
    is_alive,
    is_terrestrial,
    normalized_cold_resistance,
    resolve_animals,
)


class EventTerrestrial(Event):
    BLIZZARD_COOLDOWN_MAX = 1500
    BLIZZARD_DURATION = 180
    BLIZZARD_DAMAGE_BASE = 5.0
    BLIZZARD_COLD_THRESHOLD = 0.7
    BLIZZARD_SPEED_FACTOR = 0.7

    GLACIER_COLLAPSE_PROB = 0.0003
    GLACIER_COLLAPSE_RADIUS = 60.0
    GLACIER_COLLAPSE_DAMAGE = 30.0
    COLLAPSE_EFFECT_TTL = 60

    TEMP_UPDATE_INTERVAL = 600
    TEMP_BASE = -10.0
    TEMP_VARIATION = 8.0
    MAX_LOG_SIZE = 10

    def __init__(self, world_width=None, world_height=None, sea_line=None):
        super().__init__(duration=0)
        self.world_width = world_width
        self.world_height = world_height
        self.sea_line = sea_line

        self.terrestrial_temp = self.TEMP_BASE
        self._temp_timer = 0

        self.blizzard_cooldown = self.BLIZZARD_COOLDOWN_MAX
        self._blizzard_active = False
        self._blizzard_speed_restore = {}
        self._blizzard_move_restore = {}
        self._last_known_animals = []
        self._last_sim = None
        self._last_terrain = None

        self._last_collapse_pos = None
        self._last_collapse_ttl = 0
        self.event_log = []

    def set_world_context(self, world_width=None, world_height=None, sea_line=None):
        if world_width is not None:
            self.world_width = world_width
        if world_height is not None:
            self.world_height = world_height
        if sea_line is not None:
            self.sea_line = sea_line
        return self

    def _resolve_context(self, subject):
        animals = resolve_animals(subject)
        self._last_known_animals = animals

        if hasattr(subject, "animals"):
            self._last_sim = subject
            self._last_terrain = getattr(subject, "terrain", None)
            self.set_world_context(
                world_width=getattr(subject, "world_w", getattr(subject, "world_width", None)),
                world_height=getattr(subject, "world_h", getattr(subject, "world_height", None)),
                sea_line=getattr(subject, "sea_line", None),
            )
        else:
            self._last_sim = None
            self._last_terrain = None

        return animals

    def _filter_terrestrial(self, animals):
        return [
            animal
            for animal in animals
            if is_terrestrial(animal, sea_line=self.sea_line, terrain=self._last_terrain)
        ]

    def trigger(self, animals):
        resolved_animals = self._resolve_context(animals)
        return self.blizzard(self._last_sim or resolved_animals)

    def update(self, animals):
        resolved_animals = self._resolve_context(animals)
        terrestrial_animals = self._filter_terrestrial(resolved_animals)
        turn_log = []

        # The turn loop mirrors the plan: temperature first, then active/random events.
        self._update_temperature()

        blizzard_log = self._handle_blizzard(terrestrial_animals)
        if blizzard_log:
            turn_log.extend(blizzard_log)

        collapse_log = self._handle_glacier_collapse(terrestrial_animals)
        if collapse_log:
            turn_log.extend(collapse_log)

        if self._last_collapse_ttl > 0:
            self._last_collapse_ttl -= 1
            if self._last_collapse_ttl <= 0:
                self._last_collapse_pos = None

        self.event_log.extend(turn_log)
        if len(self.event_log) > self.MAX_LOG_SIZE:
            self.event_log = self.event_log[-self.MAX_LOG_SIZE :]

        return turn_log

    def _update_temperature(self):
        self._temp_timer += 1
        if self._temp_timer < self.TEMP_UPDATE_INTERVAL:
            return

        self._temp_timer = 0
        target = self.TEMP_BASE + random.uniform(-self.TEMP_VARIATION, self.TEMP_VARIATION)
        # Use the midpoint so temperature drifts instead of jumping abruptly.
        self.terrestrial_temp = (self.terrestrial_temp + target) / 2.0

    def get_temperature_damage_multiplier(self):
        temp_diff = self.TEMP_BASE - self.terrestrial_temp
        multiplier = 1.0 + max(0.0, temp_diff * 0.1)
        return min(2.0, multiplier)

    def _handle_blizzard(self, animals):
        # A blizzard is either counting down while active, or counting down to the next trigger.
        if self._blizzard_active:
            self.duration -= 1
            if self.duration <= 0:
                return self._end_blizzard()
            return None

        self.blizzard_cooldown -= 1
        if self.blizzard_cooldown <= 0:
            return self.blizzard(self._last_sim or animals)
        return None

    def blizzard(self, animals):
        terrestrial_animals = self._filter_terrestrial(self._resolve_context(animals))
        log = ["[Blizzard] A blizzard has started."]
        self.active = True
        self._blizzard_active = True
        self.duration = self.BLIZZARD_DURATION
        self.blizzard_cooldown = self.BLIZZARD_COOLDOWN_MAX

        temp_multiplier = self.get_temperature_damage_multiplier()
        affected_count = 0

        for animal in terrestrial_animals:
            if not is_alive(animal):
                continue

            self._apply_blizzard_slow(animal)

            cold_resistance = normalized_cold_resistance(animal)
            if cold_resistance < self.BLIZZARD_COLD_THRESHOLD:
                # Lower resistance and colder weather both increase the final damage.
                weakness = (
                    self.BLIZZARD_COLD_THRESHOLD - cold_resistance
                ) / max(self.BLIZZARD_COLD_THRESHOLD, 0.01)
                damage = self.BLIZZARD_DAMAGE_BASE * weakness * temp_multiplier
                apply_damage(animal, damage)
                affected_count += 1
                self._apply_move_lock(animal)

        log.append(f"  -> {affected_count} terrestrial animals took cold damage.")
        log.append(f"  -> Current terrestrial temperature: {self.terrestrial_temp:.1f}C")
        return log

    def _apply_blizzard_slow(self, animal):
        if not hasattr(animal, "speed"):
            return

        key = id(animal)
        if key not in self._blizzard_speed_restore:
            # Store the original speed once so the animal can be restored cleanly later.
            self._blizzard_speed_restore[key] = getattr(animal, "speed", 0)
            animal.speed = getattr(animal, "speed", 0) * self.BLIZZARD_SPEED_FACTOR

    def _apply_move_lock(self, animal):
        key = id(animal)

        if hasattr(animal, "can_move") and key not in self._blizzard_move_restore:
            self._blizzard_move_restore[key] = animal.can_move
            animal.can_move = False

        animal.frozen_turns = max(getattr(animal, "frozen_turns", 0), self.BLIZZARD_DURATION)

    def _end_blizzard(self):
        log = ["[Blizzard] The blizzard has ended."]
        self.active = False
        self._blizzard_active = False
        self.duration = 0

        # Undo temporary movement penalties applied at blizzard start.
        for key, original_speed in self._blizzard_speed_restore.items():
            animal = self._find_animal_by_id(key)
            if animal is not None and hasattr(animal, "speed"):
                animal.speed = original_speed
        self._blizzard_speed_restore.clear()

        for key, original_can_move in self._blizzard_move_restore.items():
            animal = self._find_animal_by_id(key)
            if animal is not None and hasattr(animal, "can_move"):
                animal.can_move = original_can_move
        self._blizzard_move_restore.clear()

        return log

    def _handle_glacier_collapse(self, animals):
        if not animals:
            return None

        if random.random() < self.GLACIER_COLLAPSE_PROB:
            return self.glacier_collapse(self._last_sim or animals)
        return None

    def glacier_collapse(self, animals):
        terrestrial_animals = self._filter_terrestrial(self._resolve_context(animals))
        if not terrestrial_animals:
            return None

        world_width = self.world_width or infer_world_width(terrestrial_animals)
        sea_line = infer_sea_line(terrestrial_animals, self.sea_line)

        # Prefer actual ice cells when terrain data exists so collapse effects match the map.
        ice_cells = getattr(self._last_terrain, "ice_cells", None)
        if ice_cells:
            collapse_x, collapse_y = random.choice(ice_cells)
        else:
            collapse_x = random.uniform(0.0, world_width)
            collapse_y = random.uniform(0.0, max(1.0, sea_line))

        affected_count = 0
        for animal in terrestrial_animals:
            if not is_alive(animal):
                continue

            if distance(animal, collapse_x, collapse_y) <= self.GLACIER_COLLAPSE_RADIUS:
                dist = distance(animal, collapse_x, collapse_y)
                # The closer the animal is to the collapse center, the larger the hit.
                distance_factor = 1.0 - (dist / self.GLACIER_COLLAPSE_RADIUS)
                damage = self.GLACIER_COLLAPSE_DAMAGE * clamp(distance_factor, 0.0, 1.0)
                apply_damage(animal, damage)
                affected_count += 1

        self._last_collapse_pos = (collapse_x, collapse_y)
        self._last_collapse_ttl = self.COLLAPSE_EFFECT_TTL
        if self._last_sim is not None and hasattr(self._last_sim, "last_collapse"):
            self._last_sim.last_collapse = (
                collapse_x,
                collapse_y,
                self.GLACIER_COLLAPSE_RADIUS,
                getattr(self._last_sim, "turn", 0),
            )

        return [
            f"[Glacier Collapse] Position ({collapse_x:.0f}, {collapse_y:.0f})",
            f"  -> {affected_count} animals were hit inside radius {self.GLACIER_COLLAPSE_RADIUS:.0f}.",
        ]

    def _find_animal_by_id(self, key):
        # This method is populated during update-trigger cycles.
        # If an animal object no longer exists, restoration is skipped.
        for animal in getattr(self, "_last_known_animals", []):
            if id(animal) == key:
                return animal
        return None

    def get_last_collapse_info(self):
        if self._last_collapse_pos is None:
            return None
        x, y = self._last_collapse_pos
        return (x, y, self._last_collapse_ttl)

    def get_blizzard_cooldown_ratio(self):
        return clamp(self.blizzard_cooldown / self.BLIZZARD_COOLDOWN_MAX, 0.0, 1.0)

    def get_status_summary(self):
        return {
            "temperature": self.terrestrial_temp,
            "blizzard_active": self._blizzard_active,
            "blizzard_duration": self.duration,
            "blizzard_cooldown": self.blizzard_cooldown,
            "blizzard_cooldown_ratio": self.get_blizzard_cooldown_ratio(),
            "temp_damage_multiplier": self.get_temperature_damage_multiplier(),
            "last_collapse": self.get_last_collapse_info(),
        }

    def __repr__(self):
        state = "ON" if self._blizzard_active else f"CD:{self.blizzard_cooldown}"
        return f"<EventTerrestrial temp={self.terrestrial_temp:.1f}C blizzard={state}>"


event_terrestrial = EventTerrestrial
