"""Handles transport networks and operations on them"""
from typing import override
import osmnx as ox
import networkx as nx
from sklearn.neighbors import KDTree
from shapely import Point
from geopandas import GeoDataFrame

class TransportNetwork():
    """Represents a transport network"""
    graph: nx.MultiDiGraph
    kd_tree: KDTree

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph
        node_positions = [(node[1]["x"], node[1]["y"]) for node in self.graph.nodes.data()]
        self.kd_tree = KDTree(node_positions)

    def get_nearest_node(self, pos: Point) -> int:
        """Gets the id of the nearest node in the road network to the provided point"""
        node_index = self.kd_tree.query([(pos.x, pos.y)], k=1, return_distance=False)
        node_id = list(self.graph.nodes)[node_index[0,0]]
        return node_id

    def get_edges_as_gdf(self) -> GeoDataFrame:
        """Returns a gdf with the edges of this network's graph"""
        gdfs = ox.convert.graph_to_gdfs(self.graph) # tuple w/ format (nodes, edges)
        return gdfs[1]

    def plan_route(self, source: int, target: int) -> list[tuple[int, int]]:
        """Plans a route from the source node to the target node"""
        return nx.astar_path(self.graph, source, target, weight="length")

class DriveNetwork(TransportNetwork):
    """
    Network for driving
    
    DEFAULT_LIMIT is the speed limit (in km/h) applied to a road without a defined speed limit
    """
    DEFAULT_LIMIT = 30

    def _get_num_limit(self, limit: str) -> float:
        """
        Converts the provided speed limit to a number in km/h
        Expected limit format e.g. '20 mph'
        """
        parts = limit.split()
        speed = int(parts[0])
        if parts[1] == "mph":
            speed *= 1.609344
        return speed

    def _get_speed_limit(self, attrs: dict) -> float:
        """Extracts the speed limit from the provided attribute dict"""
        if "maxspeed" not in attrs:
            return self.DEFAULT_LIMIT

        limit = attrs["maxspeed"]
        # Some edges have two speed limits (where the limit changes I assume)
        # In this case average the two limits
        if isinstance(limit, list):
            num_limits = [self._get_num_limit(x) for x in limit]
            return sum(num_limits) / len(limit)
        return self._get_num_limit(limit)

    def _get_edge_time(self, u: int, v: int, attrs: dict) -> float:
        """
        Calculates how long (in hours) it would take to traverse
        a link travelling at the speed limit.
        """
        speed_limit = self._get_speed_limit(attrs[0])
        return (attrs[0]["length"] / 1000) / speed_limit

    @override
    def plan_route(self, source: int, target: int) -> list[tuple[int, int]]:
        """Plans a driving route from the source node to the target node"""
        return nx.astar_path(self.graph, source, target, weight=self._get_edge_time)

class WalkNetwork(TransportNetwork):
    """Network for walking"""

class BikeNetwork(TransportNetwork):
    """Network for cycling"""
