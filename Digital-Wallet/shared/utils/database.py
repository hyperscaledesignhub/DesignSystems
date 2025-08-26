import asyncpg
import os
from typing import Optional

class DatabasePool:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def create_pool(self, database_url: str):
        self.pool = await asyncpg.create_pool(database_url)
    
    async def close_pool(self):
        if self.pool:
            await self.pool.close()
    
    async def execute(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

db_pool = DatabasePool()

def get_database_url(service_name: str) -> str:
    # Convert service-name to SERVICE_NAME for env vars
    env_prefix = service_name.upper().replace("-", "_")
    host = os.getenv(f"{env_prefix}_DB_HOST", "localhost")
    port = os.getenv(f"{env_prefix}_DB_PORT", "5432")
    user = os.getenv(f"{env_prefix}_DB_USER", "postgres")
    password = os.getenv(f"{env_prefix}_DB_PASSWORD", "password")
    database = os.getenv(f"{env_prefix}_DB_NAME", service_name.replace("-", "_"))
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"