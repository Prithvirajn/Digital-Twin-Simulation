<<<<<<< HEAD
import osmnx as ox
import pandas as pd
import geopandas as gpd
import random

# Load KR Puram boundary from GeoJSON
boundary = gpd.read_file("KR_Puram.geojson")
polygon = boundary.geometry[0]

# Download the drivable road network within the polygon
print("📡 Loading K.R. Puram road network...")
G = ox.graph_from_polygon(polygon, network_type='drive')

# Ensure network has speeds and travel times
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)

# Get all node coordinates in the road network
nodes = list(G.nodes)
coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in nodes]

# Generate bins by picking random road nodes
bins = []
for i in range(30):
    lat, lon = random.choice(coords)
    bins.append({
        'id': f'Bin{i+1}',
        'lat': lat,
        'lon': lon,
        'capacity': random.randint(850, 1200),       # realistic bin capacity
        'fill': random.randint(50, 800),            # current fill
        'daily_growth': random.randint(60, 150),    # daily fill growth rate
        'last_visited_day': 0                       # initially unvisited
    })

# Save bins to CSV
bins_df = pd.DataFrame(bins)
bins_df.to_csv("bins.csv", index=False)

print("✅ Generated 30 roadside bins inside K.R. Puram (saved as 'bins.csv').")
=======
import osmnx as ox
import pandas as pd
import geopandas as gpd
import random

# Load KR Puram boundary from GeoJSON
boundary = gpd.read_file("KR_Puram.geojson")
polygon = boundary.geometry[0]

# Download the drivable road network within the polygon
print("📡 Loading K.R. Puram road network...")
G = ox.graph_from_polygon(polygon, network_type='drive')

# Ensure network has speeds and travel times
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)

# Get all node coordinates in the road network
nodes = list(G.nodes)
coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in nodes]

# Generate bins by picking random road nodes
bins = []
for i in range(30):
    lat, lon = random.choice(coords)
    bins.append({
        'id': f'Bin{i+1}',
        'lat': lat,
        'lon': lon,
        'capacity': random.randint(850, 1200),       # realistic bin capacity
        'fill': random.randint(50, 800),            # current fill
        'daily_growth': random.randint(60, 150),    # daily fill growth rate
        'last_visited_day': 0                       # initially unvisited
    })

# Save bins to CSV
bins_df = pd.DataFrame(bins)
bins_df.to_csv("bins.csv", index=False)

print("✅ Generated 30 roadside bins inside K.R. Puram (saved as 'bins.csv').")
>>>>>>> a8ee72ade03890e0735d53aa3bfabf6944a8f04f
