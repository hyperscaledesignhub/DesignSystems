import math
from typing import List, Tuple

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

def encode(latitude: float, longitude: float, precision: int = 6) -> str:
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    
    geohash = []
    is_lon = True
    
    while len(geohash) < precision:
        val = 0
        for bit in range(5):
            if is_lon:
                mid = (lon_min + lon_max) / 2
                if longitude > mid:
                    val |= (1 << (4 - bit))
                    lon_min = mid
                else:
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2
                if latitude > mid:
                    val |= (1 << (4 - bit))
                    lat_min = mid
                else:
                    lat_max = mid
            is_lon = not is_lon
        geohash.append(BASE32[val])
    
    return ''.join(geohash)

def get_neighbors(geohash: str) -> List[str]:
    neighbors = []
    
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    
    is_lon = True
    for char in geohash:
        idx = BASE32.index(char)
        for bit in range(5):
            if is_lon:
                mid = (lon_min + lon_max) / 2
                if idx & (1 << (4 - bit)):
                    lon_min = mid
                else:
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2
                if idx & (1 << (4 - bit)):
                    lat_min = mid
                else:
                    lat_max = mid
            is_lon = not is_lon
    
    lat_center = (lat_min + lat_max) / 2
    lon_center = (lon_min + lon_max) / 2
    lat_delta = (lat_max - lat_min) / 2
    lon_delta = (lon_max - lon_min) / 2
    
    neighbor_coords = [
        (lat_center + lat_delta, lon_center),
        (lat_center - lat_delta, lon_center),
        (lat_center, lon_center + lon_delta),
        (lat_center, lon_center - lon_delta),
        (lat_center + lat_delta, lon_center + lon_delta),
        (lat_center + lat_delta, lon_center - lon_delta),
        (lat_center - lat_delta, lon_center + lon_delta),
        (lat_center - lat_delta, lon_center - lon_delta)
    ]
    
    for lat, lon in neighbor_coords:
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            neighbors.append(encode(lat, lon, len(geohash)))
    
    return neighbors

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c