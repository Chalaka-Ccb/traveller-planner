# app/services/ors_service.py
import math
from typing import List, Tuple, Dict, Optional
import openrouteservice
from app.config import ORS_API_KEY

# lazy ORS client
_client = None
def get_client():
    global _client
    if _client is None and ORS_API_KEY:
        try:
            _client = openrouteservice.Client(key=ORS_API_KEY)
        except Exception as e:
            print(f"[ORS] client init failed: {e}")
            _client = None
    return _client

# --- helpers ---

def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    val = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(val))

def estimate_duration_seconds(distance_km: float, speed_kmph: float = 40.0) -> int:
    if distance_km <= 0:
        return 0
    return int((distance_km / speed_kmph) * 3600)

def _coords_row_to_latlon(row: Dict) -> Tuple[float, float]:
    """
    Try to pull (lat, lon) from a dataset row.
    Supports:
     - row['coords'] = (lon, lat)
     - row['Latitude'], row['Longitude']
    """
    if "coords" in row and row["coords"]:
        try:
            c0, c1 = row["coords"]
            if abs(c0) > 90:  # heuristic: lon first
                lon, lat = c0, c1
            else:
                lat, lon = c0, c1
            return (float(lat), float(lon))
        except Exception:
            pass
    lat = row.get("Latitude") or row.get("Lat") or row.get("lat")
    lon = row.get("Longitude") or row.get("Lon") or row.get("lng") or row.get("Lng")
    if lat and lon:
        return (float(lat), float(lon))
    return (0.0, 0.0)

def get_leg_duration_ors(a: Tuple[float, float], b: Tuple[float, float]) -> Optional[int]:
    client = get_client()
    if not client:
        return None
    try:
        coords = [(a[1], a[0]), (b[1], b[0])]  # ORS wants (lon, lat)
        route = client.directions(coords, profile="driving-car", format="geojson")
        summary = route["features"][0]["properties"]["summary"]
        return int(summary.get("duration", 0))
    except Exception as e:
        print(f"[ORS] directions failed: {e}")
        return None

# --- main optimizer ---

def optimize_route(coords_latlon: List[Tuple[float, float]], start_index: int = 0) -> Tuple[List[int], int]:
    """
    Greedy nearest-neighbor TSP ordering.
    Returns (order indices, total travel duration seconds).
    Uses ORS per-leg if available; fallback to haversine estimate.
    """
    n = len(coords_latlon)
    if n <= 1:
        return list(range(n)), 0

    # distance matrix (km)
    dist_km = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1, n):
            d = haversine_km(coords_latlon[i], coords_latlon[j])
            dist_km[i][j] = d
            dist_km[j][i] = d

    visited = [False]*n
    order = [start_index]
    visited[start_index] = True
    current = start_index

    while len(order) < n:
        nearest = None
        bestd = float("inf")
        for j in range(n):
            if not visited[j] and dist_km[current][j] < bestd:
                bestd = dist_km[current][j]
                nearest = j
        if nearest is None:
            break
        order.append(nearest)
        visited[nearest] = True
        current = nearest

    total_seconds = 0
    for i in range(len(order)-1):
        a = coords_latlon[order[i]]
        b = coords_latlon[order[i+1]]
        dur = get_leg_duration_ors(a, b)
        if dur is None:
            dur = estimate_duration_seconds(dist_km[order[i]][order[i+1]])
        total_seconds += dur

    return order, total_seconds
