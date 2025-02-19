"""Util script to create a scenario from a real location"""
import os
import osmnx as ox
import pandas as pd

DIRECTORY = "./scenarios/ton_test/"

LOCATION = {
    "centre": "Tonbridge Castle",
    "radius": 3000
}

def create_network_of_type(network_type: str) -> None:
    """Fetches network of given type for specified location and writes it to disk"""
    # TODO: ensure graph is fully connected?
    graph = ox.graph_from_address(
        LOCATION["centre"],
        dist=LOCATION["radius"],
        network_type=network_type
    )
    out_path = os.path.join(DIRECTORY, f"network_{network_type}.graphml")
    ox.io.save_graphml(graph, out_path)

def get_areas(landuses: list[str]) -> None:
    """Fetches areas of the specified type"""
    gdf_list = []
    for landuse in landuses:
        areas = ox.features_from_address(
            LOCATION["centre"],
            dist=LOCATION["radius"],
            tags={"landuse": landuse}
        )
        gdf_list.append(areas)
    return gdf_list

def create_areas_of_types(landuses: list[str]) -> None:
    """Fetches areas of the specified type and writes them to disk"""
    gdf_list = get_areas(landuses)
    combined_areas = pd.concat(gdf_list, ignore_index=True)
    out_path = os.path.join(DIRECTORY, "areas.geojson")
    combined_areas.to_file(out_path, driver="GeoJSON")

if __name__ == "__main__":
    create_network_of_type("drive")
    create_network_of_type("walk")
    create_network_of_type("bike")
    create_areas_of_types(["residential", "retail", "industrial"])
