"""Agents representing geographical features in the visualisation"""
import mesa
import mesa_geo as mg
from shapely import Polygon, LineString

class NetworkLink(mg.GeoAgent):
    """
    A transport link between two points (e.g. a road)

    unique_id       This agent's unique ID.
    model           The model this agent is part of.
    geometry        A Shapely LineString object that defines this object's geometry.
    """
    unique_id: int
    model: mesa.Model
    geometry: LineString

class Area(mg.GeoAgent):
    """
    Represents an OSM area

    unique_id       This agent's unique ID.
    model           The model this agent is part of.
    geometry        A Shapely Polygon object that defines this object's geometry.
    """
    unique_id: int
    model: mesa.Model
    geometry: Polygon

class ResidentialArea(Area):
    """An area where people live"""

class RetailArea(Area):
    """An area with shops"""

class IndustrialArea(Area):
    """An area with industry"""
