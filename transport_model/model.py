"""A model with people who go places"""
import xml.etree.ElementTree as ET
import os
import mesa
import mesa_geo as mg
import geopandas
from .agents import Person, Road, ResidentialArea, RetailArea, IndustrialArea

class TransportModel(mesa.Model):
    """The core model class"""
    CRS = "EPSG:4326"

    def __init__(self, scenario):
        """
        Constructor for the model

        scenario    Gives the name of the scenario (which should be located in the scenarios folder)
        """
        super().__init__()

        self.scenario_path = os.path.join("./scenarios", scenario)

        self.space = mg.GeoSpace(crs=self.CRS, warn_crs_conversion=False)

        self._load_road_network()
        self._load_people()
        self._load_areas()

        self.selected_agent = None

    def _load_road_network(self):
        """Loads road network from file in the scenario"""
        network_path = os.path.join(self.scenario_path, "network.geojson")
        gdf = geopandas.read_file(network_path)
        road_creator = mg.AgentCreator(Road, model=self)
        roads = road_creator.from_GeoDataFrame(gdf)
        self.space.add_agents(roads)

    def _load_people(self):
        """Loads person agents from file in the scenario"""
        agents_path = os.path.join(self.scenario_path, "agents.xml")
        xml_tree = ET.parse(agents_path)
        root = xml_tree.getroot()

        for agent in root.findall("agent"):
            latitude = float(agent.find("home_lat").text)
            longitude = float(agent.find("home_long").text)
            attrs = {
                "name": agent.find("name").text,
                "home": (longitude, latitude),
                "description": agent.find("description").text
            }
            new_agent = Person(self, attrs["home"], self.CRS)
            self.space.add_agents(new_agent)

    def _load_area_type(self, areas, area_class, landuse):
        """"Creates agents for the specicfied area class and landuse"""
        areas_of_type = areas.loc[areas["landuse"] == landuse]
        area_creator = mg.AgentCreator(area_class, model=self)
        agents = area_creator.from_GeoDataFrame(areas_of_type)
        self.space.add_agents(agents)

    def _load_areas(self):
        """Loads areas (residential, retail, etc...) from file in the scenario"""
        areas_path = os.path.join(self.scenario_path, "areas.geojson")
        areas = geopandas.read_file(areas_path)
        self._load_area_type(areas, ResidentialArea, "residential")
        self._load_area_type(areas, RetailArea, "retail")
        self._load_area_type(areas, IndustrialArea, "industrial")

    def step(self):
        self.agents_by_type[Person].shuffle_do("step")

# look into partially abstracting out households by having one super-agent represent each household
