import asyncpg
import asyncio
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    is_primary: bool = True

class DatabasePool:
    def __init__(self, primary_config: DatabaseConfig, replica_configs: List[DatabaseConfig]):
        self.primary_config = primary_config
        self.replica_configs = replica_configs
        self.primary_pool: Optional[asyncpg.Pool] = None
        self.replica_pools: List[asyncpg.Pool] = []
        self.current_replica_index = 0
        self.promoted_primary_pool: Optional[asyncpg.Pool] = None
        self.promoted_primary_config: Optional[DatabaseConfig] = None
        
    async def initialize(self):
        """Initialize database connections"""
        try:
            # Initialize primary connection
            self.primary_pool = await asyncpg.create_pool(
                host=self.primary_config.host,
                port=self.primary_config.port,
                database=self.primary_config.database,
                user=self.primary_config.user,
                password=self.primary_config.password,
                min_size=5,
                max_size=10
            )
            logger.info("Primary database pool initialized")
            
            # Initialize replica connections
            for i, replica_config in enumerate(self.replica_configs):
                try:
                    replica_pool = await asyncpg.create_pool(
                        host=replica_config.host,
                        port=replica_config.port,
                        database=replica_config.database,
                        user=replica_config.user,
                        password=replica_config.password,
                        min_size=3,
                        max_size=8
                    )
                    self.replica_pools.append(replica_pool)
                    logger.info(f"Replica {i+1} database pool initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize replica {i+1}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize primary database pool: {e}")
            raise
            
    async def get_write_connection(self):
        """Get connection for write operations with failover"""
        # Try original primary first
        if self.primary_pool:
            try:
                async with self.primary_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                return self.primary_pool.acquire()
            except Exception as e:
                logger.warning(f"Primary database unavailable, attempting failover: {e}")
        
        # Try promoted primary if available
        if self.promoted_primary_pool:
            try:
                async with self.promoted_primary_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                return self.promoted_primary_pool.acquire()
            except Exception as e:
                logger.warning(f"Promoted primary unavailable: {e}")
                
        # Attempt to promote a replica to primary
        for i, replica_pool in enumerate(self.replica_pools):
            try:
                async with replica_pool.acquire() as conn:
                    # Check if replica can accept writes (not in recovery mode)
                    in_recovery = await conn.fetchval("SELECT pg_is_in_recovery()")
                    if not in_recovery:
                        logger.info(f"Using replica {i+1} as promoted primary for writes")
                        self.promoted_primary_pool = replica_pool
                        self.promoted_primary_config = self.replica_configs[i]
                        return replica_pool.acquire()
                    else:
                        logger.info(f"Replica {i+1} is still in recovery mode")
            except Exception as e:
                logger.warning(f"Failed to check replica {i+1} for promotion: {e}")
                continue
        
        raise Exception("No available database for write operations")
        
    async def get_read_connection(self):
        """Get connection for read operations (replica preferred, fallback to primary)"""
        # Try to use replica if available
        if self.replica_pools:
            try:
                # Round-robin selection of replicas
                replica_pool = self.replica_pools[self.current_replica_index]
                self.current_replica_index = (self.current_replica_index + 1) % len(self.replica_pools)
                return replica_pool.acquire()
            except Exception as e:
                logger.warning(f"Failed to get replica connection, falling back to primary: {e}")
        
        # Fallback to primary or promoted primary
        if self.primary_pool:
            try:
                return self.primary_pool.acquire()
            except Exception as e:
                logger.warning(f"Primary unavailable for read fallback: {e}")
        
        if self.promoted_primary_pool:
            try:
                return self.promoted_primary_pool.acquire()
            except Exception as e:
                logger.warning(f"Promoted primary unavailable for read fallback: {e}")
                
        raise Exception("No database pools available for read operations")
        
    async def check_health(self):
        """Check health of all database connections"""
        health_status = {
            "primary": False,
            "promoted_primary": False,
            "replicas": []
        }
        
        # Check primary
        try:
            async with self.primary_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["primary"] = True
        except Exception as e:
            logger.error(f"Primary database health check failed: {e}")
        
        # Check promoted primary
        if self.promoted_primary_pool:
            try:
                async with self.promoted_primary_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                health_status["promoted_primary"] = True
            except Exception as e:
                logger.error(f"Promoted primary health check failed: {e}")
            
        # Check replicas
        for i, replica_pool in enumerate(self.replica_pools):
            try:
                async with replica_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                health_status["replicas"].append({"replica": i+1, "healthy": True})
            except Exception as e:
                logger.error(f"Replica {i+1} health check failed: {e}")
                health_status["replicas"].append({"replica": i+1, "healthy": False})
                
        return health_status
        
    async def close(self):
        """Close all database connections"""
        if self.primary_pool:
            await self.primary_pool.close()
            
        for replica_pool in self.replica_pools:
            await replica_pool.close()
            
        logger.info("All database pools closed")

# Global database pool instance
db_pool: Optional[DatabasePool] = None

async def initialize_database_pools():
    """Initialize the global database pool"""
    global db_pool
    
    primary_config = DatabaseConfig(
        host="postgres-primary",
        port=5832,
        database="proximity_db",
        user="postgres",
        password="password",
        is_primary=True
    )
    
    replica_configs = [
        DatabaseConfig(
            host="postgres-replica1",
            port=5833,
            database="proximity_db",
            user="postgres",
            password="password",
            is_primary=False
        ),
        DatabaseConfig(
            host="postgres-replica2",
            port=5834,
            database="proximity_db",
            user="postgres",
            password="password",
            is_primary=False
        )
    ]
    
    db_pool = DatabasePool(primary_config, replica_configs)
    await db_pool.initialize()
    
async def get_database_pool() -> DatabasePool:
    """Get the global database pool"""
    if not db_pool:
        raise Exception("Database pool not initialized")
    return db_pool