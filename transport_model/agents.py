"""Agents for the model"""
import random
import mesa
import mesa_geo as mg
from shapely import Point, Polygon

class Person(mg.GeoAgent):
    """Represents one person"""
    def __init__(self, model: mesa.Model, pos: tuple[float, float], crs: str) -> None:
        geometry = Point(pos)
        super().__init__(model, geometry, crs)

    def __repr__(self) -> str:
        return f"Agent {self.unique_id}"

    def step(self) -> None:
        pass

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
