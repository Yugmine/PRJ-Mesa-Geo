"""Memory used to store the agents' past experiences with travel"""
from dataclasses import dataclass
from transport_model.time import Time
from .routes import Route, RoadType

@dataclass
class ModeChoice:
    """
    Stores information about a mode choice the LLM has made.
    """
    day: int
    time: Time
    origin: str
    destination: str
    mode: str
    justification: str

class MemoryEntry:
    """
    An entry for one route in TravelMemory.

    travel_time     The mean time this route has taken to complete.
    count           How many times this route has been completed.
    """
    travel_time: float
    count: int

    def __init__(self) -> None:
        self.travel_time = 0.0
        self.count = 0

    def update(self, new_time: float) -> None:
        """
        Updates the travel time average.

        Args:
            new_time    Time (in mins) to update the average with.
        """
        self.travel_time = ((self.travel_time * self.count) + new_time) / (self.count + 1)
        self.count += 1

class ActiveMemoryEntry(MemoryEntry):
    """
    An entry for an active travel route in TravelMemory.
    
    comfort         Weighted average of comfort for this route. 
    """
    comfort: float

    def __init__(self) -> None:
        self.comfort = 0.0
        super().__init__()

    def active_update(self, new_time: float, new_comfort: float) -> None:
        """
        Updates the stored comfort average before calling the superclass update method.

        Args:
            new_time: Time (in mins) to update the average with.
            comfort: Comfort value to update the average with.
        """
        self.comfort = ((self.comfort * self.count) + new_comfort) / (self.count + 1)
        super().update(new_time)

class TravelMemory:
    """
    Stores memory of previous experiences with travel.
    Memories can be used to influence planning + mode choice.

    route_memory        Stores memories of previous routes.
                        Uses the form Route : entry
    comfort_memory      Caches comfort values generated for the given road type.
                        Uses the form RoadType: {mode: comfort}
    justifications      Stores justifications for mode choices.
    """
    route_memory: dict[Route, MemoryEntry]
    comfort_memory: dict[RoadType, dict[str, int]]
    justifications: list[ModeChoice]

    def __init__(self) -> None:
        self.route_memory = {}
        self.comfort_memory = {}
        self.justifications = []

    def _create_route_entry(self, route: Route) -> MemoryEntry:
        """
        Creates a new entry in route_memory.

        Args:
            route: The route to create an entry for.

        Returns:
            The new route entry.
        """
        if route.mode in ("bike", "walk"):
            entry = ActiveMemoryEntry()
        else:
            entry = MemoryEntry()
        self.route_memory[route] = entry
        return entry

    def get_route_entry(self, route: Route) -> MemoryEntry | None:
        """
        Args:
            route: The route to get the entry for.
        
        Returns:
            The entry for the specified mode and path
            (returns None if it doesn't exist).
        """
        if route not in self.route_memory:
            return None
        return self.route_memory[route]

    def store_route(
        self,
        route: Route,
        travel_time: float,
        comfort: float = None
    ) -> None:
        """
        Stores a memory of a completed route.

        Args:
            route: The route.
            travel_time: How long (in minutes) the route took to complete.
            comfort (Optional): If it was a walking/cycling route,
                                the average comfort of the route.
        """
        entry = self.get_route_entry(route)
        if entry is None:
            entry = self._create_route_entry(route)

        if comfort is None:
            entry.update(travel_time)
        else:
            entry.active_update(travel_time, comfort)

    def route_is_stored(self, route: Route) -> bool:
        """
        Args:
            route: The route to check for.
        Returns:
            True if the given route is stored in memory, False otherwise"""
        return self.get_route_entry(route) is not None

    def store_comfort(self, road: RoadType, mode: str, comfort: int) -> None:
        """
        Stores the given comfort value.
        
        Args:
            road: The road type the comfort value was generated for.
            mode: The transport mode.
            comfort: The generated comfort value.
        """
        if road not in self.comfort_memory:
            self.comfort_memory[road] = {}
        self.comfort_memory[road][mode] = comfort

    def get_comfort(self, road: RoadType, mode: str) -> int | None:
        """
        Args:
            road: The road type.
            mode: The transport mode.
        
        Returns:
            The stored comfort value for the given road type and mode,
            or None if it doesn't exist in memory.
        """
        if road not in self.comfort_memory or mode not in self.comfort_memory[road]:
            return None
        return self.comfort_memory[road][mode]

    def store_mode_choice(self, choice: ModeChoice) -> None:
        """
        Stores the given mode choice in memory.

        Args:
            choice: The mode choice to store.
        """
        self.justifications.append(choice)
