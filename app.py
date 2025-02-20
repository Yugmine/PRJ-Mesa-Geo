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

def selected_agent_card(model: TransportModel) -> solara.Card:
    """Card showing information on the selected agent"""
    if model.selected_agent is None:
        return solara.Card(title="No agent selected")

    if model.selected_agent.current_target is None:
        components = solara.Text("Not currently travelling")
    else:
        components = solara.Column(children=[
            solara.Text(
                f"Travelling to: {model.locations[model.selected_agent.current_target]['name']}"
            ),
            solara.Text(f"Mode is {model.selected_agent.current_mode}")
        ])

    card = solara.Card(
        title=f"Selected agent: {model.selected_agent.name}",
        children=[components]
    )
    return card

def clock_text(model: TransportModel) -> solara.Text:
    """Text showing the current simulated time"""
    return solara.Text(f"Day: {model.day} {model.hour:02d}:{model.minute:02d}")

model_params = {
    "scenario": "ton_test",
    "time_step": {
        "type": "SliderInt",
        "value": 5,
        "label": "Minutes per step:",
        "min": 1,
        "max": 15,
        "step": 1,
    },
}

transport_model = TransportModel(model_params["scenario"])

page = SolaraViz(
    transport_model,
    name="Transport Model",
    model_params=model_params,
    components=[
        make_geospace_component(draw),
        selected_agent_card,
        clock_text
    ],
)
# This is required to render the visualization in the Jupyter notebook
page
