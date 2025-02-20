"""Agents for the model"""
import random
import mesa
import mesa_geo as mg
from shapely import Point, Polygon
from .network import TransportNetwork

class Person(mg.GeoAgent):
    """
    Represents one person

    name                Person's name.
    home                ID of the person's home.
    description         Natural language description of the person.
    current_path        List of nodes that the person is travelling between (empty if not moving).
    path_offset         When this person is following a path and is in the middle of an edge,
                        gives how far along the edge they are.
    current_mode        Current transport mode the person is using (None if not moving).
    current_target      ID of the location the person is travelling to (None if not moving).
    walk_dist_per_step  Distance this person can walk in one time step.
    bike_dist_per_step  Distance this person can cycle in one time step.
    """
    name: str
    home: int
    description: str
    current_path: list[int]
    path_offset: float
    current_mode: str
    current_target: int
    walk_dist_per_step: int
    bike_dist_per_step: int

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

        walk_speed = 1.4 # TODO: vary depending on agent definition
        bike_speed = 4.2 # TODO: vary depending on agent definition
        self.walk_dist_per_step = self.model.time_step * 60 * walk_speed
        self.bike_dist_per_step = self.model.time_step * 60 * bike_speed

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

    def _plan_active_trip(self, location: int, network: TransportNetwork) -> None:
        """
        Plans a trip to the location with the provided ID
        Currently it just plans the quickest route
        """
        # TODO: include the LLM in this process + do for car
        source= network.get_nearest_node((self.geometry.x, self.geometry.y))
        target_coords = self.model.get_location_coords(location)
        target = network.get_nearest_node(target_coords)
        if source != target:
            source_coords = network.get_node_coords(source)
            self._set_location(source_coords)
            self.current_path = network.plan_route(source, target)
            self.current_target = location

    def _plan_walking_trip(self, location: int) -> None:
        """Plans a walking trip"""
        self._plan_active_trip(location, self.model.walk_network)
        self.current_mode = "walk"

    def _plan_cycling_trip(self, location: int) -> None:
        """Plans a cycling trip"""
        self._plan_active_trip(location, self.model.bike_network)
        self.current_mode = "bike"

    def _follow_path_simple(self, dist: float, network: TransportNetwork) -> None:
        """Move along the planned path by bike or walking (at constant speed)"""
        path_length = network.get_path_length(self.current_path)
        if dist > path_length - self.path_offset:
            # We have reached our destination
            new_location = self.model.get_location_coords(self.current_target)
            self._clear_path()
        else:
            # Still travelling
            self.current_path, self.path_offset, new_location = network.traverse_path(self.current_path, dist + self.path_offset)
        self._set_location(new_location)

    def _move(self) -> None:
        """Move along the planned path"""
        # TODO: handle driving
        if self.current_mode == "drive":
            raise NotImplementedError
        elif self.current_mode == "walk":
            self._follow_path_simple(self.walk_dist_per_step, self.model.walk_network)
        elif self.current_mode == "bike":
            self._follow_path_simple(self.bike_dist_per_step, self.model.bike_network)

    def step(self) -> None:
        # temp test: gets all agents to walk to and from Tonbridge station
        if self.current_path:
            self._move()
        else:
            if (self.geometry.x, self.geometry.y) == self.model.get_location_coords(3):
                self._plan_walking_trip(self.home)
            else:
                self._plan_walking_trip(3)

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
