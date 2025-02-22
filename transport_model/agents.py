"""Agents for the model"""
import random
import mesa
import mesa_geo as mg
from shapely import Point, Polygon
from utils.llm import generate_response
from .network import TransportNetwork

class Person(mg.GeoAgent):
    """
    Represents one person

    name                Person's name.
    home                ID of the person's home.
    description         Natural language description of the person.
    current_path        List of nodes that the person is travelling between (empty if not moving).
    path_offset         When this person is following a path and is in the middle of an edge,
                        gives how far through traversing it they are (in minutes).
    current_mode        Current transport mode the person is using (None if not moving).
    current_target      ID of the location the person is travelling to (None if not moving).
    walk_speed          Average speed this person can walk at (km/h).
    bike_speed          Average speed this person can cycle at (km/h).
    """
    name: str
    home: int
    description: str
    current_path: list[int]
    path_offset: float
    current_mode: str
    current_target: int
    walk_speed: float
    bike_speed: float

    def __init__(
        self,
        model: mesa.Model,
        crs: str,
        name: str,
        home: int,
        description: str
    ) -> None:
        geometry = Point(model.get_location_coords(home))
        super().__init__(model, geometry, crs)

        self.name = name
        self.home = home
        self.description = description
        self._clear_path()

        self.walk_speed = 5 # TODO: vary depending on agent definition
        self.bike_speed = 15 # TODO: vary depending on agent definition

    def __repr__(self) -> str:
        return f"Agent {self.name}"

    def _clear_path(self) -> None:
        """Clears the currently stored path"""
        self.current_path = []
        self.path_offset = 0
        self.current_mode = None
        self.current_target = None

    def _set_location(self, location: tuple[float, float]) -> None:
        """Sets this agent's current location"""
        self.geometry = Point(location)

    def _plan_trip(self, location: int, network: TransportNetwork) -> None:
        """
        Plans a trip to the location with the provided ID
        Currently it just plans the quickest route
        """
        # TODO: include the LLM in this process
        source = network.get_nearest_node((self.geometry.x, self.geometry.y))
        target_coords = self.model.get_location_coords(location)
        target = network.get_nearest_node(target_coords)
        if source != target:
            source_coords = network.get_node_coords(source)
            self._set_location(source_coords)
            self.current_path = network.plan_route(source, target)
            self.current_target = location

    def _plan_driving_trip(self, location: int) -> None:
        """Plans a driving trip"""
        self._plan_trip(location, self.model.drive_network)
        self.current_mode = "drive"

    def _plan_walking_trip(self, location: int) -> None:
        """Plans a walking trip"""
        self._plan_trip(location, self.model.walk_network)
        self.current_mode = "walk"

    def _plan_cycling_trip(self, location: int) -> None:
        """Plans a cycling trip"""
        self._plan_trip(location, self.model.bike_network)
        self.current_mode = "bike"

    def _follow_path(self, network: TransportNetwork, speed: float = None) -> None:
        """Move along the planned path on the given network"""
        path_time = network.get_path_length(self.current_path, speed)
        time = self.model.time_step
        if time > path_time - self.path_offset:
            # We have reached our destination
            new_location = self.model.get_location_coords(self.current_target)
            self._clear_path()
        else:
            # Still Travelling
            self.current_path, self.path_offset, new_location = network.traverse_path(
                path = self.current_path,
                time = time + self.path_offset,
                speed = speed
            )
        self._set_location(new_location)

    def _move(self) -> None:
        """Move along the planned path"""
        if self.current_mode == "drive":
            self._follow_path(self.model.drive_network)
        elif self.current_mode == "walk":
            self._follow_path(self.model.walk_network, self.walk_speed)
        elif self.current_mode == "bike":
            self._follow_path(self.model.bike_network, self.bike_speed)

    def step(self) -> None:
        # temp test: gets all agents to walk to and from Robert Country Vehicles
        if self.current_path:
            self._move()
        else:
            if (self.geometry.x, self.geometry.y) == self.model.get_location_coords(1):
                self._plan_walking_trip(self.home)
            else:
                self._plan_walking_trip(1)
                print(generate_response("Hello mr chatgpt"))

class NetworkLink(mg.GeoAgent):
    """A transport link between two points (e.g. a road)"""
    unique_id: int
    model: mesa.Model
    geometry: Point

class Road(NetworkLink):
    """A road for cars"""

# NOTE: currently unused
class Walkway(NetworkLink):
    """A path for pedestrians"""

# NOTE: currently unused
class Cycleway(NetworkLink):
    """A route for cyclists"""

class Area(mg.GeoAgent):
    """Represents an OSM area"""
    unique_id: int
    model: mesa.Model
    geometry: Polygon

    # NOTE: currently unused
    def get_random_point(self) -> Point:
        """Returns a random point within this area"""
        min_x, min_y, max_x, max_y = self.geometry.bounds
        point = None
        while not (point and point.within(self.geometry)):
            point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
        return point

class ResidentialArea(Area):
    """An area where people live"""

class RetailArea(Area):
    """An area with shops"""

class IndustrialArea(Area):
    """An area with industry"""
