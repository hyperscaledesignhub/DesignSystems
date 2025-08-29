import os
import asyncpg
from typing import Optional
from contextlib import asynccontextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://emailuser:emailpass@postgres:5432/emaildb")

class DatabasePool:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
    
    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    @asynccontextmanager
    async def acquire(self):
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args):
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

db_pool = DatabasePool()

async def init_database():
    """Initialize database tables"""
    await db_pool.connect()
    
    queries = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            is_active BOOLEAN DEFAULT true,
            storage_used BIGINT DEFAULT 0,
            storage_limit BIGINT DEFAULT 5368709120,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS emails (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            from_email VARCHAR(255) NOT NULL,
            to_recipients TEXT[] NOT NULL,
            cc_recipients TEXT[] DEFAULT '{}',
            bcc_recipients TEXT[] DEFAULT '{}',
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            html_body TEXT,
            status VARCHAR(50) DEFAULT 'received',
            priority VARCHAR(50) DEFAULT 'normal',
            is_read BOOLEAN DEFAULT false,
            is_starred BOOLEAN DEFAULT false,
            spam_score FLOAT DEFAULT 0.0,
            labels TEXT[] DEFAULT '{}',
            folder VARCHAR(100) DEFAULT 'inbox',
            thread_id UUID,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP,
            scheduled_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS attachments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email_id UUID REFERENCES emails(id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            content_type VARCHAR(100),
            size BIGINT NOT NULL,
            s3_key VARCHAR(500),
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            data JSONB DEFAULT '{}',
            is_read BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS folders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            parent_id UUID REFERENCES folders(id) ON DELETE CASCADE,
            color VARCHAR(7),
            icon VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name, parent_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS filter_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            conditions JSONB NOT NULL,
            actions JSONB NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_emails_user_id ON emails(user_id);
        CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status);
        CREATE INDEX IF NOT EXISTS idx_emails_created_at ON emails(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);
        CREATE INDEX IF NOT EXISTS idx_attachments_email_id ON attachments(email_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
        CREATE INDEX IF NOT EXISTS idx_folders_user_id ON folders(user_id);
        """
    ]
    
    for query in queries:
        await db_pool.execute(query)
    
    print("Database tables initialized successfully")