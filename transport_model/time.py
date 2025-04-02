"""Handles time in the model."""

class Time:
    """
    Object that represents a point in time.
    Intended to be immutable.

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
        return f"{self.hour:02d}:{int(self.minute):02d}"

    def n_mins_from_now(self, n: float) -> 'Time':
        """
        Args:
            n: A number of minutes to increment the current time by.
               Assumed to be < 60.
        
        Returns:
            A new Time object that's n minutes later than this one.
        """
        new_hour = self.hour
        new_minute = self.minute + n
        if new_minute >= 60:
            new_minute -= 60
            new_hour += 1
            if new_hour == 24:
                new_hour = 0
        return Time(new_hour, new_minute)

    def time_to(self, end: 'Time') -> float:
        """
        Calculates the gap from this time to the provided time (in minutes)
        Only looks forwards (e.g. if this time is 16:30 and end is 16:15, returns 1425).
        Assumes difference < 24 hours.

        Args:
            end: A Time object to compare with.
        Returns:
            The time from this time to end (in minutes).
        """
        if end.hour < self.hour or (end.hour == self.hour and end.minute < self.minute):
            # We've rolled over to tomorrow
            time_before_midnight = (60 * (23 - self.hour)) + (60 - self.minute)
            time_after_midnight = (60 * end.hour) + end.minute
            return time_before_midnight + time_after_midnight
        return (60 * (end.hour - self.hour)) + (end.minute - self.minute)
