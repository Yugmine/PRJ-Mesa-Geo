"""A model with people who go places"""
import xml.etree.ElementTree as ET
import os
import mesa
import mesa_geo as mg
import geopandas
import osmnx as ox
from geopandas.geodataframe import GeoDataFrame
from networkx import MultiDiGraph
from .agents import Person, NetworkLink, Road, Area, ResidentialArea, RetailArea, IndustrialArea
from .network import TransportNetwork, DriveNetwork, WalkNetwork, BikeNetwork

class TransportModel(mesa.Model):
    """The core model class"""
    CRS = "EPSG:4326"
    scenario_path: str
    space: mg.GeoSpace
    drive_network: DriveNetwork
    walk_network: WalkNetwork
    bike_network: BikeNetwork
    selected_agent: mg.GeoAgent

    def __init__(self, scenario: str) -> None:
        """
        Constructor for the model

        scenario    Gives the name of the scenario (which should be located in the scenarios folder)
        """
        super().__init__()

        self.scenario_path = os.path.join("./scenarios", scenario)

        self.space = mg.GeoSpace(crs=self.CRS, warn_crs_conversion=False)

        self.drive_network = DriveNetwork(self._get_network("drive"))
        self.walk_network = WalkNetwork(self._get_network("walk"))
        self.bike_network = BikeNetwork(self._get_network("bike"))

        self._create_link_agents(Road, self.drive_network)

        self._load_people()
        self._load_areas()
        self.selected_agent = None

    def _get_network(self, network_type: str) -> MultiDiGraph:
        """Loads network from file in the scenario"""
        network_path = os.path.join(self.scenario_path, f"network_{network_type}.graphml")
        return ox.io.load_graphml(network_path)

    def _create_link_agents(self, link_class: type[NetworkLink], network: TransportNetwork) -> None:
        """Creates network link agents from provided network"""
        link_creator = mg.AgentCreator(link_class, model=self)
        links = link_creator.from_GeoDataFrame(network.get_edges_as_gdf())
        self.space.add_agents(links)

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

    def step(self) -> None:
        self.agents_by_type[Person].shuffle_do("step")

# look into partially abstracting out households by having one super-agent represent each household
