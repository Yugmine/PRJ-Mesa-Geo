"""Handles transport networks and operations on them"""
from typing import override
from dataclasses import dataclass
from collections.abc import Iterator
import osmnx as ox
import networkx as nx
from sklearn.neighbors import KDTree
from geopandas import GeoDataFrame
from shapely import LineString
from .routes import Route, RouteProgress

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
    """
    Represents a transport network
    
    graph       The graph that represents the transport network.
    kd_tree     A KDTree initialised with the positions of nodes in the graph.
                Used to find the nearest node to a given point.
    """
    graph: nx.MultiDiGraph
    kd_tree: KDTree

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph
        node_positions = [(node[1]["x"], node[1]["y"]) for node in self.graph.nodes.data()]
        self.kd_tree = KDTree(node_positions)

    def _get_final_edge(
            self,
            path: list[int],
            time: float,
            speed: float = None
        ) -> tuple[Edge, float, float]:
        """
        Gets the edge we'll end up on after traversing the given path.

        Args:
            path: The path to traverse.
            time: How many minutes to traverse the path for.
            speed: (For walking or cycling), the speed to traverse the path at.

        Returns:
            Final Edge.
            Edge traversal time (in minutes).
            How far through traversing the edge we are (in minutes).
        """
        cumulative_time = 0
        for i in range(len(path) - 1):
            edge_data = self.edge_info(path[i], path[i + 1])
            edge_time = self._get_edge_time(edge_data, speed)
            if cumulative_time + edge_time > time:
                time_along_edge = time - cumulative_time
                return Edge(path[i], path[i + 1]), edge_time, time_along_edge
            cumulative_time += edge_time
        return None

    def _create_line(self, edge: Edge) -> LineString:
        """
        Args:
            edge: The edge to create a LineString for

        Returns:
            A LineString between the edge's start and end nodes.
        """
        start_pos = self.get_node_coords(edge.u)
        end_pos = self.get_node_coords(edge.v)
        return LineString([start_pos, end_pos])

    def _get_edge_geometry(self, edge: Edge) -> LineString:
        """
        Args:
            edge: The edge to get geometry for.
        
        Returns:
            The edge's geometry if it has set geometry, or a
            straight line between its start and end nodes.
        """
        edge_data = self.edge_info(edge.u, edge.v)

        if "geometry" in edge_data:
            return edge_data["geometry"]

        return self._create_line(edge)

    def _get_point_along_edge(
            self,
            edge: Edge,
            progress: float
        ) -> tuple[float, float]:
        """
        Args:
            edge: The edge to get a point on.
            progress: A proportion along the edge to get a point for.
                      e.g. if progress = 0.4, the point should be 40% along the edge.
        
        Returns:
            An (x, y) coordinate the specified proportion along the edge.
        """
        geometry = self._get_edge_geometry(edge)
        interpolation_dist =  progress * geometry.length
        new_point = geometry.interpolate(interpolation_dist)
        return (new_point.x, new_point.y)

    def get_path_duration(self, path: list[int], speed: float = None) -> float:
        """
        Args:
            path: The path to get a duration for.
            speed: (Only for walking and cycling) the agent's speed.
        
        Returns:
            How long it takes to traverse the given path (in minutes).
        """
        total_time = 0
        for i in range(len(path) - 1):
            edge_info = self.edge_info(path[i], path[i + 1])
            total_time += self._get_edge_time(edge_info, speed)
        return total_time

    def get_path_distance(self, path: list[int]) -> float:
        """
        Args:
            path: The path to get a distance for.
        
        Returns:
            The length of the path in metres.
        """
        total_distance = 0
        for i in range(len(path) - 1):
            edge_info = self.edge_info(path[i], path[i + 1])
            total_distance += edge_info["length"]
        return total_distance

    def get_nearest_node(self, coords: tuple[float, float]) -> int:
        """
        Args:
            coords: The coords to search for a node near.

        Returns:
            The ID of the nearest node in the graph to the provided coords.
        """
        node_index = self.kd_tree.query([coords], k=1, return_distance=False)
        node_id = list(self.graph.nodes)[node_index[0,0]]
        return node_id

    def get_node_coords(self, node_id: int) -> tuple[float, float]:
        """
        Args:
            node_id: The ID of the node to get coordinates for.
        
        Returns:
            The (x, y) coordinates of the node.
        """
        return self.graph.nodes[node_id]["x"], self.graph.nodes[node_id]["y"]

    def get_edges_as_gdf(self) -> GeoDataFrame:
        """
        Returns:
            A GeoDataFrame with the edges of this network's graph
        """
        gdfs = ox.convert.graph_to_gdfs(self.graph) # tuple w/ format (nodes, edges)
        return gdfs[1]

    def traverse_route(
            self,
            route: Route,
            progress: RouteProgress,
            time_step: int,
            speed: float = None
        ) -> tuple[RouteProgress, tuple[float, float] | None, float]:
        """
        Traverses the provided route.

        Args:
            route: The route to traverse.
            progress: How far through traversing the route the agent is.
            time_step: How much time passes with each model time step (in minutes).
            speed: (Only for walking and cycling) the speed to traverse the route at.

        Returns:
            Agent's new progress through the route.
            New location for the agent (None if route is complete).
            Remaining time in the step (in minutes).
            (e.g. if step is 5 mins and agent only needs to move for
            3 mins to finish, return 2)
        """
        remaining_path = route.from_node(progress.node)
        path_time = self.get_path_duration(remaining_path, speed)
        traversal_time = time_step + progress.offset

        if traversal_time > path_time:
            # Route completed
            time_left = traversal_time - path_time
            return RouteProgress(route.path[-1]), None, time_left

        edge, edge_time, new_offset = self._get_final_edge(remaining_path, traversal_time, speed)
        new_progress = RouteProgress(edge.u, new_offset)

        edge_progress = new_offset / edge_time
        new_location = self._get_point_along_edge(edge, edge_progress)
        return new_progress, new_location, 0.0

    def edge_info(self, edge_u, edge_v) -> dict:
        """
        Args:
            edge_u: The start node of the edge.
            edge_v: The end node fo the edge.
        Returns:
            The info dict for the provided edge.
        """
        return self.graph.get_edge_data(edge_u, edge_v)[0]

    def _get_edge_time(self, attrs: dict, speed: float = None) -> float:
        """
        Args:
            attrs: The info dict of the edge to traverse.
            speed: (Only for walking and cycling) The speed to traverse the edge at.
        
        Returns:
            The time taken to traverse the given edge.
        """
        raise NotImplementedError("Implemented in subclass")

    def plan_paths(self, source: int, target: int) -> Iterator[list[int]]:
        """
        Args:
            source: The start node.
            target: The end node.
        
        Returns:
            an iterator of shortest paths from the source node to the target node.
        """
        raise NotImplementedError("Implemented in subclass")

class DriveNetwork(TransportNetwork):
    """
    Network for driving.
    
    default_limit       The speed limit (in km/h) applied to roads with no defined speed limit.
    speed_factor        Multiplied by speed limit to get the speed a car will travel at.
    """
    default_limit: int
    speed_factor: float

    def __init__(
        self,
        graph: nx.MultiDiGraph,
        default_limit: int,
        speed_factor: float
    ) -> None:
        self.default_limit = default_limit
        self.speed_factor = speed_factor
        super().__init__(graph)

    def _get_num_limit(self, limit: str) -> float:
        """
        Args:
            limit: A string speed limit (e.g. '20 mph').
        
        Returns:
            The speed limit in km/h as a float.
        """
        parts = limit.split()
        speed = int(parts[0])
        if parts[1] == "mph":
            speed *= 1.609344
        return speed

    def _get_speed_limit(self, attrs: dict) -> float:
        """
        Args:
            attrs: An edge attributes dictionary
        
        Returns:
            The speed limit of the edge in km/h.
        """
        if "maxspeed" not in attrs:
            return self.default_limit

        limit = attrs["maxspeed"]
        # Some edges have two speed limits (where the limit changes I assume)
        # In this case average the two limits
        if isinstance(limit, list):
            num_limits = [self._get_num_limit(x) for x in limit]
            return sum(num_limits) / len(limit)
        return self._get_num_limit(limit)

    def _weight_func(self, u: int, v: int, attrs: dict) -> float:
        """
        Wrapper to match expected function signature for weight function.
        Used for NetworkX shortest path calculations only.
        """
        return self._get_edge_time(attrs)

    @override
    def _get_edge_time(self, attrs: dict, speed: float = None) -> float:
        """
        Args:
            attrs: The info dict of the edge to traverse.
            speed: Unused.
        
        Returns:
            The time taken to traverse the given edge.
        """
        speed_limit = self._get_speed_limit(attrs)
        car_speed = speed_limit * self.speed_factor
        return ((attrs["length"] / 1000) / car_speed) * 60

    @override
    def plan_paths(self, source: int, target: int) -> Iterator[list[int]]:
        """
        Args:
            source: The start node.
            target: The end node.
        
        Returns:
            an iterator of shortest paths from the source node to the target node.
        """
        digraph = ox.convert.to_digraph(self.graph)
        paths = nx.shortest_simple_paths(digraph, source, target, weight=self._weight_func)
        return paths

class ActiveNetwork(TransportNetwork):
    """Network for active travel (walking and cycling)."""

    @override
    def _get_edge_time(self, attrs: dict, speed: float = None) -> float:
        """
        Args:
            attrs: The info dict of the edge to traverse.
            speed: The speed to traverse the edge at.
        
        Returns:
            The time taken to traverse the given edge.
        """
        return ((attrs["length"] / 1000) / speed) * 60

    @override
    def plan_paths(self, source: int, target: int) -> Iterator[list[int]]:
        """
        Args:
            source: The start node.
            target: The end node.
        
        Returns:
            an iterator of shortest paths from the source node to the target node.
        """
        digraph = ox.convert.to_digraph(self.graph)
        paths = nx.shortest_simple_paths(digraph, source, target, weight="length")
        return paths

class WalkNetwork(ActiveNetwork):
    """Network for walking."""

class BikeNetwork(ActiveNetwork):
    """Network for cycling."""
