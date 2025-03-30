"""Analysis of model outputs"""
import os
import pandas as pd
import matplotlib.pyplot as plt

SCENARIO = "westerham"
RUN = 4

#print(df["mode"].value_counts())
#print(df.groupby(["start_day"]).value_counts())

def graph_daily_share(trips: pd.DataFrame):
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

def final_n_days_share(trips: pd.DataFrame, n: int):
    """Prints the mode share across all trips made in the last n days"""
    final_day = trips["start_day"].max()
    last_n_days = trips[trips["start_day"] > final_day - n]
    percentages = last_n_days["mode"].value_counts(normalize=True) * 100
    print(percentages)

if __name__ == "__main__":
    data_path = os.path.join("./output", SCENARIO, f"run {RUN}.csv")
    df = pd.read_csv(data_path)
    graph_daily_share(df)
    final_n_days_share(df, 5)
