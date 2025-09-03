import asyncpg
import json
import asyncio
import logging
from typing import Dict, List
import geohash
import sys
import os

from db_pool import initialize_database_pools, get_database_pool
from redis_manager import get_redis_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def warm_cache():
    try:
        # Get Redis manager and database pool
        redis_mgr = get_redis_manager()
        db_pool = await get_database_pool()
        
        async with await db_pool.get_read_connection() as conn:
            businesses = await conn.fetch("SELECT * FROM businesses")
        logger.info(f"Found {len(businesses)} businesses to cache")
        
        # Prepare data for bulk caching
        business_cache_data = {}
        geohash_cache_data = {}
        
        for business in businesses:
            business_data = dict(business)
            business_id = str(business_data['id'])
            
            # Format business data for caching
            business_data['id'] = business_id
            business_data['latitude'] = float(business_data['latitude'])
            business_data['longitude'] = float(business_data['longitude'])
            business_data['created_at'] = business_data['created_at'].isoformat()
            business_data['updated_at'] = business_data['updated_at'].isoformat()
            
            # Add to business cache
            business_cache_data[business_id] = business_data
            
            # Build geohash cache entries
            for precision in [4, 5, 6]:
                gh = geohash.encode(
                    float(business_data['latitude']),
                    float(business_data['longitude']),
                    precision
                )
                key = f"geohash:{precision}:{gh}"
                if key not in geohash_cache_data:
                    geohash_cache_data[key] = []
                geohash_cache_data[key].append(business_id)
        
        # Bulk cache operations with 24-hour TTL
        redis_mgr.warm_cache_businesses(business_cache_data, ttl=86400)
        redis_mgr.warm_cache_geohashes(geohash_cache_data, ttl=86400)
        
        logger.info(f"Cache warming completed. Cached {len(businesses)} businesses and {len(geohash_cache_data)} geohash entries")
    
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        raise

async def main():
    # Initialize database pools
    await initialize_database_pools()
    
    # Initial cache warming
    logger.info("Starting initial cache warming...")
    await warm_cache()
    
    # Schedule cache warming every hour
    while True:
        try:
            logger.info("Running scheduled cache warming...")
            await warm_cache()
            
            # Clean up expired entries and log memory usage
            redis_mgr = get_redis_manager()
            redis_mgr.clear_expired_caches()
            
            logger.info("Sleeping for 1 hour until next cache warming cycle...")
            await asyncio.sleep(3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            logger.info("Retrying in 60 seconds...")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())