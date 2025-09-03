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