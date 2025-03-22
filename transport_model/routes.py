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
    info            Any relevant natural language information about the road
    """
    highway: str
    maxspeed: str
    info: str = "n/a"

    def __hash__(self):
        return hash((self.highway, self.maxspeed, self.info))
