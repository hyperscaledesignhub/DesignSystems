from pydantic import BaseModel
from datetime import datetime
from typing import List

class FileResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    content_type: str
    created_at: datetime
    updated_at: datetime
    is_shared: bool

class FileList(BaseModel):
    files: List[FileResponse]
    total: int

class FileShare(BaseModel):
    shared_with_user_id: str
    permission: str = "read"