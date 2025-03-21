"""Classes to help with trips and routes"""
from dataclasses import dataclass
from utils.model_time import Time

@dataclass
class Trip:
    """
    Stores information about a planned trip.

    origin          Starting location.
    destination     Desired ending location.
    start_time      Time this trip will start.
    """
    origin: str
    destination: str
    start_time: Time

@dataclass
class Route:
    """
    Stores information about the route a person is following.

    mode                The transport mode being used for this route.
    path                List of nodes remaining in this route.
    path_offset         When a person is following a path and is in the middle of an edge,
                        gives how far through traversing it they are (in minutes).
    """
    mode: str
    path: list[int]
    path_offset: float = 0.0

    def trim_path_to_node(self, node: int) -> None:
        """Updates path to remove any nodes before the provided node"""
        index = self.path.index(node)
        self.path = self.path[index:]

    def set_offset(self, new_offset: float) -> None:
        """Sets the path offset"""
        self.path_offset = new_offset

@dataclass
class RoadType:
    """
    A type of road.

    highway         The road class e.g. "primary"
    maxspeed        The speed limit e.g. "40 mph"
    """
    highway: str
    maxspeed: str

    def __hash__(self):
        return hash((self.highway, self.maxspeed))

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

    def update_travel_time(self, new_time: float) -> None:
        """
        Updates the average travel time for this entry

        Args:
            new_time    Time (in mins) to update the average with.
        """
        self.travel_time = ((self.travel_time * self.count) + new_time) / (self.count + 1)
        self.count += 1

class ActiveMemoryEntry(MemoryEntry):
    """
    An entry for an active travel route in TravelMemory.
    
    comfort         A list of comfort values for each edge.
    """
    comfort: list[float]

    def __init__(self, mode: str, path: list[int]) -> None:
        self.comfort = []
        super().__init__(mode, path)

    def add_comfort(self, val: int) -> None:
        """Adds a comfort value to the stored list"""
        self.comfort.append(val)

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
