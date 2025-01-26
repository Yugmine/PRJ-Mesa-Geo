"""A model with people who go places"""
import mesa
import osmnx as ox
import mesa_geo as mg
from src.agents import Person, Road, ResidentialArea, RetailArea, IndustrialArea

class TransportModel(mesa.Model):
    """The core model class"""
    LOCATION = {
        "centre": "Tonbridge Castle",
        "radius": 3000
    }
    CRS = "EPSG:4326"

    def __init__(self, num_agents=10):
        super().__init__()

        self.num_agents = num_agents

        self.space = mg.GeoSpace(crs=self.CRS, warn_crs_conversion=False)
        graph = ox.graph_from_address(
            self.LOCATION["centre"],
            dist=self.LOCATION["radius"],
            network_type="drive"
        )
        gdf = ox.convert.graph_to_gdfs(graph) # tuple w/ format (nodes, edges)
        for element in gdf:
            self.space.add_layer(element)

        road_creator = mg.AgentCreator(Road, model=self)
        roads = road_creator.from_GeoDataFrame(gdf[1])
        self.space.add_agents(roads)

        residential = self.create_areas_of_type(ResidentialArea, "residential")
        retail = self.create_areas_of_type(RetailArea, "retail")
        industrial = self.create_areas_of_type(IndustrialArea, "industrial")
        self.space.add_agents(residential + retail + industrial)

        for _ in range(num_agents):
            pos = residential[3].get_random_point()
            agent = Person(self, pos, self.CRS)
            self.space.add_agents(agent)

        self.selected_agent = None

    def create_areas_of_type(self, area_class, landuse):
        """Creates area agents for the specified type of area"""
        areas = ox.features_from_address(
            self.LOCATION["centre"],
            dist=self.LOCATION["radius"],
            tags={"landuse": landuse}
        )
        area_creator = mg.AgentCreator(area_class, model=self)
        return area_creator.from_GeoDataFrame(areas)

    def step(self):
        self.agents_by_type[Person].shuffle_do("step")

# look into partially abstracting out households by having one super-agent represent each household
