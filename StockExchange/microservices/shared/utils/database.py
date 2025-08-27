import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import redis.asyncio as redis

Base = declarative_base()

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url)
        self.SessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            class_=AsyncSession
        )
    
    async def get_session(self):
        async with self.SessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

class RedisManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._pool = None
    
    async def get_redis(self):
        if not self._pool:
            self._pool = redis.ConnectionPool.from_url(self.redis_url)
        return redis.Redis(connection_pool=self._pool)
    
    async def close(self):
        if self._pool:
            await self._pool.disconnect()

# Database URLs
def get_database_url(service_name: str) -> str:
    return os.getenv(
        f"{service_name.upper()}_DATABASE_URL",
        f"postgresql+asyncpg://postgres:postgres@localhost:5432/{service_name}"
    )

def get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379")