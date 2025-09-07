from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

class BlockUpload(BaseModel):
    file_id: str
    block_order: int
    data: bytes

class BlockInfo(BaseModel):
    block_id: uuid.UUID
    file_id: str
    block_hash: str
    block_order: int
    block_size: int
    compressed_size: int
    storage_path: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class FileBlocksResponse(BaseModel):
    file_id: str
    blocks: List[BlockInfo]
    total_size: int
    compressed_size: int
    block_count: int

class ReconstructRequest(BaseModel):
    file_id: str

class ReconstructResponse(BaseModel):
    file_id: str
    data: bytes
    original_size: int
    compressed_size: int