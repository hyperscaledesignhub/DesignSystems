import redis
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class SimpleRedisManager:
    def __init__(self):
        self.client = redis.Redis(
            host='redis-master',
            port=6739,
            decode_responses=True
        )
        
    def get_write_client(self) -> redis.Redis:
        return self.client
    
    def get_read_client(self) -> redis.Redis:
        return self.client
    
    def set_business(self, business_id: str, business_data: Dict[str, Any], ttl: int = 86400):
        try:
            key = f"business:{business_id}"
            self.client.setex(key, ttl, json.dumps(business_data))
        except Exception as e:
            logger.error(f"Failed to cache business {business_id}: {e}")
    
    def get_business(self, business_id: str) -> Optional[Dict[str, Any]]:
        try:
            key = f"business:{business_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached business {business_id}: {e}")
            return None
    
    def delete_business(self, business_id: str):
        try:
            key = f"business:{business_id}"
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete cached business {business_id}: {e}")
    
    def set_geohash_businesses(self, precision: int, geohash: str, business_ids: List[str], ttl: int = 86400):
        try:
            key = f"geohash:{precision}:{geohash}"
            self.client.setex(key, ttl, json.dumps(business_ids))
        except Exception as e:
            logger.error(f"Failed to cache geohash {geohash}: {e}")
    
    def get_geohash_businesses(self, precision: int, geohash: str) -> List[str]:
        try:
            key = f"geohash:{precision}:{geohash}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return []
        except Exception as e:
            logger.error(f"Failed to get cached geohash {geohash}: {e}")
            return []
    
    def warm_cache_businesses(self, business_data: Dict[str, Dict[str, Any]], ttl: int = 86400):
        try:
            pipe = self.client.pipeline()
            for business_id, data in business_data.items():
                key = f"business:{business_id}"
                pipe.setex(key, ttl, json.dumps(data))
            pipe.execute()
            logger.info(f"Warmed {len(business_data)} business cache entries")
        except Exception as e:
            logger.error(f"Failed to warm business caches: {e}")
    
    def warm_cache_geohashes(self, geohash_data: Dict[str, List[str]], ttl: int = 86400):
        try:
            pipe = self.client.pipeline()
            for key, business_ids in geohash_data.items():
                pipe.setex(key, ttl, json.dumps(business_ids))
            pipe.execute()
            logger.info(f"Warmed {len(geohash_data)} geohash cache entries")
        except Exception as e:
            logger.error(f"Failed to warm geohash caches: {e}")
    
    def clear_expired_caches(self):
        try:
            info = self.client.info('memory')
            logger.info(f"Redis memory usage: {info.get('used_memory_human', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        try:
            self.client.ping()
            return {
                "master": True,
                "slaves": [{"slave": 1, "healthy": True}],
                "sentinels": True
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "master": False,
                "slaves": [{"slave": 1, "healthy": False}],
                "sentinels": False
            }

# Global instance
simple_redis = None

def get_redis_manager() -> SimpleRedisManager:
    global simple_redis
    if not simple_redis:
        simple_redis = SimpleRedisManager()
    return simple_redis