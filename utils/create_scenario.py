"""Util script to create a scenario from a real location"""
import os
import json
import random
import osmnx as ox
import pandas as pd
from geopandas import GeoDataFrame
from shapely import Polygon, Point

DIRECTORY = "./scenarios/westerham/"

LOCATION = {
    "centre": "Westerham Kings Arms Hotel",
    "radius": 1250
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

def get_areas(landuses: list[str]) -> GeoDataFrame:
    """Fetches areas of the specified type"""
    gdf_list = []
    for landuse in landuses:
        areas = ox.features_from_address(
            LOCATION["centre"],
            dist=LOCATION["radius"],
            tags={"landuse": landuse}
        )
        gdf_list.append(areas)
    return pd.concat(gdf_list, ignore_index=True)

def create_areas_of_types(landuses: list[str]) -> None:
    """Fetches areas of the specified type and writes them to disk"""
    gdf = get_areas(landuses)
    out_path = os.path.join(DIRECTORY, "areas.geojson")
    gdf.to_file(out_path, driver="GeoJSON")

def get_shops_and_amenities() -> list[dict[str, any]]:
    """Fetches all named shops + amenities"""
    features = ox.features_from_address(
        LOCATION["centre"],
        dist=LOCATION["radius"],
        tags={"shop": True, "amenity": True}
    )
    named_features = features[features["name"].notna()]
    return [v.dropna().to_dict() for _, v in named_features.iterrows()]

def get_feature_geometry(feature: dict[str, any]) -> Point:
    """Gets a point to represent the given feature"""
    geometry = feature["geometry"]
    if isinstance(geometry, Polygon):
        geometry = geometry.centroid
    return geometry

def get_feature_description(feature: dict[str, any]) -> str:
    """Gets a description of the given feature"""
    description = []
    if "amenity" in feature:
        description.append(f"amenity type: {feature["amenity"]}")
    if "shop" in feature:
        description.append(f"shop type: {feature["shop"]}")
    if "cuisine" in feature:
        description.append(f"cuisine: {feature["cuisine"]}")
    return ", ".join(description)

def get_shop_amenity_locations() -> dict[str, dict[str, str | float]]:
    """
    Fetches all named shops + amenities and creates 
    correctly formatted entries for them.
    """
    feature_list = get_shops_and_amenities()
    locations = {}
    for feature in feature_list:
        name = feature["name"]
        locations[name] = {}
        geometry = get_feature_geometry(feature)
        locations[name]["lat"] = geometry.y
        locations[name]["long"] = geometry.x
        locations[name]["description"] = get_feature_description(feature)
    return locations

def get_random_point(area: Polygon) -> Point:
    """Returns a random point within this area"""
    min_x, min_y, max_x, max_y = area.bounds
    point = None
    while not (point and point.within(area)):
        point = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
    return point

def get_houses(num: int) -> dict[str, dict[str, str | float]]:
    """Creates the specified number of houses"""
    residential_areas = get_areas(["residential"])
    row_indices = range(residential_areas.shape[0])
    weights = [row["geometry"].area for _, row in residential_areas.iterrows()]
    areas_to_choose = random.choices(row_indices, weights=weights, k=num)

    houses = {}
    for i, area_index in enumerate(areas_to_choose):
        area = residential_areas.loc[area_index, "geometry"]
        geometry = get_random_point(area)
        houses[f"House {i}"] = {
            "lat": geometry.y,
            "long": geometry.x,
            "description": "House"
        }
    return houses

def create_locations(num_houses: int) -> None:
    """Creates and writes locations to disk"""
    shops_amenities = get_shop_amenity_locations()
    houses = get_houses(num_houses)
    locations = shops_amenities | houses

    out_path = os.path.join(DIRECTORY, "locations.json")
    with open(out_path, "w", encoding="utf-8") as file:
        json.dump(locations, file, indent = 4)

def create_global_info() -> None:
    """Creates an empty global info file"""
    path = os.path.join(DIRECTORY, "global_info.txt")
    with open(path, "w", encoding="utf-8") as file:
        file.write("")

if __name__ == "__main__":
    create_network_of_type("drive")
    create_network_of_type("walk")
    create_network_of_type("bike")
    create_areas_of_types(["residential", "retail", "industrial"])
    create_locations(50)
    create_global_info()
