from __future__ import annotations

from event import Event
from event_common import apply_damage, is_alive, resolve_animals


class EventEnd(Event):
    IMPACT_DAMAGE = 9999

    def __init__(
        self,
        trigger_turn=None,
        warning_duration=60,
        warning_label="Meteor Warning",
        impact_label="Meteor Impact",
        end_reason="Final impact event occurred.",
    ):
        super().__init__(duration=warning_duration)
        self.trigger_turn = trigger_turn
        self.warning_duration = warning_duration
        self.warning_label = warning_label
        self.impact_label = impact_label
        self.end_reason = end_reason
        self.turn_count = 0
        self.game_over = False
        self.finished = False
        self.event_log = []
        self._armed = False
        self._last_sim = None

    def _resolve_context(self, subject):
        animals = resolve_animals(subject)
        self._last_sim = subject if hasattr(subject, "animals") else None
        return animals

    def arm(self, warning_duration=None):
        self._armed = True
        if warning_duration is not None:
            self.warning_duration = warning_duration
        return self

    def trigger(self, animals):
        resolved_animals = self._resolve_context(animals)
        if self.finished:
            return []

        # The end event has a warning phase first, then the actual impact on later turns.
        self.active = True
        self.duration = self.warning_duration
        self._armed = False

        if self.duration <= 0:
            return self._impact(resolved_animals)

        log = [f"[{self.warning_label}] Impact in {self.duration} turns."]
        self.event_log.extend(log)
        return log

    def update(self, animals):
        resolved_animals = self._resolve_context(animals)
        self.turn_count += 1

        if self.finished:
            return []

        if not self.active:
            if self._armed or (self.trigger_turn is not None and self.turn_count >= self.trigger_turn):
                return self.trigger(self._last_sim or resolved_animals)
            return []

        self.duration -= 1
        if self.duration > 0:
            return []

        return self._impact(resolved_animals)

    def _impact(self, animals):
        hit_count = 0
        for animal in animals:
            if not is_alive(animal):
                continue
            # This is the terminal event, so it intentionally uses overwhelming damage.
            apply_damage(animal, self.IMPACT_DAMAGE)
            hit_count += 1

        self.active = False
        self.finished = True
        self.game_over = True
        self.duration = 0
        if self._last_sim is not None:
            if hasattr(self._last_sim, "running"):
                self._last_sim.running = False
            if hasattr(self._last_sim, "end_reason"):
                self._last_sim.end_reason = self.end_reason

        log = [
            f"[{self.impact_label}] The final event has started.",
            f"  -> {hit_count} living animals were removed by the impact.",
            "  -> Simulation should now end.",
        ]
        self.event_log.extend(log)
        return log

    def get_status_summary(self):
        return {
            "turn_count": self.turn_count,
            "active": self.active,
            "remaining_warning_turns": self.duration,
            "game_over": self.game_over,
            "finished": self.finished,
        }

    def __repr__(self):
        return (
            f"<EventEnd active={self.active} "
            f"remaining={self.duration} game_over={self.game_over}>"
        )


event_end = EventEnd
