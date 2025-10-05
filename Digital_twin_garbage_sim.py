# digital_twin_garbage_sim_priority.py
import os
import sys
import subprocess
import random
from datetime import datetime, timedelta
import pandas as pd
import folium
from shapely.geometry import Point
import geopandas as gpd
import osmnx as ox
import networkx as nx
import webbrowser
from collections import defaultdict
import copy

# ---------------------- Config ----------------------
WARD_FILE = "KR_Puram.geojson"
NUM_BINS = 30
VEHICLE_CAPACITY_L = 5000
SIM_DAYS = 7
OUTPUT_METRICS = "metrics_krpuram_priority_routing.csv"
DEPOT_COORD = (13.007242, 77.677815)  # (lat, lon)

random.seed(42)

# ---------------------- Load ward polygon ----------------------
def load_ward_polygon(geojson_file):
    gdf = gpd.read_file(geojson_file)
    if gdf.empty:
        raise ValueError(f"No polygon found in {geojson_file}")
    return gdf.geometry.unary_union

WARD_POLYGON = load_ward_polygon(WARD_FILE)
print("🗺️ Loaded KR Puram polygon.")

# ---------------------- Generate bins ----------------------
def random_point_in_polygon(polygon):
    minx, miny, maxx, maxy = polygon.bounds
    while True:
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(p):
            return {
                "lat": p.y,
                "lon": p.x,
                "capacity_L": 1000,
                "fill_L": 0,
                "id": f"Bin{random.randint(1000,9999)}",
                "last_serviced_day": -1,   # last day we removed >0
                "last_visited_day": -1,    # last day we stopped here (even 0 pickup)
                "first_seen_day": 0,       # initial bins exist from day 0
            }

bins = [random_point_in_polygon(WARD_POLYGON) for _ in range(NUM_BINS)]
print(f"✅ Generated {NUM_BINS} bins.")

# ---------------------- Utils ----------------------
def color_for_fill(pct):
    if pct < 0.5:
        return 'green'
    elif pct < 0.8:
        return 'orange'
    else:
        return 'red'

def haversine_km(a, b):
    from math import radians, sin, cos, asin, sqrt
    lat1, lon1 = a
    lat2, lon2 = b
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lat2 - lon1)
    lat1 = radians(lat1); lat2 = radians(lat2)
    h = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2*R*asin(sqrt(h))

def open_file_in_browser(path):
    url = 'file://' + os.path.realpath(path)
    opened = False
    try:
        opened = webbrowser.open_new(url)
    except Exception:
        opened = False
    if opened:
        return
    try:
        if sys.platform.startswith('win'):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == 'darwin':
            subprocess.call(['open', path])
        else:
            subprocess.call(['xdg-open', path])
    except Exception as e:
        print(f"Could not auto-open {path}: {e}\nOpen manually: {os.path.realpath(path)}")

# ---------------------- Road network ----------------------
print("🛣️ Loading road network...")
buffered_poly = WARD_POLYGON.buffer(0.001)  # ~100m buffer
G = ox.graph_from_polygon(buffered_poly, network_type='drive')
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)
depot_node = ox.distance.nearest_nodes(G, DEPOT_COORD[1], DEPOT_COORD[0])
print("✅ Road network loaded.")

def safe_nearest_node(lat, lon):
    try:
        return ox.distance.nearest_nodes(G, lon, lat)
    except Exception:
        return None

# ---------------------- User reports ----------------------
USER_REPORTS = "user_reports.csv"
def load_user_reports():
    if not os.path.exists(USER_REPORTS):
        return []
    df = pd.read_csv(USER_REPORTS)
    if "status" not in df.columns:
        df["status"] = "unvisited"
    df_un = df[df["status"].astype(str).str.lower() == "unvisited"]
    out = []
    for _, r in df_un.iterrows():
        try:
            lat = float(r["lat"]); lon = float(r["lon"])
        except Exception:
            continue
        out.append({
            "id": f"User_{r.get('name','anon')}",
            "lat": lat,
            "lon": lon,
            "capacity_L": 1000,
            "fill_L": 1000,
            "last_serviced_day": -1,
            "last_visited_day": -1,
            # first_seen_day set when merged into sim
        })
    return out

def mark_user_bin_visited(bin_id, picked):
    """Mark user report visited as 'visited' when we actually pick >0."""
    if picked <= 0 or not os.path.exists(USER_REPORTS):
        return
    df = pd.read_csv(USER_REPORTS)
    name = bin_id.replace("User_", "")
    mask = df["name"].astype(str) == name
    if mask.any():
        df.loc[mask, "status"] = "visited"
        df.to_csv(USER_REPORTS, index=False)

# ---------------------- Routing (STRICT phasing, FULL CLEAR) ----------------------
def plan_priority_routes(bins_state, day_idx):
    """
    RED -> YELLOW -> GREEN, with SLA "aging-to-red":
      - At start of day, a bin is RED if (fill >= 80%) OR (unvisited >= 2 days since max(first_seen_day, last_visited_day)).
      - We keep making trips until ALL bins in the current phase are EMPTY (fill == 0),
        then move to the next phase. No bin can be skipped.
      - Nearest-next heuristic, partial pickups allowed, graph fallback to haversine if needed.
    Returns: (routes, served_ids)
    """
    # Snap (with jitter retry)
    for b in bins_state:
        node = safe_nearest_node(b['lat'], b['lon'])
        if node is None:
            jitter = 0.0001
            node = safe_nearest_node(b['lat']+random.uniform(-jitter,jitter),
                                     b['lon']+random.uniform(-jitter,jitter))
        b['node'] = node

    def days_unvisited(b):
        anchor = max(b.get('first_seen_day', day_idx), b.get('last_visited_day', -1))
        return max(0, day_idx - anchor)

    def sod_category(b):
        cap = b.get('capacity_L', 0) or 1
        pct = (b.get('fill_L', 0) / cap)
        if pct >= 0.8 or days_unvisited(b) >= 2:
            return 'red'
        elif pct >= 0.5:
            return 'yellow'
        else:
            return 'green'

    # Freeze members per phase at start-of-day
    phase_bins = {'red': [], 'yellow': [], 'green': []}
    for b in bins_state:
        if b.get('fill_L', 0) > 0:
            phase_bins[sod_category(b)].append(b)

    def dist_m(from_node, to_node, from_coord, to_coord):
        if from_node is not None and to_node is not None:
            try:
                return nx.shortest_path_length(G, from_node, to_node, weight='length')
            except Exception:
                pass
        return haversine_km(from_coord, to_coord) * 1000.0

    served_ids = set()
    day_routes = []

    for phase in ['red', 'yellow', 'green']:
        active = [b for b in phase_bins[phase] if b.get('fill_L', 0) > 0]
        print(f"➡️  Day {day_idx+1} phase '{phase}' bins to EMPTY: {len(active)}")

        trips = 0
        safety_guard = 0
        while any(b.get('fill_L', 0) > 0 for b in active):
            safety_guard += 1
            if safety_guard > 10000:
                raise RuntimeError(f"Safety guard tripped in phase {phase} (possible infinite loop).")

            trips += 1
            remaining_capacity = VEHICLE_CAPACITY_L
            route = []

            current_node = depot_node
            current_coord = DEPOT_COORD

            # Keep collecting nearest non-empty bins until truck is full
            while remaining_capacity > 0 and any(b.get('fill_L', 0) > 0 for b in active):
                # nearest non-empty candidate
                candidates = []
                for b in active:
                    if b.get('fill_L', 0) <= 0:
                        continue
                    d = dist_m(current_node, b.get('node'), current_coord, (b['lat'], b['lon']))
                    candidates.append((d, b))
                if not candidates:
                    break
                candidates.sort(key=lambda x: x[0])
                _, nxt = candidates[0]

                pickup = min(nxt['fill_L'], remaining_capacity)
                if pickup <= 0:
                    break

                # record stop
                route.append({
                    "id": nxt['id'],
                    "lat": nxt['lat'],
                    "lon": nxt['lon'],
                    "node": nxt.get('node'),
                    "picked_L": pickup
                })
                served_ids.add(nxt['id'])

                # apply pickup + visit stamps
                nxt['fill_L'] -= pickup
                remaining_capacity -= pickup
                nxt['last_visited_day'] = day_idx
                if pickup > 0:
                    nxt['last_serviced_day'] = day_idx
                if nxt['id'].startswith("User_"):
                    mark_user_bin_visited(nxt['id'], pickup)

                # move position
                if nxt.get('node') is not None:
                    current_node = nxt['node']
                    current_coord = (G.nodes[current_node]['y'], G.nodes[current_node]['x'])
                else:
                    current_node = None
                    current_coord = (nxt['lat'], nxt['lon'])

            # Materialize this trip to coords
            if route:
                path_coords = [DEPOT_COORD]
                last_node = depot_node
                for stop in route:
                    s_node = stop['node']
                    if last_node is not None and s_node is not None:
                        try:
                            nodes_path = nx.shortest_path(G, last_node, s_node, weight='length')
                            for n in nodes_path[1:]:
                                path_coords.append((G.nodes[n]['y'], G.nodes[n]['x']))
                            last_node = s_node
                        except Exception:
                            path_coords.append((stop['lat'], stop['lon']))
                            last_node = None
                    else:
                        path_coords.append((stop['lat'], stop['lon']))
                        last_node = None

                # return to depot
                if last_node is not None:
                    try:
                        nodes_path = nx.shortest_path(G, last_node, depot_node, weight='length')
                        for n in nodes_path[1:]:
                            path_coords.append((G.nodes[n]['y'], G.nodes[n]['x']))
                    except Exception:
                        path_coords.append(DEPOT_COORD)
                else:
                    path_coords.append(DEPOT_COORD)

                day_routes.append({"coords": path_coords, "stops": route})

        # Phase must be empty now — enforce
        leftover = [b['id'] for b in active if b.get('fill_L', 0) > 0]
        if leftover:
            raise RuntimeError(f"Phase '{phase}' ended with non-empty bins: {leftover[:10]}{'...' if len(leftover)>10 else ''}")
        print(f"✅ Day {day_idx+1} phase '{phase}' cleared in {trips} trip(s).")

    return day_routes, served_ids

# ---------------------- Simulation ----------------------
def simulate_priority():
    daily_bins_state = []
    daily_routes = []
    metrics = []
    now = datetime.now()

    bins_state = [copy.deepcopy(b) for b in bins]
    for b in bins_state:
        b.setdefault("first_seen_day", 0)
        b.setdefault("last_visited_day", -1)
        b.setdefault("last_serviced_day", -1)

    for day in range(SIM_DAYS):
        # daily accumulation
        for b in bins_state:
            daily_fill = random.randint(400, 600)
            b['fill_L'] = min(b['capacity_L'], b.get('fill_L', 0) + daily_fill)

        # add any new user-reported bins (first_seen_day = today)
        user_bins_today = {ub['id']: ub for ub in load_user_reports()}
        existing_ids = {b['id'] for b in bins_state}
        for uid, ub in user_bins_today.items():
            if uid not in existing_ids:
                ub = copy.deepcopy(ub)
                ub["first_seen_day"] = day
                ub.setdefault("last_visited_day", -1)
                ub.setdefault("last_serviced_day", -1)
                bins_state.append(ub)

        # plan strict phased routes (FULL CLEAR per phase)
        day_routes_out, _ = plan_priority_routes(bins_state, day)

        # metrics
        total_distance_km = 0.0
        overflow_events = sum(1 for b in bins_state if b['fill_L'] >= b['capacity_L'])
        total_pickups = 0
        for r in day_routes_out:
            coords = r["coords"]
            for i in range(len(coords)-1):
                try:
                    n1 = ox.distance.nearest_nodes(G, coords[i][1], coords[i][0])
                    n2 = ox.distance.nearest_nodes(G, coords[i+1][1], coords[i+1][0])
                    total_distance_km += nx.shortest_path_length(G, n1, n2, weight='length')/1000
                except Exception:
                    total_distance_km += haversine_km(coords[i], coords[i+1])
            total_pickups += len(r["stops"])

        daily_bins_state.append([copy.deepcopy(b) for b in bins_state])
        daily_routes.append([r["coords"] for r in day_routes_out])
        metrics.append({
            'day': day+1,
            'date': (now + timedelta(days=day)).strftime("%Y-%m-%d"),
            'overflow_events': int(overflow_events),
            'total_distance_km': float(total_distance_km),
            'total_pickups': int(total_pickups)
        })
        print(f"📈 Day {day+1} summary: trips={len(day_routes_out)}, distance={total_distance_km:.2f} km, pickups={total_pickups}, overflow={overflow_events}")

        # Debug audit: which bins still have fill >0 at end of day
        end_unemptied = [b['id'] for b in bins_state if b['fill_L'] > 0]
        print(f"🧾 End-of-day {day+1}: unemptied bins count = {len(end_unemptied)}")

    pd.DataFrame(metrics).to_csv(OUTPUT_METRICS, index=False)
    print(f"✅ Metrics saved: {OUTPUT_METRICS}")
    return daily_bins_state, daily_routes

# ---------------------- Map generation ----------------------
def write_maps_tabs(daily_bins_state, daily_routes):
    """
    Single self-contained map with LayerControl (no tabs/iframes/plugins).
    Routes use PolyLine (offline-friendly).
    """
    m_all = folium.Map(location=DEPOT_COORD, zoom_start=13)
    folium.GeoJson(
        WARD_POLYGON.__geo_interface__,
        name="Ward Boundary",
        style_function=lambda x: {"color": "blue", "weight": 2, "fill": False}
    ).add_to(m_all)

    for day_idx in range(SIM_DAYS):
        grp = folium.FeatureGroup(name=f"Day {day_idx+1}", show=(day_idx==0))
        # Bins
        for b in daily_bins_state[day_idx]:
            cap = b['capacity_L'] if b.get('capacity_L') else 1
            pct = (b['fill_L']/cap)
            folium.CircleMarker(
                location=(b['lat'], b['lon']),
                radius=6,
                color=color_for_fill(pct),
                fill=True, fill_opacity=0.85,
                popup=folium.Popup(
                    html=(f"<b>{b['id']}</b><br>"
                          f"Fill: {b['fill_L']}/{b['capacity_L']} L<br>"
                          f"Last visited day: {b.get('last_visited_day',-1)}<br>"
                          f"Last serviced day: {b.get('last_serviced_day',-1)}"),
                    max_width=320
                )
            ).add_to(grp)
        # Routes (polyline)
        for r in daily_routes[day_idx]:
            folium.PolyLine(locations=r, weight=4, opacity=0.9).add_to(grp)
        grp.add_to(m_all)

    folium.LayerControl(collapsed=False).add_to(m_all)

    out = "krpuram_dashboard.html"
    m_all.save(out)
    open_file_in_browser(out)
    print(f"📊 Dashboard saved at: {os.path.realpath(out)}")

# ---------------------- Main ----------------------
if __name__=="__main__":
    daily_bins, daily_routes = simulate_priority()
    write_maps_tabs(daily_bins, daily_routes)
