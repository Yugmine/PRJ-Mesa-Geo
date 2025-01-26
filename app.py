"""Solara visualization of the model"""
import solara
from src.model import TransportModel
from src.agents import Person, Road, Area, ResidentialArea, RetailArea, IndustrialArea
from custom_geospace_component import make_geospace_component
from custom_solara_viz import SolaraViz

def draw(agent):
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

def selected_agent_text(model):
    """Text showing which agent has been clicked on to select it"""
    if model.selected_agent is None:
        return solara.Text("No agent selected")
    else:
        return solara.Text(f"Selected agent: {model.selected_agent.unique_id}")

model_params = {
    "num_agents": {
        "type": "SliderInt",
        "value": 10,
        "label": "Number of agents:",
        "min": 1,
        "max": 100,
        "step": 1,
    },
}

transport_model = TransportModel()

page = SolaraViz(
    transport_model,
    name="Transport Model",
    model_params=model_params,
    components=[
        make_geospace_component(draw),
        selected_agent_text
    ],
)
# This is required to render the visualization in the Jupyter notebook
page
