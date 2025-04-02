"""Classes to help with trips and routes"""
from dataclasses import dataclass
from transport_model.time import Time

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
    """
    mode: str
    path: list[int]

    def from_node(self, node: int) -> list[int]:
        """
        Args:
            node: The first node in the returned path.
        
        Returns:
            The path from the given node onwards.
        """
        index = self.path.index(node)
        return self.path[index:]

    def between_nodes(self, start: int, end: int) -> list[int]:
        """
        Args:
            start: First node.
            end: Last node

        Returns:
            The path between the two provided nodes (inclusive).
        """
        start_index = self.path.index(start)
        # +1 because list slicing excludes the last element
        end_index = self.path.index(end) + 1
        return self.path[start_index:end_index]

    def __hash__(self):
        return hash((self.mode, tuple(self.path)))

@dataclass
class RouteProgress:
    """
    Stores information about how far through traversing a route an agent is.

    node        The node the agent has got up to.
    offset      When a person is in the middle of an edge,
                gives how far through traversing it they are (in minutes).
    """
    node: int
    offset: float = 0.0

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
