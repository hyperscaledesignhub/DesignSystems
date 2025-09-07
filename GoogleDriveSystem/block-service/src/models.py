from sqlalchemy import Column, String, BigInteger, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from database import Base

class FileBlock(Base):
    __tablename__ = "file_blocks"
    
    block_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(String, nullable=False, index=True)
    block_hash = Column(String, nullable=False, index=True)  # Not unique - same block can be in multiple files
    block_order = Column(Integer, nullable=False)
    block_size = Column(BigInteger, nullable=False)
    compressed_size = Column(BigInteger, nullable=False)
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class BlockDeduplication(Base):
    __tablename__ = "block_deduplication"
    
    hash = Column(String, primary_key=True)
    reference_count = Column(Integer, nullable=False, default=1)
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)