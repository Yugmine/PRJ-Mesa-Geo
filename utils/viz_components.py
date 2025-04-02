"""Components for the visualisation"""
import solara
from transport_model.model import TransportModel
from transport_model.person import PersonAgent
from transport_model.time import Time

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
        content = solara.Column(children=[
            solara.Text(f"Origin: {agent.trip.origin}"),
            solara.Text(f"Destination: {agent.trip.destination}"),
            solara.Text(f"Start time: {agent.trip.start_time}")
        ])
    return solara.Details(
        summary="Next trip:",
        children=[content]
    )

def plan_entry_text(entry: tuple[Time, str]) -> solara.Text:
    """Displays the provided entry in the plan"""
    time, action = entry
    return solara.Text(f"{time} - {action}")

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

def agent_mode_choice_view(agent: PersonAgent) -> solara.Details:
    """Displays justifications given for mode choices"""
    lines = []
    for choice in agent.memory.justifications:
        context = solara.Markdown((
            f"**Day {choice.day} {choice.time}  -  "
            f"{choice.origin} > {choice.destination} ({choice.mode})**"
        ))
        justification = solara.Text(choice.justification)
        lines.append(solara.Column(children=[context, justification]))
    all_choices = solara.Column(children=lines)
    return solara.Details(
        summary="Mode choice justifications:",
        children=[all_choices]
    )

def selected_agent_card(model: TransportModel) -> solara.Card:
    """Card showing information on the selected agent"""
    agent = model.selected_agent
    if agent is None:
        return solara.Card(title="No agent selected")

    components = solara.Column(children=[
        agent_mode_view(agent),
        agent_trip_view(agent),
        agent_plan_view(agent),
        agent_mode_choice_view(agent)
    ])

    card = solara.Card(
        title=f"Selected agent: {agent.person.name}",
        children=[components]
    )
    return card

def model_info(model: TransportModel) -> solara.Column:
    """Displays global information about the model"""
    num_agents = len(model.agents_by_type[PersonAgent])
    num_travelling = len(
        [agent for agent in model.agents_by_type[PersonAgent] if agent.is_travelling()]
    )
    agent_counts = solara.Column(children=[
        solara.Text(f"{num_agents} Agent(s) Total"),
        solara.Text(f"{num_travelling} Agent(s) Travelling")
    ])
    return solara.Card(
        title=f"Day: {model.day} {model.time}",
        children=[agent_counts]
    )

def info_panel(model: TransportModel) -> solara.Column:
    """Displays model information"""
    return solara.Column(children=[
        model_info(model),
        selected_agent_card(model)
    ])
