"""Solara visualization of the model"""
import solara
import mesa
from transport_model.model import TransportModel
from transport_model.agents import Person, Road, Area, ResidentialArea, RetailArea, IndustrialArea
from utils.custom_geospace_component import make_geospace_component
from utils.custom_solara_viz import SolaraViz

def draw(agent: mesa.Agent) -> dict:
    """Defines how a given agent should be represented"""
    portrayal = {}

    if isinstance(agent, Person):
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

def selected_agent_text(model: TransportModel) -> solara.Text:
    """Text showing which agent has been clicked on to select it"""
    if model.selected_agent is None:
        return solara.Text("No agent selected")
    return solara.Text(f"Selected agent: {model.selected_agent.name}")

def clock_text(model: TransportModel) -> solara.Text:
    """Text showing the current simulated time"""
    return solara.Text(f"Day: {model.day} {model.hour:02d}:{model.minute:02d}")

model_params = {
    "scenario": "ton_test",
    "time_step": {
        "type": "SliderInt",
        "value": 15,
        "label": "Minutes per step:",
        "min": 5,
        "max": 60,
        "step": 5,
    },
}

transport_model = TransportModel(model_params["scenario"])

page = SolaraViz(
    transport_model,
    name="Transport Model",
    model_params=model_params,
    components=[
        make_geospace_component(draw),
        selected_agent_text,
        clock_text
    ],
)
# This is required to render the visualization in the Jupyter notebook
page
