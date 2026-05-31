from __future__ import annotations

import random

from event import Event
from event_common import (
    apply_damage,
    clamp,
    infer_sea_line,
    infer_world_height,
    infer_world_width,
    is_alive,
    is_krill,
    is_marine,
    krill_amount,
    resolve_animals,
)


class EventMarine(Event):
    TEMP_UPDATE_INTERVAL = 600
    TEMP_BASE = -2.0
    TEMP_VARIATION = 4.0
    TEMP_DAMAGE_STEP = 0.15
    TEMP_DAMAGE_MAX = 2.0

    KRILL_RESPAWN_INTERVAL = 900
    KRILL_RESPAWN_COUNT = 2
    KRILL_RESPAWN_SIZE = 3

    STARVATION_THRESHOLD = 6
    STARVATION_RECOVERY_THRESHOLD = 10
    STARVATION_DURATION = 180
    STARVATION_HUNGER_BONUS = 4
    MAX_LOG_SIZE = 10

    def __init__(self, world_width=None, world_height=None, sea_line=None, krill_factory=None):
        super().__init__(duration=0)
        self.world_width = world_width
        self.world_height = world_height
        self.sea_line = sea_line
        self.krill_factory = krill_factory

        self.marine_temp = self.TEMP_BASE
        self._temp_timer = 0
        self._krill_respawn_timer = 0

        self.event_log = []
        self._active_event_name = None
        self._last_sim = None
        self._last_terrain = None

    def set_world_context(self, world_width=None, world_height=None, sea_line=None):
        if world_width is not None:
            self.world_width = world_width
        if world_height is not None:
            self.world_height = world_height
        if sea_line is not None:
            self.sea_line = sea_line
        return self

    def set_krill_factory(self, krill_factory):
        self.krill_factory = krill_factory
        return self

    def _resolve_context(self, subject):
        animals = resolve_animals(subject)

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

    def _sync_temperature_from_context(self):
        if self._last_terrain is None or not hasattr(self._last_terrain, "water_temp"):
            return False

        try:
            self.marine_temp = float(self._last_terrain.water_temp)
        except (TypeError, ValueError):
            return False
        return True

    def _filter_marine(self, animals):
        return [
            animal
            for animal in animals
            if is_marine(animal, sea_line=self.sea_line, terrain=self._last_terrain)
        ]

    def trigger(self, animals):
        resolved_animals = self._resolve_context(animals)
        return self.starvation(resolved_animals)

    def update(self, animals):
        resolved_animals = self._resolve_context(animals)
        turn_log = []

        # Marine turns manage water temperature, food recovery, then food shortage pressure.
        if not self._sync_temperature_from_context():
            self._update_temperature()

        # The zip project already applies climate damage in Simulation._apply_climate().
        if self._last_sim is None:
            turn_log.extend(self._apply_marine_temperature(resolved_animals))

        # When we are attached to the external simulation, that project already grows krill.
        if self._last_sim is None:
            respawn_log = self._handle_krill_respawn(resolved_animals)
            if respawn_log:
                turn_log.extend(respawn_log)

        starvation_log = self._handle_starvation(resolved_animals)
        if starvation_log:
            turn_log.extend(starvation_log)

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
        # Smooth the target so the sea feels like a slow-changing system.
        self.marine_temp = (self.marine_temp + target) / 2.0

    def _apply_marine_temperature(self, animals):
        log = []
        marine_animals = [
            animal for animal in self._filter_marine(animals) if not is_krill(animal)
        ]
        if not marine_animals:
            return log

        for animal in marine_animals:
            if hasattr(animal, "temp_dmg") and callable(animal.temp_dmg):
                # Reuse species-specific water-temperature logic when the animal already has it.
                animal.temp_dmg(self.marine_temp)
                continue

            optimum = getattr(animal, "optimum_watertemp", None)
            if optimum is None:
                continue

            try:
                optimum = float(optimum)
            except (TypeError, ValueError):
                continue

            diff = abs(self.marine_temp - optimum)
            if diff < 2.0:
                continue

            damage = clamp((diff - 2.0) * self.TEMP_DAMAGE_STEP, 0.0, self.TEMP_DAMAGE_MAX)
            apply_damage(animal, damage)

        return log

    def _handle_krill_respawn(self, animals):
        self._krill_respawn_timer += 1
        if self._krill_respawn_timer < self.KRILL_RESPAWN_INTERVAL:
            return None

        self._krill_respawn_timer = 0
        spawned = self.spawn_krill_swarm(animals, self.KRILL_RESPAWN_COUNT)
        if spawned <= 0:
            return None

        return [f"[Krill Spawn] {spawned} new krill groups were added or revived."]

    def spawn_krill_swarm(self, animals, count=1):
        spawned = 0
        # Revive existing krill first so the system can work even without a factory callback.
        revived = self._revive_dead_krill(animals, count)
        spawned += revived
        remaining = max(0, count - revived)

        if remaining > 0 and callable(self.krill_factory):
            for _ in range(remaining):
                x, y = self._random_marine_position(animals)
                created = self.krill_factory(x, y)
                if created is None:
                    continue
                if isinstance(created, (list, tuple)):
                    animals.extend(created)
                    spawned += len(created)
                else:
                    animals.append(created)
                    spawned += 1

        return spawned

    def _revive_dead_krill(self, animals, count):
        dead_krill = [animal for animal in animals if is_krill(animal) and not is_alive(animal)]
        revived = 0
        for animal in dead_krill[:count]:
            x, y = self._random_marine_position(animals)
            animal.is_alive = True
            if hasattr(animal, "hp"):
                animal.hp = max(getattr(animal, "hp", 0), 10)
            if hasattr(animal, "hunger"):
                animal.hunger = 0
            if hasattr(animal, "x"):
                animal.x = x
            if hasattr(animal, "y"):
                animal.y = y
            if hasattr(animal, "size"):
                animal.size = max(getattr(animal, "size", 0), self.KRILL_RESPAWN_SIZE)
            if hasattr(animal, "swarm_size"):
                animal.swarm_size = max(getattr(animal, "swarm_size", 0), self.KRILL_RESPAWN_SIZE)
            revived += 1
        return revived

    def _random_marine_position(self, animals):
        if self._last_terrain is not None and hasattr(self._last_terrain, "random_water_pos"):
            return self._last_terrain.random_water_pos(random)

        width = self.world_width or infer_world_width(animals)
        height = self.world_height or infer_world_height(animals)
        sea_line = infer_sea_line(animals, self.sea_line)
        return (
            random.uniform(0.0, width),
            random.uniform(sea_line, max(sea_line + 1.0, height)),
        )

    def _handle_starvation(self, animals):
        total_krill = self.get_total_krill_amount(animals)

        if self.active:
            # While starvation is active, living animals with hunger become hungry faster.
            for animal in animals:
                if not is_alive(animal) or not hasattr(animal, "hunger"):
                    continue
                animal.hunger = min(100, getattr(animal, "hunger", 0) + self.STARVATION_HUNGER_BONUS)

            self.duration -= 1
            if total_krill >= self.STARVATION_RECOVERY_THRESHOLD:
                self.active = False
                self._active_event_name = None
                self.duration = 0
                return ["[Starvation] Krill recovered. The starvation event has ended."]

            if self.duration <= 0:
                self.active = False
                self._active_event_name = None
                self.duration = 0

            return None

        if total_krill < self.STARVATION_THRESHOLD:
            return self.trigger(animals)
        return None

    def starvation(self, animals):
        total_krill = self.get_total_krill_amount(animals)
        self.active = True
        self.duration = self.STARVATION_DURATION
        self._active_event_name = "starvation"
        return [
            "[Starvation] Krill supply is critically low.",
            f"  -> Current krill amount: {total_krill}",
            f"  -> Living animals gain +{self.STARVATION_HUNGER_BONUS} hunger each turn.",
        ]

    def get_total_krill_amount(self, animals):
        if hasattr(animals, "krill_biomass") and callable(animals.krill_biomass):
            try:
                return float(animals.krill_biomass())
            except (TypeError, ValueError):
                pass

        total = 0
        for animal in resolve_animals(animals):
            if not is_alive(animal) or not is_krill(animal):
                continue

            total += krill_amount(animal)

        return total

    def get_active_krill_count(self, animals):
        return sum(1 for animal in animals if is_alive(animal) and is_krill(animal))

    def get_status_summary(self, animals):
        return {
            "marine_temperature": self.marine_temp,
            "starvation_active": self.active,
            "starvation_duration": self.duration,
            "krill_amount": self.get_total_krill_amount(animals),
            "krill_count": self.get_active_krill_count(animals),
        }

    def __repr__(self):
        state = self._active_event_name or "idle"
        return f"<EventMarine temp={self.marine_temp:.1f}C state={state}>"


event_marine = EventMarine
