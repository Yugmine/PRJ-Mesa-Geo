"""Handles transport networks and operations on them"""
from typing import override
from dataclasses import dataclass
import osmnx as ox
import networkx as nx
from sklearn.neighbors import KDTree
from geopandas import GeoDataFrame
from shapely import LineString
from .routes import Route

@dataclass
class Edge:
    """
    Represents an edge in the graph.
    
    u       ID of the starting node of this edge.
    v       ID of the ending node of this edge.
    """
    u: int
    v: int

class TransportNetwork():
    """Represents a transport network"""
    graph: nx.MultiDiGraph
    kd_tree: KDTree

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph
        node_positions = [(node[1]["x"], node[1]["y"]) for node in self.graph.nodes.data()]
        self.kd_tree = KDTree(node_positions)

    def _get_path_duration(self, path: list[int], speed: float = None) -> float:
        """
        Gets the length of the provided path (in minutes)
        
        speed is optional and only used for walking + cycling
        """
        total_time = 0
        for i in range(len(path) - 1):
            edge_info = self.graph.get_edge_data(path[i], path[i + 1])[0]
            total_time += self._get_edge_time(edge_info, speed)
        return total_time

    def _get_final_edge(
            self,
            path: list[int],
            time: float,
            speed: float = None
        ) -> tuple[Edge, float, float]:
        """
        Gets which edge we'll end up on after moving for the specified amount
        of time (in minutes), and how far through traversing it we are.

        Returns:
        - Edge start node
        - Edge end node
        - Edge traversal time (in minutes)
        - How far through traversing the edge we are (in minutes)
        """
        cumulative_time = 0
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i + 1])[0]
            edge_time = self._get_edge_time(edge_data, speed)
            if cumulative_time + edge_time > time:
                time_along_edge = time - cumulative_time
                return Edge(path[i], path[i + 1]), edge_time, time_along_edge
            cumulative_time += edge_time
        return None

    def _create_line(self, edge: Edge) -> LineString:
        """Creates a Shapely LineString for the provided edge"""
        start_pos = self.get_node_coords(edge.u)
        end_pos = self.get_node_coords(edge.v)
        return LineString([start_pos, end_pos])

    def _get_edge_geometry(self, edge: Edge) -> LineString:
        """
        Gets the edge geometry for the provided edge,
        or creates a line if it doesn't have any set geometry.
        """
        edge_data = self.graph.get_edge_data(edge.u, edge.v)[0]

        if "geometry" in edge_data:
            return edge_data["geometry"]

        return self._create_line(edge)

    def _get_point_along_edge(
            self,
            edge: Edge,
            progress: float
        ) -> tuple[float, float]:
        """
        Gets a point along the provided edge.
        progress is how far along the edge the point should be.
        e.g. if progress = 0.4, the point should be 40% along the edge.
        """
        geometry = self._get_edge_geometry(edge)
        interpolation_dist =  progress * geometry.length
        new_point = geometry.interpolate(interpolation_dist)
        return (new_point.x, new_point.y)

    def get_nearest_node(self, coords: tuple[float, float]) -> int:
        """Gets the id of the nearest node in the road network to the provided point"""
        node_index = self.kd_tree.query([coords], k=1, return_distance=False)
        node_id = list(self.graph.nodes)[node_index[0,0]]
        return node_id

    def get_node_coords(self, node_id: int) -> tuple[float, float]:
        """Gets the coordinates of the specified node"""
        return self.graph.nodes[node_id]["x"], self.graph.nodes[node_id]["y"]

    def get_edges_as_gdf(self) -> GeoDataFrame:
        """Returns a gdf with the edges of this network's graph"""
        gdfs = ox.convert.graph_to_gdfs(self.graph) # tuple w/ format (nodes, edges)
        return gdfs[1]

    def traverse_route(
            self,
            route: Route,
            time_step: int,
            speed: float = None
        ) -> tuple[float, float]:
        """
        Traverses the provided route.

        speed is optional and only used when calculating edge time for walking + cycling

        Returns:
        - New location for the agent (None if route is complete)
        """
        path_time = self._get_path_duration(route.path, speed)
        traversal_time = time_step + route.path_offset

        if traversal_time > path_time:
            # Route completed
            return None

        edge, edge_time, new_offset = self._get_final_edge(route.path, traversal_time, speed)
        route.trim_path_to_node(edge.u)
        route.set_offset(new_offset)

        progress = new_offset / edge_time
        new_location = self._get_point_along_edge(edge, progress)
        return new_location

    def _get_edge_time(self, attrs: dict, speed: float = None) -> float:
        """Get the time taken to traverse the given edge"""
        raise NotImplementedError("Implemented in subclass")

    def plan_route(self, source: int, target: int) -> list[tuple[int, int]]:
        """Plan a route from the source node to the target node"""
        raise NotImplementedError("Implemented in subclass")

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

    def _astar_weight(self, u: int, v: int, attrs: dict) -> float:
        """Wrapper to match expected function signature for astar weight function"""
        return self._get_edge_time(attrs[0])

    @override
    def _get_edge_time(self, attrs: dict, speed: float = None) -> float:
        """
        Calculates how long (in minutes) it would take to traverse
        a link travelling at the speed limit.

        speed is not used in this function (speed is assumed to be at the limit on any edge)
        """
        speed_limit = self._get_speed_limit(attrs)
        return ((attrs["length"] / 1000) / speed_limit) * 60

    @override
    def plan_route(self, source: int, target: int) -> list[tuple[int, int]]:
        """Plans a driving route from the source node to the target node"""
        return nx.astar_path(self.graph, source, target, weight=self._astar_weight)

class ActiveNetwork(TransportNetwork):
    """Network for active travel (walking + cycling)"""

    @override
    def _get_edge_time(self, attrs: dict, speed: float = None) -> float:
        """
        Calculates how long (in minutes) it would take to traverse
        a link travelling at the given speed
        """
        return ((attrs["length"] / 1000) / speed) * 60

    @override
    def plan_route(self, source: int, target: int) -> list[tuple[int, int]]:
        """Plans a route from the source node to the target node"""
        return nx.astar_path(self.graph, source, target, weight="length")

class WalkNetwork(ActiveNetwork):
    """Network for walking"""

class BikeNetwork(ActiveNetwork):
    """Network for cycling"""
