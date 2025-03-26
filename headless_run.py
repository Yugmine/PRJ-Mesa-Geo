"""Script to run the model without the visualisation"""
from transport_model.model import TransportModel

model = TransportModel(
    scenario = "westerham",
    time_step = 5,
    default_speed_limit = 30,
    car_speed_factor = 0.75,
    n_days = 5
)

if __name__ == "__main__":
    model.run_model()
