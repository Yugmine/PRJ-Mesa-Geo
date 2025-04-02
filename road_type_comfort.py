"""
Script to allow comfort values for roads to be 
generated separarately from the main model.

I would tidy this away in a folder but then python
can't import from llm properly :)))))
"""
import os
import json
from llm.llm import generate_prompt, generate_response
from transport_model.routes import RoadType

def get_system_prompts(path: str) -> dict[str, str]:
    """
    Returns a dictionary indexed by name of system prompts
    for all agents in the given scenario.
    """
    agent_file = os.path.join(path, "agents.json")
    with open(agent_file, encoding="utf-8") as f:
        agents_json = json.load(f)

    system_prompts = {}

    for info_dict in agents_json:
        name = info_dict["name"]
        inputs = [
            name,
            info_dict["home"],
            info_dict["description"],
            "n/a"
        ]
        prompt = generate_prompt(inputs, "system_prompt")
        system_prompts[name] = prompt

    return system_prompts

def get_mean_comfort(road_type: RoadType, agent_prompts: dict[str, str]) -> float:
    """Gets the mean comfort value among all agents for the given road."""
    comfort_values = []
    for name, system_prompt in agent_prompts.items():
        inputs = [
            name,
            road_type.highway,
            road_type.maxspeed,
            road_type.info
        ]
        prompt = generate_prompt(inputs, "cyclist_comfort")
        val = int(generate_response(system_prompt, prompt))
        comfort_values.append(val)
    return sum(comfort_values) / len(comfort_values)


if __name__ == "__main__":
    scenario_path = "./scenarios/westerham"
    road = RoadType(
        highway = "trunk",
        maxspeed = "40 mph",
        info = "n/a"
    )
    prompts = get_system_prompts(scenario_path)
    print(get_mean_comfort(road, prompts))
