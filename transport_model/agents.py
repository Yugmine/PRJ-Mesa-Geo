"""Agents for the model"""
import random
import mesa
import mesa_geo as mg
from shapely import Point, Polygon

class Person(mg.GeoAgent):
    """Represents one person"""
    name: str
    home: int
    description: str

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

    def __repr__(self) -> str:
        return f"Agent {self.name}"

    def step(self) -> None:
        # temporary test that moves the agent to its nearest node in the driving network
        nearest_node = self.model.drive_network.get_nearest_node(self.geometry)
        self.geometry = Point(self.model.drive_network.get_node_coords(nearest_node))

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
