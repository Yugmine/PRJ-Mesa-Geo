"""Representation of individual people in the model"""
import re
import mesa
import mesa_geo as mg
from shapely import Point
from utils.llm import generate_response, generate_prompt
from utils.model_time import Time
from .routes import Trip, Route, TripMemory

class Person:
    """
    Stores information about one person.

    name                This person's name.
    home                Name of this person's home.
    description         Natural language description of this person.
    walk_speed          Average speed this person can walk at (km/h).
    bike_speed          Average speed this person can cycle at (km/h).
    owns_car            Whether this person owns a car.
    owns_bike           Whether this person owns a bicycle.
    daily_plan          This person's plan for today. 
                        List of actions in the format (time, action).
    trip_memory         Stores memories of trip times.
    """
    name: str
    home: str
    description: str
    walk_speed: float
    bike_speed: float
    owns_car: bool
    owns_bike: bool
    daily_plan: list[tuple[Time, str]]
    trip_memory: TripMemory

    def __init__(
        self,
        info_dict: dict
    ) -> None:
        self.name = info_dict["name"]
        self.home = info_dict["home"]
        self.description = info_dict["description"]
        self.walk_speed = info_dict["walk_speed"]
        self.bike_speed = info_dict["bike_speed"]
        self.owns_car = info_dict["owns_car"]
        self.owns_bike = info_dict["owns_bike"]
        self.daily_plan = []
        self.trip_memory = TripMemory()

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
            cleaned_plan.append((Time(hour, minute), action))

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
        self._break_down_plan(response)

    def get_next_action(self) -> tuple[Time, str]:
        """Returns the next action in this person's plan"""
        if not self.daily_plan:
            return None

        return self.daily_plan.pop(0)

class PersonAgent(mg.GeoAgent):
    """
    Represents one person in the model space.

    person          The person this agent is representing.
    trip            This person's next planned trip.
    route           This person's current route (None if not travelling).
    location        This person's current location (None if travelling).
    """
    person: Person
    trip: Trip
    route: Route
    location: str

    def __init__(
        self,
        model: mesa.Model,
        crs: str,
        person: Person
    ) -> None:
        self.person = person
        self.location = person.home
        self.trip = None
        self.route = None
        geometry = Point(model.get_location_coords(person.home))
        super().__init__(model, geometry, crs)

    def __repr__(self) -> str:
        return f"Agent {self.person.name}"

    def _set_position(self, position: tuple[float, float]) -> None:
        """Sets this agent's current position"""
        self.geometry = Point(position)

    def _plan_route(self, mode: str) -> None:
        """
        Plans a route for the planned trip with the given mode
        Currently it just plans the quickest route
        """
        network = self.model.get_network(mode)
        origin_coords = self.model.get_location_coords(self.trip.origin)
        origin = network.get_nearest_node(origin_coords)
        destination_coords = self.model.get_location_coords(self.trip.destination)
        destination = network.get_nearest_node(destination_coords)
        if origin != destination:
            # Move the agent to the start node
            start_coords = network.get_node_coords(origin)
            self._set_position(start_coords)
            # TODO: include the LLM in this process
            path = network.plan_route(origin, destination)
            self.route = Route(mode, path)

    def _get_speed(self, mode: str) -> float:
        """
        Gets speed for the given mode
        (speed not required for driving because it depends on speed limits)
        """
        if mode == "walk":
            return self.person.walk_speed
        if mode == "bike":
            return self.person.bike_speed
        return None

    def _add_to_memory(self, mins_left: float) -> None:
        """Adds the trip that just finished to memory"""
        end_time = self.model.time.n_mins_from_now(mins_left)
        self.person.trip_memory.add_trip(self.trip, self.route.mode, end_time)

    def _follow_route(self) -> None:
        """Move along the planned route"""
        network = self.model.get_network(self.route.mode)
        speed = self._get_speed(self.route.mode)

        new_position, mins_left = network.traverse_route(
            route = self.route,
            time_step = self.model.time_step,
            speed = speed
        )

        if new_position is None:
            # We have reached our destination
            new_position = self.model.get_location_coords(self.trip.destination)
            self.location = self.trip.destination
            self._add_to_memory(mins_left)
            self.trip = None
            self.route = None
            self._next_plan_step()

        self._set_position(new_position)

    def _generate_location_prompt(self, action: str) -> str:
        """Fills the prompt template for getting the location for an action"""
        inputs = [
            self.person.name,
            self.location,
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
        return self.location

    def _next_plan_step(self) -> None:
        """Gets the next step in this person's plan and loads it ready to be followed"""
        entry = self.person.get_next_action()
        if entry is None:
            return
        time, action = entry
        destination = self._get_action_location(action)

        if destination == self.location:
            # don't need to move - load the next step
            self._next_plan_step()
        else:
            self.trip = Trip(
                origin = self.location,
                destination = destination,
                start_time = time
            )

    def is_travelling(self) -> bool:
        """Checks if this agent is travelling (true) or stationary (false)"""
        return self.route is not None

    def get_current_mode(self) -> str:
        """
        Returns the current mode this agent is travelling with.
        Returns None if this agent is not travelling.
        """
        if not self.is_travelling():
            return None
        return self.route.mode

    def step(self) -> None:
        if self.is_travelling():
            self._follow_route()
        elif self.trip is not None:
            if self.model.time == self.trip.start_time:
                # move to the planned location
                self._plan_route("walk")
        elif self.model.time == Time(4, 0):
            # Plan for the day
            self.person.plan_day()
            self._next_plan_step()
