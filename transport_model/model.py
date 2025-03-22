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
from utils.model_time import Time
from .geo_agents import NetworkLink, Road, Area, ResidentialArea, RetailArea, IndustrialArea
from .person import Person, PersonAgent
from .network import TransportNetwork, DriveNetwork, WalkNetwork, BikeNetwork

def get_num_agents_by_mode(model: mesa.Model, mode: str) -> int:
    """Returns the number of agents currently travelling by the given mode"""
    agents = [
        agent for agent in model.agents_by_type[PersonAgent]
        if agent.get_current_mode() == mode
    ]
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
    global_info: str
    selected_agent: PersonAgent
    day: int
    time: Time
    time_step: int
    default_speed_limit: int
    car_speed_factor: float
    datacollector: mesa.DataCollector

    def __init__(
        self,
        scenario: str,
        time_step: int = 5,
        default_speed_limit: int = 30,
        car_speed_factor: float = 0.75
    ) -> None:
        """
        Constructor for the model

        scenario                Gives the name of the scenario
                                (which should be located in the scenarios folder).
        time_step               The number of minutes that should pass in every model step.
        default_speed_limit     The speed limit (in km/h) applied to roads
                                with no defined speed limit.
        car_speed_factor        Multiplied by speed limit to get the speed a car will travel at.
        """
        super().__init__()

        self.scenario_path = os.path.join("./scenarios", scenario)
        self.day = 1
        self.time = Time(4, 0)
        self.time_step = time_step
        self.default_speed_limit = default_speed_limit
        self.car_speed_factor = car_speed_factor

        self.space = mg.GeoSpace(crs=self.CRS, warn_crs_conversion=False)

        self.drive_network = DriveNetwork(
            self._get_network("drive"),
            default_speed_limit,
            car_speed_factor
        )
        self.walk_network = WalkNetwork(self._get_network("walk"))
        self.bike_network = BikeNetwork(self._get_network("bike"))

        self._create_link_agents(Road, self.drive_network)

        self._load_locations()
        self._load_people()
        self._load_areas()
        self._load_info()
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

        for info_dict in agents_json:
            new_person = Person(info_dict)
            new_agent = PersonAgent(
                model = self,
                crs = self.CRS,
                person = new_person
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

    def _load_info(self) -> None:
        """Loads global info (e.g. vehicle mileage tax) for the simulation"""
        info_path = os.path.join(self.scenario_path, "global_info.txt")
        with open (info_path, "r", encoding="utf-8") as file:
            self.global_info = file.read()

    def _update_clock(self):
        """Updates the simulation clock by the specified time step"""
        new_day = self.time.perform_time_step(self.time_step)
        if new_day:
            self.day += 1

    def get_location_coords(self, loc_name: str) -> tuple[float, float]:
        """Returns the coordinates of the specified location"""
        long = self.locations[loc_name]["long"]
        lat = self.locations[loc_name]["lat"]
        return long, lat

    def get_location_names(self) -> list[str]:
        """Returns a list of the name of every location"""
        return list(self.locations.keys())

    def is_location(self, location: str) -> bool:
        """Checks if the provided location is in the environment"""
        return location in self.locations.keys()

    def get_network(self, mode: str) -> TransportNetwork:
        """Returns the network for the specified mode"""
        if mode == "drive":
            return self.drive_network
        if mode == "walk":
            return self.walk_network
        if mode == "bike":
            return self.bike_network
        return None

    def step(self) -> None:
        self.agents_by_type[PersonAgent].shuffle_do("step")
        self.datacollector.collect(self)
        self._update_clock()
