"""Analysis of model outputs"""
import os
import pandas as pd

SCENARIO = "westerham"
RUN = 0

data_path = os.path.join("./output", SCENARIO, f"run {RUN}.csv")

df = pd.read_csv(data_path)

print(df["mode"].value_counts())
