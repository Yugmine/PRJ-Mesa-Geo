"""Memory used to store the agents' past experiences with travel"""
from typing import override
from .routes import Trip, Route, RoadType

class MemoryEntry:
    """
    An entry for one route in TravelMemory.

    mode            The transport mode used for the route.
    path            The path taken for the route.
    travel_time     The mean time this route has taken to complete.
    count           How many times this route has been completed.
    """
    mode: str
    path: list[int]
    travel_time: float
    count: int

    def __init__(self, mode: str, path: list[int]) -> None:
        self.mode = mode
        self.path = path
        self.travel_time = 0.0
        self.count = 0

    def complete_memory(self, new_time: float) -> None:
        """
        Completes the use of this entry, updating the travel time average.

        Args:
            new_time    Time (in mins) to update the average with.
        """
        self.travel_time = ((self.travel_time * self.count) + new_time) / (self.count + 1)
        self.count += 1

class ActiveMemoryEntry(MemoryEntry):
    """
    An entry for an active travel route in TravelMemory.
    
    comfort             Weighted average of comfort for this route.
    edge_comfort        Comfort values for each edge in the route.
    lengths             The length of each edge.    
    """
    comfort: float
    edge_comfort: list[int]
    lengths: list[float]

    def __init__(self, mode: str, path: list[int]) -> None:
        self.comfort = 0.0
        self._clear_temp_vars()
        super().__init__(mode, path)

    def _clear_temp_vars(self) -> None:
        """
        Vars used every time this route is re-used.
        Need to be reset in between.
        """
        self.edge_comfort = []
        self.lengths = []

    def _compute_comfort_average(self) -> float:
        """Computes an average comfort value weighted by edge length."""
        total_length = sum(self.lengths)
        weighted_comfort = []
        for i, comfort_val in enumerate(self.edge_comfort):
            weighted_val = comfort_val * (self.lengths[i] / total_length)
            weighted_comfort.append(weighted_val)
        return sum(weighted_comfort)

    def add_comfort(self, comfort_val: int, length: float) -> None:
        """Adds a comfort value to the stored list"""
        self.edge_comfort.append(comfort_val)
        self.lengths.append(length)

    @override
    def complete_memory(self, new_time: float) -> None:
        """Updates the stored comfort average before calling the superclass method."""
        new_comfort = self._compute_comfort_average()
        self.comfort = ((self.comfort * self.count) + new_comfort) / (self.count + 1)
        self._clear_temp_vars()
        super().complete_memory(new_time)


class TravelMemory:
    """
    Stores memory of previous experiences with travel..
    Memories can be used to influence planning + mode choice.

    journey_memory      Stores memories of previous journeys.
                        Uses the form (origin, destination) : [list of entries]
    comfort_memory      Caches comfort values generated for the given road type.
                        Uses the form RoadType: {mode: comfort}
    """
    journey_memory: dict[tuple[str, str], list[MemoryEntry]]
    comfort_memory: dict[RoadType, dict[str, int]]

    def __init__(self) -> None:
        self.journey_memory = {}
        self.comfort_memory = {}

    def journey_entry_by_key(self, key: tuple[str, str], mode: str, path: list[int]) -> MemoryEntry:
        """
        Gets the entry for the specified key and route.
        Returns None if it doesn't exist.
        """
        if key not in self.journey_memory:
            return None
        entries = self.journey_memory[key]
        for entry in entries:
            if entry.mode == mode and entry.path == path:
                return entry
        return None

    def get_or_init_journey(self, trip: Trip, route: Route) -> MemoryEntry:
        """Gets an existing journey entry or initialises one if it doesn't exist"""
        key = (trip.origin, trip.destination)
        if key not in self.journey_memory:
            self.journey_memory[key] = []
        entry = self.journey_entry_by_key(key, route.mode, route.path)
        if entry is None:
            if route.mode in ("bike", "walk"):
                entry = ActiveMemoryEntry(route.mode, route.path)
            else:
                entry = MemoryEntry(route.mode, route.path)
            self.journey_memory[key].append(entry)
        return entry

    def store_comfort(self, road: RoadType, mode: str, comfort: int) -> None:
        """Stores the given comfort value"""
        if road not in self.comfort_memory:
            self.comfort_memory[road] = {}
        self.comfort_memory[road][mode] = comfort

    def get_comfort(self, road: RoadType, mode: str) -> int:
        """Gets the stored comfort value for the given road type, or None"""
        if road not in self.comfort_memory or mode not in self.comfort_memory[road]:
            return None
        return self.comfort_memory[road][mode]
