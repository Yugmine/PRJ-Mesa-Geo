"""Solara visualization of the model"""
from mesa import Agent
from mesa.visualization import make_plot_component
from transport_model.model import TransportModel
from transport_model.geo_agents import Road, Area, ResidentialArea, RetailArea, IndustrialArea
from transport_model.person import PersonAgent
from utils.viz_components import info_panel
from utils.custom_geospace_component import make_geospace_component
from utils.custom_solara_viz import SolaraViz

def draw(agent: Agent) -> dict:
    """Defines how a given agent should be represented"""
    portrayal = {}

    if isinstance(agent, PersonAgent):
        if agent.model.selected_agent == agent:
            portrayal["color"] = "brown"
        else:
            portrayal["color"] = "red"
    elif isinstance(agent, Road):
        portrayal["color"] = "grey"
    elif isinstance(agent, Area):
        portrayal["stroke"] = False
        if isinstance(agent, ResidentialArea):
            portrayal["color"] = "green"
        elif isinstance(agent, RetailArea):
            portrayal["color"] = "blue"
        elif isinstance(agent, IndustrialArea):
            portrayal["color"] = "yellow"

    return portrayal

mode_plot = make_plot_component(["num_driving", "num_walking", "num_cycling"])

model_params = {
    "scenario": "westerham",
    "time_step": {
        "type": "SliderInt",
        "value": 5,
        "label": "Minutes per step:",
        "min": 1,
        "max": 15,
        "step": 1,
    },
    "default_speed_limit": 30,
    "car_speed_factor": 0.75,
}

transport_model = TransportModel(model_params["scenario"])

page = SolaraViz(
    transport_model,
    name="Transport Model",
    model_params=model_params,
    components=[
        make_geospace_component(draw),
        info_panel,
        mode_plot,
    ],
)
# This is required to render the visualization in the Jupyter notebook
page
