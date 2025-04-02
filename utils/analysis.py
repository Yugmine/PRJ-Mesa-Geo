"""Analysis of recorded trip data"""
import os
import pandas as pd
import matplotlib.pyplot as plt

SCENARIO = "westerham"
RUN = 17

def graph_daily_share(trips: pd.DataFrame) -> None:
    """Graphs the percentage share of each mode per day"""
    daily_counts = trips.groupby(["start_day", "mode"]).size().unstack(fill_value=0)
    daily_percentage = daily_counts.div(daily_counts.sum(axis=1), axis=0) * 100

    graph = daily_percentage.plot(kind="line", marker="o")
    graph.set_xticks(range(1, len(daily_percentage.index) + 1))

    plt.title("Percentage Mode Share by Day")
    plt.xlabel("Day")
    plt.ylabel("Percentage Share (%)")
    plt.legend(title="Mode")
    plt.grid(True)
    plt.show()

def final_n_days_share(trips: pd.DataFrame, n: int) -> None:
    """Prints the mode share across all trips made in the last n days"""
    final_day = trips["start_day"].max()
    last_n_days = trips[trips["start_day"] > final_day - n]
    percentages = last_n_days["mode"].value_counts(normalize=True) * 100
    print(percentages)

def trips_under_mile(trips: pd.DataFrame) -> float:
    """Returns a dataframe with only trips under 1 mile"""
    return trips[trips["distance"] < 1609.34]

def percent_under_mile(trips: pd.DataFrame) -> None:
    """Prints the proportion of trips that were under 1 mile"""
    under_a_mile = trips_under_mile(trips).shape[0]
    total_rows = trips.shape[0]
    percentage = (under_a_mile / total_rows) * 100
    print(f"{percentage:.1f}% of trips were under a mile")

def count_destination_occurences(trips: pd.DataFrame, destination: str) -> float:
    """Counts the number of times agents travelled to the given destination"""
    trips_to_destination = trips[trips["destination"] == destination]
    return trips_to_destination.shape[0]

if __name__ == "__main__":
    data_path = os.path.join("./output", SCENARIO, f"run {RUN}.csv")
    df = pd.read_csv(data_path)
    #final_n_days_share(df, 5)
    #final_n_days_share(trips_under_mile(df), 5)
    #percent_under_mile(df)
    #graph_daily_share(df)
    print(count_destination_occurences(df, "Costa"))
