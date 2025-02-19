"""Agents for the model"""
import random
import mesa
import mesa_geo as mg
from shapely import Point, Polygon

class Person(mg.GeoAgent):
    """Represents one person"""
    name: str
    home: tuple[float, float]
    description: str

    def __init__(
        self,
        model: mesa.Model,
        crs: str,
        name: str,
        home: tuple[float, float],
        description: str
    ) -> None:
        geometry = Point(home)
        super().__init__(model, geometry, crs)

        self.name = name
        self.home = home
        self.description = description

    def __repr__(self) -> str:
        return f"Agent {self.name}"

    def step(self) -> None:
        nearest_node = self.model.get_nearest_node(self.geometry)
        self.geometry = Point(self.model.network.nodes[nearest_node]["x"], self.model.network.nodes[nearest_node]["y"])

class Road(mg.GeoAgent):
    """A road that links two points"""
    unique_id: int
    model: mesa.Model
    geometry: Point

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
