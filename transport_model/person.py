"""Representation of individual people in the model"""
import re
import mesa
import mesa_geo as mg
from shapely import Point
from utils.llm import generate_response, generate_prompt
from .network import TransportNetwork

class Person():
    """
    Stores information about one person.

    name                This person's name.
    home                Name of this person's home.
    description         Natural language description of this person.
    walk_speed          Average speed this person can walk at (km/h).
    bike_speed          Average speed this person can cycle at (km/h).
    daily_plan          This person's plan for today. List of actions in the format (hour, minute, action).
    """
    name: str
    home: str
    description: str
    walk_speed: float
    bike_speed: float
    daily_plan: list[tuple[tuple[int, int], str]]

    def __init__(
        self,
        info_dict: dict
    ) -> None:
        self.name = info_dict["name"]
        self.home = info_dict["home"]
        self.description = info_dict["description"]
        self.walk_speed = 5 # TODO: vary depending on agent definition
        self.bike_speed = 15 # TODO: vary depending on agent definition

    def _break_down_plan(self, plan: str) -> None:
        """
        Breaks down the provided plan into a list and stores it
        
        Expected plan format:
        08:00 do something
        09:00 do something else
        ...
        """
        lines = plan.split("\n")
        lines = [line.strip() for line in lines]
        # Matches strings that start with a time in the format 9:00 or 09:00
        pattern = r"^([01]?[0-9]|2[0-3]):([0-5][0-9])\b\s+.*"
        lines = [line for line in lines if re.match(pattern, line)]

        cleaned_plan = []
        for line in lines:
            time = line.split()[0]
            hour = int(time.split(":")[0])
            minute = int(time.split(":")[1])
            action = line.removeprefix(time).strip()
            cleaned_plan.append(((hour, minute), action))

        self.daily_plan = cleaned_plan

    def generate_system_prompt(self) -> str:
        """Generates the system prompt for this person"""
        inputs = [
            self.name,
            self.home,
            self.description
        ]
        return generate_prompt(inputs, "system_prompt")

    def plan_day(self) -> None:
        """Generates a plan for this agent's day using the LLM"""
        system_prompt = self.generate_system_prompt()
        prompt = generate_prompt([self.name], "daily_planning")
        response = generate_response(system_prompt, prompt)
        print(response)
        self._break_down_plan(response)

    def get_next_action(self) -> tuple[tuple[int, int], str]:
        """Returns the next action in this person's plan"""
        if not self.daily_plan:
            return None

        return self.daily_plan.pop(0)

class PersonAgent(mg.GeoAgent):
    """
    Represents one person in the model space.

    person              The person this agent is representing.
    current_path        List of nodes that the person is travelling between (empty if not moving).
    path_offset         When this person is following a path and is in the middle of an edge,
                        gives how far through traversing it they are (in minutes).
    current_mode        Current transport mode the person is using (None if not moving).
    current_target      Name of the location the person is travelling to, or is at.
    next_move_time      The time that this agent will next move (None if not planning to move).
    """
    person: Person
    current_path: list[int]
    path_offset: float
    current_mode: str
    current_target: str
    next_move_time: tuple[int, int]

    def __init__(
        self,
        model: mesa.Model,
        crs: str,
        person: Person
    ) -> None:
        self.person = person
        self.current_target = person.home
        geometry = Point(model.get_location_coords(person.home))
        super().__init__(model, geometry, crs)
        self._clear_path()

    def __repr__(self) -> str:
        return f"Agent {self.person.name}"

    def _clear_path(self) -> None:
        """Clears the currently stored path"""
        self.current_path = []
        self.path_offset = 0
        self.current_mode = None
        self.next_move_time = None

    def _set_location(self, location: tuple[float, float]) -> None:
        """Sets this agent's current location"""
        self.geometry = Point(location)

    def _plan_trip(self, location: str, network: TransportNetwork) -> None:
        """
        Plans a trip to the location with the provided name
        Currently it just plans the quickest route
        """
        # TODO: include the LLM in this process
        source = network.get_nearest_node((self.geometry.x, self.geometry.y))
        target_coords = self.model.get_location_coords(location)
        target = network.get_nearest_node(target_coords)
        if source != target:
            source_coords = network.get_node_coords(source)
            self._set_location(source_coords)
            self.current_path = network.plan_route(source, target)
            self.current_target = location

    def _plan_driving_trip(self, location: str) -> None:
        """Plans a driving trip"""
        self._plan_trip(location, self.model.drive_network)
        self.current_mode = "drive"

    def _plan_walking_trip(self, location: str) -> None:
        """Plans a walking trip"""
        self._plan_trip(location, self.model.walk_network)
        self.current_mode = "walk"

    def _plan_cycling_trip(self, location: str) -> None:
        """Plans a cycling trip"""
        self._plan_trip(location, self.model.bike_network)
        self.current_mode = "bike"

    def _follow_path(self, network: TransportNetwork, speed: float = None) -> None:
        """Move along the planned path on the given network"""
        path_time = network.get_path_length(self.current_path, speed)
        time = self.model.time_step
        if time > path_time - self.path_offset:
            # We have reached our destination
            new_location = self.model.get_location_coords(self.current_target)
            self._clear_path()
            self._next_plan_step()
        else:
            # Still Travelling
            self.current_path, self.path_offset, new_location = network.traverse_path(
                path = self.current_path,
                time = time + self.path_offset,
                speed = speed
            )
        self._set_location(new_location)

    def _move(self) -> None:
        """Move along the planned path"""
        if self.current_mode == "drive":
            self._follow_path(self.model.drive_network)
        elif self.current_mode == "walk":
            self._follow_path(self.model.walk_network, self.person.walk_speed)
        elif self.current_mode == "bike":
            self._follow_path(self.model.bike_network, self.person.bike_speed)

    def _generate_location_prompt(self, action: str) -> str:
        """Fills the prompt template for getting the location for an action"""
        inputs = [
            self.person.name,
            self.current_target,
            self.model.get_location_names(),
            action
        ]
        return generate_prompt(inputs, "action_location")

    def _get_action_location(self, action: str) -> str:
        """Gets the location to perform the given action"""
        prompt = self._generate_location_prompt(action)
        system_prompt = self.person.generate_system_prompt()

        for _ in range (3):
            action_location = generate_response(system_prompt, prompt)
            if self.model.is_location(action_location):
                return action_location

        # Timeout - failed to generate valid location within 3 attempts
        print(f"WARNING: agent {self.person.name} couldn't get valid location for action: {action}")
        # Don't move
        return self.current_target

    def _next_plan_step(self) -> None:
        """Gets the next step in this person's plan and loads it ready to be followed"""
        time, action = self.person.get_next_action()
        if action is None:
            return

        self.next_move_time = time
        self.current_target = self._get_action_location(action)

    def step(self) -> None:
        if self.current_path:
            self._move()
        elif self.model.get_time() == self.next_move_time:
            # move to the planned location
            pass
        elif self.model.get_time() == (5, 0):
            # Plan for the day
            self.person.plan_day()
            self._next_plan_step()
