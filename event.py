from abc import ABC, abstractmethod


class Event(ABC):
    def __init__(self, duration=0):
        self.active = False
        self.duration = duration

    @abstractmethod
    def trigger(self, animals):
        # Start the event and return any log messages for this turn.
        pass

    @abstractmethod
    def update(self, animals):
        # Advance the event by one turn and return turn logs.
        pass

    def end(self):
        self.active = False
        self.duration = 0
