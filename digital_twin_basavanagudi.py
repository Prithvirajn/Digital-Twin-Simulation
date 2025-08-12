import os
import sys
import warnings
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

# Optional OSMnx import
try:
    import osmnx as ox
    import networkx as nx
    OSMNX_AVAILABLE = True
except Exception:
    OSMNX_AVAILABLE = False

WARD_NUMBER = 154
WARD_NAME_KEYWORD = "Basavanagudi"
WARD_FILE = "BBMP.geojson"  # must be in same folder

# Garbage data file (adjust path/filename as needed)
GARBAGE_DATA_FILE = "garbage_data.csv"  # assumed CSV with lat/lon columns

def load_bbmp_data(path=WARD_FILE):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Boundary file '{path}' not found in current folder: {os.getcwd()}")
    gdf = gpd.read_file(path)
    print(f"Loaded '{path}' with {len(gdf)} features.")
    print("Columns available:", list(gdf.columns))
    return gdf

def extract_ward(gdf):
    ward_cols = []
    for c in gdf.columns:
        lc = c.lower()
        if "ward" in lc and ("no" in lc or "number" in lc or "id" in lc):
            ward_cols.append(c)
    for col in ward_cols:
        try:
            mask = gdf[col].astype(str).str.contains(str(WARD_NUMBER), na=False)
            if mask.any():
                found = gdf[mask]
                print(f"Found ward using column '{col}'.")
                return found
        except Exception:
            continue

    name_cols = [c for c in gdf.columns if "name" in c.lower() or "ward" in c.lower()]
    for col in name_cols:
        try:
            mask = gdf[col].astype(str).str.contains(WARD_NAME_KEYWORD, case=False, na=False)
            if mask.any():
                found = gdf[mask]
                print(f"Found ward by name using column '{col}'.")
                return found
        except Exception:
            continue

    print("\nCould not automatically locate Ward 154 (Basavanagudi).")
    print("Here are the first 5 rows of the GeoDataFrame to help debug:")
    with pd_option_context():
        print(gdf.head(5).to_string())
    raise ValueError("Ward 154 (Basavanagudi) not found in the provided GeoJSON.")

from contextlib import contextmanager
@contextmanager
def pd_option_context(width=120):
    import pandas as _pd
    old = _pd.get_option("display.width")
    try:
        _pd.set_option("display.width", width)
        yield
    finally:
        _pd.set_option("display.width", old)

def get_street_network(ward_gdf):
    if not OSMNX_AVAILABLE:
        warnings.warn("osmnx not installed — skipping street network fetch and route plotting.")
        return None

    # Use union_all if available (fixes deprecation warning)
    poly = ward_gdf.geometry.union_all() if hasattr(ward_gdf.geometry, "union_all") else ward_gdf.geometry.unary_union

    try:
        G = ox.graph_from_polygon(poly, network_type="drive")
        print(f"Downloaded OSM street network: nodes = {len(G.nodes)}, edges = {len(G.edges)}")
        return G
    except Exception as e:
        warnings.warn(f"osmnx failed to fetch street network: {e}")
        return None

def load_garbage_data(filename=GARBAGE_DATA_FILE):
    import pandas as pd
    if not os.path.exists(filename):
        warnings.warn(f"Garbage data file '{filename}' not found, skipping garbage data plotting.")
        return None
    df = pd.read_csv(filename)
    # Assume latitude and longitude columns (case insensitive)
    lat_col = next((c for c in df.columns if "lat" in c.lower()), None)
    lon_col = next((c for c in df.columns if "lon" in c.lower() or "lng" in c.lower()), None)
    if lat_col is None or lon_col is None:
        warnings.warn("Garbage data CSV missing latitude or longitude columns.")
        return None
    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    print(f"Loaded garbage data with {len(gdf)} points.")
    return gdf

def plot_results(ward_gdf, G=None, garbage_gdf=None):
    fig, ax = plt.subplots(figsize=(10, 10))
    ward_gdf.plot(ax=ax, facecolor="none", edgecolor="crimson", linewidth=2, label="Ward Boundary")
    if G is not None:
        try:
            ox.plot_graph(G, ax=ax, node_size=0, edge_color="gray", show=False, close=False)
        except Exception as e:
            warnings.warn(f"Could not overlay OSM graph on plot: {e}")

    if garbage_gdf is not None:
        try:
            garbage_gdf.plot(ax=ax, color="green", markersize=40, alpha=0.7, marker="o", label="Garbage Points")
        except Exception as e:
            warnings.warn(f"Could not plot garbage data points: {e}")

    plt.legend()
    plt.title(f"Basavanagudi (Ward {WARD_NUMBER}) with Roads and Garbage Points")
    plt.tight_layout()
    plt.show()

def main():
    try:
        gdf = load_bbmp_data()
    except Exception as e:
        print("ERROR loading boundary file:", e)
        sys.exit(1)

    try:
        ward = extract_ward(gdf)
    except Exception as e:
        print("ERROR extracting ward:", e)
        sys.exit(1)

    bounds = ward.total_bounds
    print(f"Ward bounds: minx={bounds[0]:.6f}, miny={bounds[1]:.6f}, maxx={bounds[2]:.6f}, maxy={bounds[3]:.6f}")

    G = get_street_network(ward)

    garbage_gdf = load_garbage_data()

    plot_results(ward, G, garbage_gdf)

if __name__ == "__main__":
    main()
