"""Handles time in the model."""

class Time:
    """
    hour    Current hour
    minute  Current minute
    """
    hour: int
    minute: float

    def __init__(
        self,
        hour: int,
        minute: float
    )  -> None:
        self.hour = hour
        self.minute = minute

    def __eq__(self, other):
        return self.hour == other.hour and self.minute == other.minute

    def __repr__(self):
        return f"{self.hour:02d}:{self.minute:02d}"

    def _increment(self, extra_mins: float) -> tuple[int, float]:
        """
        Returns hour and minute values that have been
        incremented by the provided number of minutes.
        Assumes an increment of < 60 minutes.
        """
        new_hour = self.hour
        new_minute = self.minute + extra_mins
        if new_minute >= 60:
            new_minute -= 60
            new_hour += 1
            if new_hour == 24:
                new_hour = 0
        return new_hour, new_minute

    def n_mins_from_now(self, n: float) -> 'Time':
        """Returns a time object that's n minutes later than this one"""
        new_hour, new_minute = self._increment(n)
        return Time(new_hour, new_minute)

    def perform_time_step(self, step: float) -> bool:
        """
        Increments stored values by the provided time step.

        Returns:
            Whether the increment moves the time over to a new day.
        """
        old_hour = self.hour
        self.hour, self.minute = self._increment(step)
        if self.hour < old_hour:
            return True
        return False

    def time_to(self, end: 'Time') -> float:
        """
        Calculates the time from this time to the provided time (in minutes)
        Only looks forwards (e.g. if this time is 16:30 and end is 16:15, returns 1425).
        Assumes difference < 24 hours.
        """
        if end.hour < self.hour or (end.hour == self.hour and end.minute < self.minute):
            # We've rolled over to tomorrow
            time_before_midnight = (60 * (23 - self.hour)) + (60 - self.minute)
            time_after_midnight = (60 * end.hour) + end.minute
            return time_before_midnight + time_after_midnight
        return (60 * (end.hour - self.hour)) + (end.minute - self.minute)

    def copy(self) -> 'Time':
        """Creates a copy of this object"""
        return Time(self.hour, self.minute)
