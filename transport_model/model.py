"""A model with people who go places"""
import json
import os
from functools import partial
import mesa
import mesa_geo as mg
import geopandas
import osmnx as ox
from geopandas.geodataframe import GeoDataFrame
from networkx import MultiDiGraph
from .geo_agents import NetworkLink, Road, Area, ResidentialArea, RetailArea, IndustrialArea
from .person_agent import Person
from .network import TransportNetwork, DriveNetwork, WalkNetwork, BikeNetwork

def get_num_agents_by_mode(model: mesa.Model, mode: str) -> int:
    """Returns the number of agents currently travelling by the given mode"""
    agents = [agent for agent in model.agents_by_type[Person] if agent.current_mode == mode]
    return len(agents)

class TransportModel(mesa.Model):
    """The core model class"""
    CRS = "EPSG:4326"
    scenario_path: str
    space: mg.GeoSpace
    locations: dict
    drive_network: DriveNetwork
    walk_network: WalkNetwork
    bike_network: BikeNetwork
    selected_agent: Person
    day: int
    hour: int
    minute: int
    time_step: int
    datacollector: mesa.DataCollector

    def __init__(self, scenario: str, time_step: int = 5) -> None:
        """
        Constructor for the model

        scenario    Gives the name of the scenario (which should be located in the scenarios folder)
        time_step   The number of minutes that should pass in every model step
        """
        super().__init__()

        self.scenario_path = os.path.join("./scenarios", scenario)
        self.day = 0
        self.hour = 0
        self.minute = 0
        self.time_step = time_step

        self.space = mg.GeoSpace(crs=self.CRS, warn_crs_conversion=False)

        self.drive_network = DriveNetwork(self._get_network("drive"))
        self.walk_network = WalkNetwork(self._get_network("walk"))
        self.bike_network = BikeNetwork(self._get_network("bike"))

        self._create_link_agents(Road, self.drive_network)

        self._load_locations()
        self._load_people()
        self._load_areas()
        self.selected_agent = None

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "num_driving": partial(get_num_agents_by_mode, mode="drive"),
                "num_walking": partial(get_num_agents_by_mode, mode="walk"),
                "num_cycling": partial(get_num_agents_by_mode, mode="bike"),
            }
        )

    def _get_network(self, network_type: str) -> MultiDiGraph:
        """Loads network from file in the scenario"""
        network_path = os.path.join(self.scenario_path, f"network_{network_type}.graphml")
        return ox.io.load_graphml(network_path)

    def _create_link_agents(self, link_class: type[NetworkLink], network: TransportNetwork) -> None:
        """Creates network link agents from provided network"""
        link_creator = mg.AgentCreator(link_class, model=self)
        links = link_creator.from_GeoDataFrame(network.get_edges_as_gdf())
        self.space.add_agents(links)

    def _load_locations(self) -> None:
        """Loads locations from file in the scenario"""
        locations_path = os.path.join(self.scenario_path, "locations.json")
        with open(locations_path, encoding="utf-8") as f:
            self.locations = json.load(f)

    def _load_people(self) -> None:
        """Loads person agents from file in the scenario"""
        agents_path = os.path.join(self.scenario_path, "agents.json")
        with open(agents_path, encoding="utf-8") as f:
            agents_json = json.load(f)

        for agent in agents_json:
            new_agent = Person(
                model = self,
                crs = self.CRS,
                name = agent["name"],
                home = agent["home"],
                description = agent["description"]
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

    def _update_clock(self):
        """Updates the simulation clock by the specified time step"""
        self.minute += self.time_step
        if self.minute == 60:
            if self.hour == 23:
                self.hour = 0
                self.day += 1
            else:
                self.hour += 1
            self.minute = 0

    def get_location_coords(self, loc_id: int) -> tuple[float, float]:
        """Returns the coordinates of the specified location"""
        long = self.locations[loc_id]["long"]
        lat = self.locations[loc_id]["lat"]
        return long, lat

    def step(self) -> None:
        self.datacollector.collect(self)
        self._update_clock()
        self.agents_by_type[Person].shuffle_do("step")

# look into partially abstracting out households by having one super-agent represent each household
