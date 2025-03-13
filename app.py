"""Solara visualization of the model"""
import solara
from mesa import Agent
from mesa.visualization import make_plot_component
from transport_model.model import TransportModel
from transport_model.geo_agents import Road, Area, ResidentialArea, RetailArea, IndustrialArea
from transport_model.person import PersonAgent
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

def selected_agent_card(model: TransportModel) -> solara.Card:
    """Card showing information on the selected agent"""
    if model.selected_agent is None:
        return solara.Card(title="No agent selected")

    if model.selected_agent.current_target is None:
        components = solara.Text("Not currently travelling")
    else:
        components = solara.Column(children=[
            solara.Text(
                f"Travelling to: {model.selected_agent.current_target}"
            ),
            solara.Text(f"Mode is {model.selected_agent.current_mode}")
        ])

    card = solara.Card(
        title=f"Selected agent: {model.selected_agent.person.name}",
        children=[components]
    )
    return card

def clock_text(model: TransportModel) -> solara.Text:
    """Text showing the current simulated time"""
    return solara.Text(f"Day: {model.day} {model.hour:02d}:{model.minute:02d}")

def model_info(model: TransportModel) -> solara.Column:
    """Displays global information about the model"""
    num_agents = len(model.agents_by_type[PersonAgent])
    num_travelling = len(
        [agent for agent in model.agents_by_type[PersonAgent] if agent.current_mode is not None]
    )
    return solara.Column(children=[
        clock_text(model),
        solara.Text(f"{num_agents} Agent(s) Total"),
        solara.Text(f"{num_travelling} Agent(s) Travelling")
    ])

mode_plot = make_plot_component(["num_driving", "num_walking", "num_cycling"])

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
        model_info,
        mode_plot
    ],
)
# This is required to render the visualization in the Jupyter notebook
page
