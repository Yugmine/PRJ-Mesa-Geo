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

def agent_mode_view(agent: PersonAgent) -> solara.Text:
    """Displays information about the provided agent's travel mode"""
    if not agent.is_travelling():
        return solara.Text("Not currently travelling")
    return solara.Text(f"Travelling with mode: {agent.get_current_mode()}")

def agent_trip_view(agent: PersonAgent) -> solara.Details:
    """Displays information about the provided agent's planned trip"""
    if agent.trip is None:
        content = solara.Text("No trip planned")
    else:
        hours = agent.trip.start_time[0]
        minutes = agent.trip.start_time[1]
        content = solara.Column(children=[
            solara.Text(f"Origin: {agent.trip.origin}"),
            solara.Text(f"Destination: {agent.trip.destination}"),
            solara.Text(f"Start time: {hours:02d}:{minutes:02d}")
        ])
    return solara.Details(
        summary="Next trip:",
        children=[content]
    )

def plan_entry_text(entry: tuple[tuple[int, int], str]) -> solara.Text:
    """Displays the provided entry in the plan"""
    ((hours, minutes), action) = entry
    return solara.Text(f"{hours:02d}:{minutes:02d} - {action}")

def agent_plan_view(agent: PersonAgent) -> solara.Details:
    """Displays information about the provided agent's daily plan"""
    if not agent.person.daily_plan:
        content = solara.Text("Plan is empty")
    else:
        content = solara.Column(children=[
            plan_entry_text(entry) for entry in agent.person.daily_plan
        ])
    return solara.Details(
        summary="Remaining daily plan:",
        children=[content]
    )

def selected_agent_card(model: TransportModel) -> solara.Card:
    """Card showing information on the selected agent"""
    agent = model.selected_agent
    if agent is None:
        return solara.Card(title="No agent selected")

    components = solara.Column(children=[
        agent_mode_view(agent),
        agent_trip_view(agent),
        agent_plan_view(agent)
    ])

    card = solara.Card(
        title=f"Selected agent: {agent.person.name}",
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
        [agent for agent in model.agents_by_type[PersonAgent] if agent.is_travelling()]
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
        mode_plot,
        model_info
    ],
)
# This is required to render the visualization in the Jupyter notebook
page
