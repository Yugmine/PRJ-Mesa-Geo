"""Representation of individual people in the model"""
import re
import mesa
import mesa_geo as mg
from shapely import Point
from utils.llm import generate_response, generate_prompt
from utils.model_time import Time
from .routes import Trip, Route, RoadType
from .memory import TravelMemory, MemoryEntry, ModeChoice

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
    memory              Stores memories of previous journeys.
    """
    name: str
    home: str
    description: str
    walk_speed: float
    bike_speed: float
    owns_car: bool
    owns_bike: bool
    daily_plan: list[tuple[Time, str]]
    memory: TravelMemory

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
        self.memory = TravelMemory()

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

    person              The person this agent is representing.
    trip                This person's next planned trip.
    route               This person's current route (None if not travelling).
    location            This person's current location (None if travelling).
    memory_entry        The current memory being built.
                        (This memory remembers information about the current trip).
    """
    person: Person
    trip: Trip
    route: Route
    location: str
    memory_entry: MemoryEntry

    def __init__(
        self,
        model: mesa.Model,
        crs: str,
        person: Person
    ) -> None:
        self.person = person
        self.location = person.home
        self._clear_travel_info()
        geometry = Point(model.get_location_coords(person.home))
        super().__init__(model, geometry, crs)

    def __repr__(self) -> str:
        return f"Agent {self.person.name}"

    def _set_position(self, position: tuple[float, float]) -> None:
        """Sets this agent's current position"""
        self.geometry = Point(position)

    def _clear_travel_info(self) -> None:
        """Clears information stored when travelling"""
        self.trip = None
        self.route = None
        self.memory_entry = None

    def _mode_possible_routes(self, origin: str, destination: str, mode: str) -> list[Route]:
        """Gets some possible routes between the given locations with the given mode"""
        network = self.model.get_network(mode)
        origin_coords = self.model.get_location_coords(origin)
        origin_node = network.get_nearest_node(origin_coords)
        destination_coords = self.model.get_location_coords(destination)
        destination_node = network.get_nearest_node(destination_coords)
        paths = network.plan_paths(origin_node, destination_node)
        return [Route(mode, path) for path in paths]

    def _get_candidate_routes(self, origin: str, destination: str):
        """Get a list of reasonable routes between the origin and destination"""
        routes = self._mode_possible_routes(origin, destination, "walk")
        if self.person.owns_bike:
            routes += self._mode_possible_routes(origin, destination, "bike")
        if self.person.owns_car:
            routes += self._mode_possible_routes(origin, destination, "drive")
        return routes

    def _get_route_description(self, route: Route) -> str:
        """
        Gets a string description of the given route.
        Includes information from any stored memories.
        """
        route_memory = self.person.memory.get_route_entry(route.mode, route.path)

        if route_memory is None:
            network = self.model.get_network(route.mode)
            est_travel_time = network.get_path_duration(route.path, self._get_speed(route.mode))
            return (
                f"mode: {route.mode}, "
                f"not previously used, "
                f"estimated travel time (minutes): {est_travel_time:.2f}"
            )

        description = (
            f"mode: {route.mode}, "
            f"previously used {route_memory.count} time(s), "
            f"average travel time (minutes): {route_memory.travel_time:.2f}"
        )
        if route.mode in ("bike", "walk"):
            description += (
                f", on a scale of 1 (not at all comfortable) to 10 (very comfortable) "
                f"they previously rated this route {route_memory.comfort:.1f}"
            )
        return description

    def _create_route_info(self, routes: list[Route]) -> str:
        """Creates a string description for all of the given routes"""
        route_descriptions = ""
        for i, route in enumerate(routes):
            line = self._get_route_description(route)
            route_descriptions += f"{i} - {line} \n"
        return route_descriptions

    def _clean_route_choice_response(self, response: str) -> tuple[int, str]:
        """Extracts the chosen route and justification from the raw LLM response"""
        split_response = response.split("\n")
        route_id = int(split_response[0])
        justification = split_response[-1]
        return route_id, justification

    def _choose_a_route(self, origin: str, destination: str) -> Route:
        """Gets the LLM to pick a route to travel between the given origin + destination"""
        routes = self._get_candidate_routes(origin, destination)
        route_info = self._create_route_info(routes)
        system_prompt = self.person.generate_system_prompt()
        inputs = [
            self.person.name,
            origin,
            destination,
            route_info
        ]
        prompt = generate_prompt(inputs, "route_choice")
        response = generate_response(system_prompt, prompt)
        route_id, justification = self._clean_route_choice_response(response)
        route_chosen = routes[route_id]
        choice = ModeChoice(
            day = self.model.day,
            time = self.model.time.copy(),
            origin = origin,
            destination = destination,
            mode = route_chosen.mode,
            justification = justification
        )
        self.person.memory.store_mode_choice(choice)
        return route_chosen

    def _plan_route(self) -> None:
        """Plan a route for the planned trip."""
        self.route = self._choose_a_route(self.trip.origin, self.trip.destination)

        # Move the agent to the start node
        network = self.model.get_network(self.route.mode)
        start_coords = network.get_node_coords(self.route.path[0])
        self._set_position(start_coords)

        # Give negative offset if we start moving in the middle of a time step
        time_to_start = self.model.time.time_to(self.trip.start_time)
        self.route.set_offset(self.model.time_step - time_to_start)

        self.memory_entry = self.person.memory.init_route_entry(self.route.mode, self.route.path)

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

    def _calculate_trip_time(self, mins_left: float) -> float:
        """
        Calculates how long the trip that just finished took.

        Args:
            mins_left       How many minutes are left in the current time step
                            (after the trip finished).
        """
        end_time = self.model.time.n_mins_from_now(self.model.time_step - mins_left)
        return self.trip.start_time.time_to(end_time)

    def _handle_list_attrs(self, attr: str | list) -> str:
        """
        Sometimes OSM attributes are lists instead of strings.
        Return the first entry if this is the case.
        """
        if isinstance(attr, list):
            return attr[0]
        return attr

    def _get_road_type(self, attrs: dict) -> RoadType:
        """Creates a RoadType object from the provided attributes dict"""
        highway = self._handle_list_attrs(attrs["highway"])
        if "maxspeed" not in attrs:
            maxspeed = "n/a"
        else:
            maxspeed = self._handle_list_attrs(attrs["maxspeed"])
        return RoadType(highway, maxspeed)

    def _get_comfort(self, road: RoadType, mode: str) -> int:
        """Gets a comfort value for the provided road type and mode"""
        system_prompt = self.person.generate_system_prompt()
        if mode == "bike":
            template = "cyclist_comfort"
        else:
            template = "walking_comfort"
        prompt = generate_prompt([self.person.name, road.highway, road.maxspeed], template)
        response = generate_response(system_prompt, prompt)
        return int(response)

    def _remember_comfort(self, old_path: list[int]) -> None:
        """
        Generates and stores comfort values for the edges we just traversed.

        Args:
            old_path        The route path before we moved.
        """
        if self.route.mode == "drive":
            # Comfort for driving assumed to be invariable.
            return

        network = self.model.get_network(self.route.mode)
        # Get the nodes of the edges we've traversed
        nodes = [node for node in old_path if node not in self.route.path]
        nodes.append(self.route.path[0])

        # For every edge, store a comfort value
        for i in range(len(nodes) - 1):
            edge_info = network.edge_info(nodes[i], nodes[i + 1])
            road = self._get_road_type(edge_info)
            comfort = self.person.memory.get_comfort(road, self.route.mode)
            if comfort is None:
                comfort = self._get_comfort(road, self.route.mode)
                self.person.memory.store_comfort(road, self.route.mode, comfort)
            length = edge_info["length"]
            self.memory_entry.add_comfort(comfort, length)

    def _follow_route(self) -> None:
        """Move along the planned route"""
        network = self.model.get_network(self.route.mode)
        speed = self._get_speed(self.route.mode)

        old_path = self.route.path

        new_position, mins_left = network.traverse_route(
            route = self.route,
            time_step = self.model.time_step,
            speed = speed
        )

        self._remember_comfort(old_path)

        if new_position is None:
            # We have reached our destination
            new_position = self.model.get_location_coords(self.trip.destination)
            self.location = self.trip.destination
            trip_time = self._calculate_trip_time(mins_left)
            self.memory_entry.complete_memory(trip_time)
            self._clear_travel_info()
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
            # Plan the trip in the timestep before the trip starts.
            # < 2 * to handle the case where we plan to start in the middle of a time step.
            # e.g. time_step = 5 and trip starting at 10:12, plan at 10:05.
            if self.model.time.time_to(self.trip.start_time) < 2 * self.model.time_step:
                self._plan_route()
        elif self.model.time.time_to(Time(4, 0)) < self.model.time_step:
            # Plan for the day
            self.person.plan_day()
            self._next_plan_step()
