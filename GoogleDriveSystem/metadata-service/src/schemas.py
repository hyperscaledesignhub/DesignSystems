from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

class MetadataCreate(BaseModel):
    file_id: str
    filename: str
    file_path: str
    file_size: int
    content_type: str
    checksum: str
    parent_folder_id: Optional[uuid.UUID] = None

class MetadataUpdate(BaseModel):
    filename: Optional[str] = None
    file_path: Optional[str] = None
    parent_folder_id: Optional[uuid.UUID] = None

class MetadataResponse(BaseModel):
    metadata_id: uuid.UUID
    file_id: str
    user_id: str
    filename: str
    file_path: str
    file_size: int
    content_type: str
    checksum: str
    version: int
    parent_folder_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class FolderCreate(BaseModel):
    folder_name: str
    parent_folder_id: Optional[uuid.UUID] = None

class FolderResponse(BaseModel):
    folder_id: uuid.UUID
    user_id: str
    folder_name: str
    parent_folder_id: Optional[uuid.UUID]
    created_at: datetime
    
    class Config:
        from_attributes = True

class FolderContents(BaseModel):
    folder: FolderResponse
    subfolders: List[FolderResponse]
    files: List[MetadataResponse]

class SearchResults(BaseModel):
    files: List[MetadataResponse]
    folders: List[FolderResponse]
    total: int