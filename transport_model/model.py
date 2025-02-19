"""A model with people who go places"""
import xml.etree.ElementTree as ET
import os
import mesa
import mesa_geo as mg
import geopandas
import osmnx as ox
from geopandas.geodataframe import GeoDataFrame
from networkx import MultiDiGraph
from sklearn.neighbors import KDTree
from shapely import Point
from .agents import Person, Road, Area, ResidentialArea, RetailArea, IndustrialArea

class TransportModel(mesa.Model):
    """The core model class"""
    CRS = "EPSG:4326"
    scenario_path: str
    space: mg.GeoSpace
    network: MultiDiGraph
    kd_tree: KDTree
    selected_agent: mg.GeoAgent

    def __init__(self, scenario: str) -> None:
        """
        Constructor for the model

        scenario    Gives the name of the scenario (which should be located in the scenarios folder)
        """
        super().__init__()

        self.scenario_path = os.path.join("./scenarios", scenario)

        self.space = mg.GeoSpace(crs=self.CRS, warn_crs_conversion=False)

        self._load_road_network()
        self._create_road_agents()
        self._load_people()
        self._load_areas()
        node_positions = [(node[1]["x"], node[1]["y"]) for node in self.network.nodes.data()]
        self.kd_tree = KDTree(node_positions)
        self.selected_agent = None

    def _load_road_network(self) -> None:
        """Loads road network from file in the scenario"""
        network_path = os.path.join(self.scenario_path, "network.graphml")
        self.network = ox.io.load_graphml(network_path)

    def _create_road_agents(self) -> None:
        """Creates road agents from saved road network"""
        gdfs = ox.convert.graph_to_gdfs(self.network) # tuple w/ format (nodes, edges)
        road_creator = mg.AgentCreator(Road, model=self)
        roads = road_creator.from_GeoDataFrame(gdfs[1])
        self.space.add_agents(roads)

    def _load_people(self) -> None:
        """Loads person agents from file in the scenario"""
        agents_path = os.path.join(self.scenario_path, "agents.xml")
        xml_tree = ET.parse(agents_path)
        root = xml_tree.getroot()

        for agent in root.findall("agent"):
            latitude = float(agent.find("home_lat").text)
            longitude = float(agent.find("home_long").text)
            new_agent = Person(
                model = self,
                crs = self.CRS,
                name = agent.find("name").text,
                home = (longitude, latitude),
                description = agent.find("description").text
            )
            self.space.add_agents(new_agent)

    def _load_area_type(self, areas: GeoDataFrame, area_class: type[Area], landuse: str) -> None:
        """"Creates agents for the specicfied area class and landuse"""
        areas_of_type = areas.loc[areas["landuse"] == landuse]
        area_creator = mg.AgentCreator(area_class, model=self)
        agents = area_creator.from_GeoDataFrame(areas_of_type)
        self.space.add_agents(agents)

    def _load_areas(self) -> None:
        """Loads areas (residential, retail, etc...) from file in the scenario"""
        areas_path = os.path.join(self.scenario_path, "areas.geojson")
        areas = geopandas.read_file(areas_path)
        self._load_area_type(areas, ResidentialArea, "residential")
        self._load_area_type(areas, RetailArea, "retail")
        self._load_area_type(areas, IndustrialArea, "industrial")

    def get_nearest_node(self, pos: Point) -> int:
        """
        Gets the id of the nearest node in the road network to the provided point
        Code taken from agents_and_networks mesa_geo example
        """
        node_index = self.kd_tree.query([(pos.x, pos.y)], k=1, return_distance=False)
        node_id = list(self.network.nodes)[node_index[0,0]]
        return node_id

    def step(self) -> None:
        self.agents_by_type[Person].shuffle_do("step")

# look into partially abstracting out households by having one super-agent represent each household
