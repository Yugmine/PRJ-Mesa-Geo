"""Solara visualization of the model"""
from mesa import Agent
from mesa.visualization import make_plot_component
from transport_model.model import TransportModel
from transport_model.geo_agents import NetworkLink, Area, ResidentialArea, RetailArea, IndustrialArea
from transport_model.person import PersonAgent
from utils.viz_components import info_panel
from modified_lib_files.custom_geospace_component import make_geospace_component
from modified_lib_files.custom_solara_viz import SolaraViz

def draw(agent: Agent) -> dict:
    """Defines how a given agent should be represented"""
    portrayal = {}

    if isinstance(agent, PersonAgent):
        if agent.model.selected_agent == agent:
            portrayal["color"] = "brown"
        else:
            portrayal["color"] = "red"
    elif isinstance(agent, NetworkLink):
        if hasattr(agent, "extra_info") and isinstance(agent.extra_info, str):
            portrayal["color"] = "yellow"
        else:
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
    "n_days": {
        "type": "SliderInt",
        "value": 10,
        "label": "Simulation length (days):",
        "min": 1,
        "max": 20,
        "step": 1,
    },
    "driving_extra_time": 5,
    "cycling_extra_time": 5
}

transport_model = TransportModel(
    model_params["scenario"],
    model_params["time_step"]["value"],
    model_params["default_speed_limit"],
    model_params["car_speed_factor"],
    model_params["n_days"]["value"],
    model_params["driving_extra_time"],
    model_params["cycling_extra_time"]
)

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
