# digital_twin_garbage_sim_dynamic_routes_geojson.py
import os
import random
import pandas as pd
import folium
from folium.plugins import AntPath
import osmnx as ox
import networkx as nx
from shapely.geometry import shape, Point
import geopandas as gpd
import webbrowser

# ---------------- CONFIG ----------------
BINS_CSV = "bins.csv"
USER_REPORTS_CSV = "user_reports.csv"
GEOJSON_FILE = "KR_Puram.geojson"
GRAPH_FILE = "krpuram_graph.graphml"     # cached graph for faster runs
SIM_DAYS = 7
VEHICLE_CAPACITY = 5000
OUTPUT_TEMPLATE = "day{:02d}.html"
LAUNCHER_FILE = "launch_all_iframes.html"
DEPOT = (13.007242, 77.677815)  # Lowry east gate (lat, lon)
random.seed(42)

# ---------------- LOAD K R PURAM BOUNDARY ----------------
if not os.path.exists(GEOJSON_FILE):
    raise FileNotFoundError(f"{GEOJSON_FILE} not found.")
gdf = gpd.read_file(GEOJSON_FILE)
if gdf.empty:
    raise ValueError("GeoJSON file appears empty or invalid.")
if gdf.crs is not None and gdf.crs.to_string() != "EPSG:4326":
    gdf = gdf.to_crs("EPSG:4326")
WARD_BOUNDARY = shape(gdf.iloc[0].geometry)

# ---------------- LOAD ROAD NETWORK ----------------
print("⏳ Loading road network within and around K R Puram boundary...")

# Slightly expand boundary (~300m buffer) to avoid routing breaks at borders
buffered_boundary = WARD_BOUNDARY.buffer(0.003)

if os.path.exists(GRAPH_FILE):
    G = ox.load_graphml(GRAPH_FILE)
    print("✅ Loaded cached graph.")
else:
    G = ox.graph_from_polygon(buffered_boundary, network_type="drive")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    ox.save_graphml(G, GRAPH_FILE)
    print("✅ Downloaded and cached graph for future runs.")

print(f"✅ Road network loaded with {len(G.nodes)} nodes and {len(G.edges)} edges.")

# ---------------- NODE HELPER ----------------
def nearest_node(lat, lon):
    """Safely find nearest road node for given coordinates"""
    try:
        return ox.distance.nearest_nodes(G, lon, lat)
    except Exception:
        # fallback: brute-force search
        min_dist = float('inf')
        nearest = None
        for n in G.nodes:
            y, x = G.nodes[n]['y'], G.nodes[n]['x']
            d = (lat - y) ** 2 + (lon - x) ** 2
            if d < min_dist:
                min_dist = d
                nearest = n
        return nearest

depot_node = nearest_node(DEPOT[0], DEPOT[1])
if depot_node is None:
    raise ValueError("Could not locate depot node inside expanded K R Puram area.")

# ---------------- LOAD STATIC BINS ----------------
bins_df = pd.read_csv(BINS_CSV)
def ensure_col(df, col, default):
    if col not in df.columns:
        df[col] = default
ensure_col(bins_df, "lat", 0.0)
ensure_col(bins_df, "lon", 0.0)
ensure_col(bins_df, "capacity", 1000)
ensure_col(bins_df, "fill", 0)
ensure_col(bins_df, "daily_growth", 100)

bins = []
for i, row in bins_df.iterrows():
    try:
        lat, lon = float(row["lat"]), float(row["lon"])
    except:
        continue
    # keep bins strictly inside original K R Puram boundary
    if not WARD_BOUNDARY.contains(Point(lon, lat)):
        continue
    bins.append({
        "id": row.get("id", f"Bin{i+1}"),
        "lat": lat,
        "lon": lon,
        "capacity": float(row["capacity"]),
        "fill": float(row["fill"]),
        "daily_growth": float(row["daily_growth"]),
        "last_visited_day": int(row.get("last_visited_day", -1)),
        "is_user_report": False
    })

# ---------------- LOAD USER REPORTS ----------------
def load_user_reports():
    if not os.path.exists(USER_REPORTS_CSV):
        return []
    df = pd.read_csv(USER_REPORTS_CSV)
    reports = []
    for _, r in df.iterrows():
        try:
            lat, lon = float(r["lat"]), float(r["lon"])
        except:
            continue
        if r.get("status", "").lower() != "unvisited":
            continue
        if not WARD_BOUNDARY.contains(Point(lon, lat)):
            continue
        reports.append({
            "id": f"User_{r.get('name','anon')}",
            "lat": lat,
            "lon": lon,
            "capacity": 1000,
            "fill": 1000,
            "daily_growth": 0,
            "last_visited_day": -1,
            "is_user_report": True,
            "report_row_name": r.get("name")
        })
    return reports

user_reports = load_user_reports()
bins.extend(user_reports)

# ---------------- HELPERS ----------------
def color_for_fill(p):
    if p < 0.5:
        return "green"
    elif p < 0.8:
        return "orange"
    else:
        return "red"

def compute_route_path(node_a, node_b):
    """Compute shortest path along road network using travel_time"""
    try:
        route = nx.shortest_path(G, node_a, node_b, weight="travel_time")
        return [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]
    except nx.NetworkXNoPath:
        # fallback: re-snap and retry
        node_a2 = nearest_node(G.nodes[node_a]['y'], G.nodes[node_a]['x'])
        node_b2 = nearest_node(G.nodes[node_b]['y'], G.nodes[node_b]['x'])
        try:
            route = nx.shortest_path(G, node_a2, node_b2, weight="travel_time")
            return [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]
        except:
            return []

def mark_user_visited(name):
    if not os.path.exists(USER_REPORTS_CSV):
        return
    df = pd.read_csv(USER_REPORTS_CSV)
    mask = df["name"].astype(str) == str(name)
    if mask.any():
        df.loc[mask, "status"] = "visited"
        df.to_csv(USER_REPORTS_CSV, index=False)

# ---------------- ROUTE PLANNER ----------------
def plan_route(bins_today, current_day):
    remaining = VEHICLE_CAPACITY
    visited = []
    current_node = depot_node
    path = [DEPOT]

    def priority(b):
        pct = b["fill"] / b["capacity"]
        days_ignored = current_day - b["last_visited_day"]
        if pct >= 0.8:
            return (0, -pct)
        elif pct >= 0.6:
            return (1, -pct)
        elif days_ignored >= 2:
            return (2, -pct)
        else:
            return (3, -pct)

    candidates = [i for i, b in enumerate(bins_today) if b["fill"] > 0]
    while candidates and remaining > 0:
        candidates.sort(key=lambda i: priority(bins_today[i]))
        best_idx = candidates[0]
        b = bins_today[best_idx]
        node_b = nearest_node(b["lat"], b["lon"])
        segment = compute_route_path(current_node, node_b)
        if segment:
            path += segment[1:]
        pickup = min(remaining, b["fill"])
        b["fill"] -= pickup
        remaining -= pickup
        b["last_visited_day"] = current_day
        if b.get("is_user_report"):
            mark_user_visited(b["report_row_name"])
        visited.append(best_idx)
        current_node = node_b
        candidates.remove(best_idx)

    # Return to depot
    back = compute_route_path(current_node, depot_node)
    if back:
        path += back[1:]
    return path, visited

# ---------------- SIMULATION ----------------
daily_pages = []
for day in range(1, SIM_DAYS + 1):
    print(f"\n📅 Simulating Day {day}...")
    for b in bins:
        if not b.get("is_user_report"):
            b["fill"] = min(b["capacity"], b["fill"] + b["daily_growth"] + random.randint(-50, 80))

    path, visited = plan_route(bins, day)
    m = folium.Map(location=DEPOT, zoom_start=14)

    folium.GeoJson(
        WARD_BOUNDARY.__geo_interface__,
        name="K R Puram Boundary",
        style_function=lambda x: {"color": "blue", "weight": 3, "fill": False}
    ).add_to(m)

    folium.Marker(
        DEPOT,
        popup="Depot (Lowry East Gate)",
        icon=folium.Icon(color="blue", icon="truck", prefix="fa")
    ).add_to(m)

    for b in bins:
        pct = b["fill"] / b["capacity"]
        if b.get("is_user_report"):
            folium.Marker(
                [b["lat"], b["lon"]],
                popup=f"USER REPORT: {b['id']}",
                icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa")
            ).add_to(m)
        else:
            folium.CircleMarker(
                [b["lat"], b["lon"]],
                radius=6,
                color=color_for_fill(pct),
                fill=True,
                fill_opacity=0.9,
                popup=f"{b['id']} - {int(b['fill'])}/{int(b['capacity'])}L"
            ).add_to(m)

    if path and len(path) > 2:
        AntPath(path, color="purple", weight=4, opacity=0.8).add_to(m)

    out = OUTPUT_TEMPLATE.format(day)
    m.save(out)
    daily_pages.append(out)
    print(f"✅ Saved {out}")

# ---------------- LAUNCHER ----------------
html = "<html><head><title>K R Puram Garbage Simulation</title></head><body><h2>Simulation Maps</h2>"
for i, f in enumerate(daily_pages, 1):
    html += f"<h3>Day {i}</h3><iframe src='{f}' width='100%' height='600'></iframe><br>"
html += "</body></html>"

with open(LAUNCHER_FILE, "w", encoding="utf-8") as f:
    f.write(html)

webbrowser.open("file://" + os.path.realpath(LAUNCHER_FILE))
print(f"\n✅ All {SIM_DAYS} maps generated with improved routing near K R Puram border.")
