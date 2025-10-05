# digital_twin_garbage_sim_dynamic_routes.py
import os
import random
from datetime import datetime, timedelta
import pandas as pd
import folium
from folium.plugins import AntPath
from shapely.geometry import Point
import geopandas as gpd
import osmnx as ox
import networkx as nx
import webbrowser
import math

# ---------------- CONFIG ----------------
WARD_FILE = "KR_Puram.geojson"
NUM_BINS = 30
VEHICLE_CAPACITY = 5000
SIM_DAYS = 7
OUTPUT_TEMPLATE = "day{:02d}.html"
DEPOT = (13.007242, 77.677815)  # Lowry east gate

# ---------------- LOAD POLYGON ----------------
def load_polygon(path):
    gdf = gpd.read_file(path)
    geom = gdf.geometry.unary_union if len(gdf) > 1 else gdf.geometry.iloc[0]
    return geom

WARD = load_polygon(WARD_FILE)
print("✅ Loaded KR Puram polygon")

# ---------------- NETWORK ----------------
print("⏳ Loading road network...")
G = ox.graph_from_polygon(WARD, network_type="drive")
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)
print("✅ Network ready")

depot_node = ox.nearest_nodes(G, DEPOT[1], DEPOT[0])

# ---------------- BIN GENERATION ----------------
def random_bin_in_polygon(poly, idnum):
    minx, miny, maxx, maxy = poly.bounds
    while True:
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if poly.contains(p):
            return {
                "id": f"Bin{idnum}",
                "lat": float(p.y),
                "lon": float(p.x),
                "capacity": 1000,
                "fill": random.randint(100, 600),  # start partially filled
                "daily_growth": random.randint(100, 250),  # different growth speed
            }

bins = [random_bin_in_polygon(WARD, i) for i in range(NUM_BINS)]

# ---------------- HELPERS ----------------
def color_for_fill(p):
    if p < 0.5:
        return "green"
    elif p < 0.8:
        return "orange"
    else:
        return "red"

# get nearest node for bin
def nearest_node_for_bin(bin):
    try:
        return ox.nearest_nodes(G, bin["lon"], bin["lat"])
    except Exception:
        return None

# compute route
def compute_route_path(node_a, node_b):
    try:
        route = nx.shortest_path(G, node_a, node_b, weight="travel_time")
        coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]
        return coords
    except Exception:
        return []

# ---------------- ROUTE PLANNER ----------------
def plan_route(bins_today):
    remaining = VEHICLE_CAPACITY
    visited = []
    current = depot_node
    path_coords = [(DEPOT[0], DEPOT[1])]

    # candidate bins = those > 60% full
    candidates = [i for i, b in enumerate(bins_today) if b["fill"] / b["capacity"] >= 0.6]
    random.shuffle(candidates)  # randomize selection order slightly

    while candidates and remaining > 0:
        # pick nearest feasible bin
        distances = []
        for i in candidates:
            node = nearest_node_for_bin(bins_today[i])
            if node:
                try:
                    d = nx.shortest_path_length(G, current, node, weight="length")
                except:
                    d = float("inf")
            else:
                d = float("inf")
            distances.append(d)
        nearest_idx = candidates[distances.index(min(distances))]
        bin = bins_today[nearest_idx]
        needed = bin["fill"]

        if needed <= remaining:
            remaining -= needed
            visited.append(nearest_idx)
            bin["fill"] = 0  # emptied
        else:
            bin["fill"] -= remaining
            remaining = 0

        # extend path
        node_b = nearest_node_for_bin(bin)
        seg = compute_route_path(current, node_b)
        if seg:
            path_coords += seg[1:]
        current = node_b
        candidates.remove(nearest_idx)

    # return to depot
    back = compute_route_path(current, depot_node)
    if back:
        path_coords += back[1:]

    return path_coords, visited

# ---------------- SIMULATION ----------------
for day in range(1, SIM_DAYS + 1):
    print(f"📅 Simulating Day {day}...")

    # daily fill increase
    for b in bins:
        b["fill"] = min(b["capacity"], b["fill"] + b["daily_growth"] + random.randint(-50, 80))

    # plan route
    path, visited = plan_route(bins)

    # map setup
    m = folium.Map(location=DEPOT, zoom_start=14)
    folium.GeoJson(WARD.__geo_interface__, style_function=lambda x: {"color":"blue","weight":3,"fill":False}).add_to(m)
    folium.Marker(DEPOT, popup="Depot", icon=folium.Icon(color="blue", icon="truck", prefix="fa")).add_to(m)

    # bins
    for b in bins:
        pct = b["fill"] / b["capacity"]
        folium.CircleMarker(
            location=[b["lat"], b["lon"]],
            radius=6,
            color=color_for_fill(pct),
            fill=True,
            fill_opacity=0.9,
            popup=f"{b['id']} - {b['fill']}/{b['capacity']} L"
        ).add_to(m)

    # route
    if len(path) > 2:
        AntPath(path, color="purple", weight=4, opacity=0.8).add_to(m)

    out = OUTPUT_TEMPLATE.format(day)
    m.save(out)
    print(f"✅ Saved {out}")

# open day01
webbrowser.open("file://" + os.path.realpath(OUTPUT_TEMPLATE.format(1)))
print("\nAll 7 maps generated. Each day has a different route and updated fill levels.")
