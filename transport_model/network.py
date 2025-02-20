"""Handles transport networks and operations on them"""
from typing import override
import osmnx as ox
import networkx as nx
from sklearn.neighbors import KDTree
from geopandas import GeoDataFrame
from shapely import LineString

class TransportNetwork():
    """Represents a transport network"""
    graph: nx.MultiDiGraph
    kd_tree: KDTree

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph
        node_positions = [(node[1]["x"], node[1]["y"]) for node in self.graph.nodes.data()]
        self.kd_tree = KDTree(node_positions)

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

    def plan_route(self, source: int, target: int) -> list[tuple[int, int]]:
        """Plans a route from the source node to the target node"""
        return nx.astar_path(self.graph, source, target, weight="length")

    def get_path_length(self, path: list[int]) -> float:
        """Gets the length of the provided path"""
        return nx.path_weight(self.graph, path, "length")

    def _get_final_edge(self, path: list[int], dist: float) -> tuple[int, int, float]:
        """
        Gets which edge we'll end up on after moving the provided distance,
        and how far along it we are.
        """
        cumulative_length = 0
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i + 1])[0]
            if cumulative_length + edge_data["length"] > dist:
                dist_along_edge = dist - cumulative_length
                return path[i], path[i + 1], dist_along_edge
            cumulative_length += edge_data["length"]
        return None

    def _trim_path_to_node(self, path: list[int], node: int) -> list[int]:
        """Creates a new path without any nodes before the given node"""
        index = path.index(node)
        return path[index:]

    def _create_line(self, start: int, end: int) -> LineString:
        """Creates a Shapely LineString between the provided nodes"""
        start_pos = self.get_node_coords(start)
        end_pos = self.get_node_coords(end)
        return LineString([start_pos, end_pos])

    def traverse_path(self, path: list[int], dist: float) -> tuple[list[int], float, tuple[float, float]]:
        """
        Traverses the provided path by the specified distance.
        Callers should verify that dist < path length.

        Returns:
        - Remaining path
        - Path offset
        - New location
        """
        edge_u, edge_v, offset = self._get_final_edge(path, dist)
        new_path = self._trim_path_to_node(path, edge_u)
        edge_data = self.graph.get_edge_data(edge_u, edge_v)[0]

        if "geometry" in edge_data:
            geometry = edge_data["geometry"]
        else:
            geometry = self._create_line(edge_u, edge_v)
        new_point = geometry.interpolate(offset)
        new_location = (new_point.x, new_point.y)
        return new_path, offset, new_location
        
# potentially make agents disappear when they're not moving (do this later)

# for car need to check distance for each edge individually (because of different speed limits)


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
