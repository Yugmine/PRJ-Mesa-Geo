"""Classes to help with trips and routes"""
from dataclasses import dataclass

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
    start_time: tuple[int, int]

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

class TripMemory:
    """
    Stores memory of previous trip lengths.
    Memories can be used to influence planning + mode choice.

    memory          Stores memories of previous trips
                    Uses the form (origin, destination) : {mode: travel_time}
    """
    memory: dict[tuple[str, str, str], dict[str, float]]

    def __init__(self) -> None:
        self.memory = {}

    def _calculate_trip_time(
            self,
            start_time: tuple[int, int],
            end_time: tuple[int, float]
        ) -> float:
        """Calculates how long a trip took (in minutes)"""
        # FIXME: Assumes trips can't take longer than a day
        (start_hour, start_minute) = start_time
        (end_hour, end_minute) = end_time

        if end_hour < start_hour:
            # We've rolled over to tomorrow
            time_before_midnight = (60 * (23 - start_hour)) + (60 - start_minute)
            time_after_midnight = (60 * end_hour) + end_minute
            return time_before_midnight + time_after_midnight

        return (60 * (end_hour - start_hour)) + (end_minute - start_minute)

    def add_trip(
            self,
            trip: Trip,
            mode: str,
            end_time: tuple[int, float]
        ) -> None:
        """Adds a trip to the memory"""
        # Currently, only stores the latest trip
        # TODO: store an average over all trips?
        path = (trip.origin, trip.destination)
        if path not in self.memory:
            self.memory[path] = {}
        trip_time = self._calculate_trip_time(trip.start_time, end_time)
        self.memory[path][mode] = trip_time

    def get_trip_times(self, trip: Trip) -> dict[str, float]:
        """Gets the remembered travel times for the given trip"""
        if (trip.origin, trip.destination) not in self.memory:
            return {}
        return self.memory[(trip.origin, trip.destination)]
