from sqlalchemy import Column, String, BigInteger, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class FileModel(Base):
    __tablename__ = "files"
    
    file_id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    filename = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    content_type = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    checksum = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    is_shared = Column(Boolean, default=False)

class SharedFile(Base):
    __tablename__ = "shared_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(String, nullable=False)
    shared_with_user_id = Column(String, nullable=False)
    permission = Column(String, nullable=False, default="read")
    shared_at = Column(DateTime, default=datetime.utcnow)