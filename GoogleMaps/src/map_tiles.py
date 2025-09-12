"""
Map Tile Service for serving and managing map tiles
Handles vector and raster tiles with multiple zoom levels
"""

import logging
import os
import json
from typing import Optional, Dict, Tuple, List
from enum import Enum
from dataclasses import dataclass
import asyncio
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

class TileFormat(Enum):
    VECTOR = "vector"  # MVT format
    RASTER = "raster"  # PNG format
    
@dataclass
class TileMetadata:
    """Metadata for a map tile"""
    z: int  # Zoom level
    x: int  # Tile X coordinate
    y: int  # Tile Y coordinate
    format: TileFormat
    style: str
    size_bytes: int
    last_modified: str

class MapTileService:
    """Service for managing and serving map tiles"""
    
    def __init__(self, tile_storage_path: str, cache_enabled: bool = True):
        self.storage_path = Path(tile_storage_path)
        self.cache_enabled = cache_enabled
        self.tile_cache: Dict[str, bytes] = {}
        self.max_cache_size = 100 * 1024 * 1024  # 100MB cache
        self.current_cache_size = 0
        
        # Create storage directories
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Tile styles
        self.styles = {
            "default": {"name": "Default", "version": "1.0"},
            "satellite": {"name": "Satellite", "version": "1.0"},
            "terrain": {"name": "Terrain", "version": "1.0"},
            "dark": {"name": "Dark Mode", "version": "1.0"}
        }
        
    async def get_tile(
        self,
        z: int,
        x: int,
        y: int,
        style: str = "default",
        format: TileFormat = TileFormat.VECTOR
    ) -> Optional[bytes]:
        """Get a map tile"""
        try:
            # Validate zoom level
            if z < 0 or z > 20:
                return None
            
            # Validate tile coordinates
            max_tile = 2 ** z
            if x < 0 or x >= max_tile or y < 0 or y >= max_tile:
                return None
            
            # Check cache first
            cache_key = self._get_cache_key(z, x, y, style, format)
            if self.cache_enabled and cache_key in self.tile_cache:
                logger.debug(f"Tile cache hit: {cache_key}")
                return self.tile_cache[cache_key]
            
            # Load from storage
            tile_path = self._get_tile_path(z, x, y, style, format)
            
            if tile_path.exists():
                with open(tile_path, 'rb') as f:
                    tile_data = f.read()
                
                # Add to cache
                if self.cache_enabled:
                    await self._add_to_cache(cache_key, tile_data)
                
                return tile_data
            else:
                # Generate tile on demand (simplified)
                tile_data = await self._generate_tile(z, x, y, style, format)
                
                # Save to storage
                await self._save_tile(tile_path, tile_data)
                
                # Add to cache
                if self.cache_enabled:
                    await self._add_to_cache(cache_key, tile_data)
                
                return tile_data
                
        except Exception as e:
            logger.error(f"Error getting tile {z}/{x}/{y}: {e}")
            return None
    
    def _get_cache_key(
        self,
        z: int,
        x: int,
        y: int,
        style: str,
        format: TileFormat
    ) -> str:
        """Generate cache key for a tile"""
        return f"{style}:{format.value}:{z}:{x}:{y}"
    
    def _get_tile_path(
        self,
        z: int,
        x: int,
        y: int,
        style: str,
        format: TileFormat
    ) -> Path:
        """Get file path for a tile"""
        ext = "mvt" if format == TileFormat.VECTOR else "png"
        return self.storage_path / style / str(z) / str(x) / f"{y}.{ext}"
    
    async def _generate_tile(
        self,
        z: int,
        x: int,
        y: int,
        style: str,
        format: TileFormat
    ) -> bytes:
        """Generate a tile (simplified mock implementation)"""
        # In production, this would:
        # 1. Query spatial database for features in tile bounds
        # 2. Render features according to style
        # 3. Encode as MVT (vector) or render as PNG (raster)
        
        if format == TileFormat.VECTOR:
            # Mock vector tile data
            tile_data = {
                "layers": [
                    {
                        "name": "roads",
                        "features": [
                            {"id": 1, "type": "LineString", "properties": {"name": "Main St"}}
                        ]
                    },
                    {
                        "name": "buildings",
                        "features": [
                            {"id": 1, "type": "Polygon", "properties": {"height": 10}}
                        ]
                    }
                ]
            }
            return json.dumps(tile_data).encode('utf-8')
        else:
            # Mock raster tile (empty PNG)
            # In production, render actual map image
            import base64
            # 1x1 transparent PNG
            png_data = base64.b64decode(
                b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
            )
            return png_data
    
    async def _save_tile(self, tile_path: Path, tile_data: bytes):
        """Save tile to storage"""
        try:
            tile_path.parent.mkdir(parents=True, exist_ok=True)
            with open(tile_path, 'wb') as f:
                f.write(tile_data)
        except Exception as e:
            logger.error(f"Error saving tile: {e}")
    
    async def _add_to_cache(self, cache_key: str, tile_data: bytes):
        """Add tile to cache with LRU eviction"""
        tile_size = len(tile_data)
        
        # Evict old tiles if cache is full
        while self.current_cache_size + tile_size > self.max_cache_size:
            if not self.tile_cache:
                break
            
            # Remove oldest tile (simplified LRU)
            oldest_key = next(iter(self.tile_cache))
            oldest_size = len(self.tile_cache[oldest_key])
            del self.tile_cache[oldest_key]
            self.current_cache_size -= oldest_size
        
        # Add new tile
        self.tile_cache[cache_key] = tile_data
        self.current_cache_size += tile_size
    
    def get_tile_bounds(self, z: int, x: int, y: int) -> Tuple[float, float, float, float]:
        """Get geographic bounds of a tile"""
        n = 2.0 ** z
        
        # Calculate bounds
        west = x / n * 360.0 - 180.0
        east = (x + 1) / n * 360.0 - 180.0
        
        lat_rad_north = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_rad_south = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
        
        north = math.degrees(lat_rad_north)
        south = math.degrees(lat_rad_south)
        
        return (north, south, east, west)
    
    def get_tiles_for_bounds(
        self,
        bounds: Tuple[float, float, float, float],
        zoom: int
    ) -> List[Tuple[int, int]]:
        """Get tile coordinates covering geographic bounds"""
        north, south, east, west = bounds
        
        # Convert bounds to tile coordinates
        x_min = self._lng_to_tile_x(west, zoom)
        x_max = self._lng_to_tile_x(east, zoom)
        y_min = self._lat_to_tile_y(north, zoom)
        y_max = self._lat_to_tile_y(south, zoom)
        
        tiles = []
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                tiles.append((x, y))
        
        return tiles
    
    def _lat_to_tile_y(self, lat: float, zoom: int) -> int:
        """Convert latitude to tile Y coordinate"""
        import math
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return y
    
    def _lng_to_tile_x(self, lng: float, zoom: int) -> int:
        """Convert longitude to tile X coordinate"""
        n = 2.0 ** zoom
        x = int((lng + 180.0) / 360.0 * n)
        return x
    
    def estimate_download_size(
        self,
        bounds: Tuple[float, float, float, float],
        min_zoom: int,
        max_zoom: int
    ) -> float:
        """Estimate download size for offline area in MB"""
        total_tiles = 0
        
        for zoom in range(min_zoom, max_zoom + 1):
            tiles = self.get_tiles_for_bounds(bounds, zoom)
            total_tiles += len(tiles)
        
        # Estimate 50KB per tile average
        size_mb = (total_tiles * 50 * 1024) / (1024 * 1024)
        return size_mb
    
    async def prepare_offline_package(
        self,
        download_id: str,
        bounds: Tuple[float, float, float, float],
        min_zoom: int,
        max_zoom: int
    ):
        """Prepare offline map package"""
        try:
            package_path = self.storage_path / "offline" / download_id
            package_path.mkdir(parents=True, exist_ok=True)
            
            tiles_downloaded = 0
            
            for zoom in range(min_zoom, max_zoom + 1):
                tiles = self.get_tiles_for_bounds(bounds, zoom)
                
                for x, y in tiles:
                    # Get or generate tile
                    tile_data = await self.get_tile(z=zoom, x=x, y=y)
                    
                    if tile_data:
                        # Save to package
                        tile_path = package_path / str(zoom) / str(x) / f"{y}.mvt"
                        await self._save_tile(tile_path, tile_data)
                        tiles_downloaded += 1
            
            # Create manifest
            manifest = {
                "download_id": download_id,
                "bounds": bounds,
                "zoom_levels": [min_zoom, max_zoom],
                "total_tiles": tiles_downloaded,
                "created_at": datetime.now().isoformat()
            }
            
            manifest_path = package_path / "manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f)
            
            logger.info(f"Offline package {download_id} prepared: {tiles_downloaded} tiles")
            
        except Exception as e:
            logger.error(f"Error preparing offline package: {e}")

import math
from datetime import datetime