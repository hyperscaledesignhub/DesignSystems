from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import uuid
from datetime import datetime
import uvicorn

from database import get_db, engine
from models import FileMetadata, Folder, Base
from schemas import (
    MetadataCreate, MetadataUpdate, MetadataResponse,
    FolderCreate, FolderResponse, FolderContents, SearchResults
)
from auth import verify_auth_token
from cache import cache_get, cache_set, cache_delete, cache_invalidate_pattern

app = FastAPI(title="Metadata Service", version="1.0.0")

Base.metadata.create_all(bind=engine)

@app.post("/metadata", response_model=MetadataResponse)
async def create_metadata(
    metadata: MetadataCreate,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    # Check if file already has metadata
    existing = db.query(FileMetadata).filter(
        FileMetadata.file_id == metadata.file_id,
        FileMetadata.user_id == user_id
    ).first()
    
    if existing:
        # Create new version
        existing.version += 1
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        cache_delete(f"metadata:{metadata.file_id}")
        return existing
    
    # Create new metadata
    db_metadata = FileMetadata(
        file_id=metadata.file_id,
        user_id=user_id,
        filename=metadata.filename,
        file_path=metadata.file_path,
        file_size=metadata.file_size,
        content_type=metadata.content_type,
        checksum=metadata.checksum,
        parent_folder_id=metadata.parent_folder_id
    )
    
    db.add(db_metadata)
    db.commit()
    db.refresh(db_metadata)
    
    return db_metadata

@app.get("/metadata/{file_id}", response_model=MetadataResponse)
async def get_metadata(
    file_id: str,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    # Try cache first
    cache_key = f"metadata:{file_id}"
    cached = cache_get(cache_key)
    if cached:
        return MetadataResponse(**cached)
    
    metadata = db.query(FileMetadata).filter(
        FileMetadata.file_id == file_id,
        FileMetadata.user_id == user_id
    ).first()
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")
    
    response = MetadataResponse.from_orm(metadata)
    cache_set(cache_key, response.dict())
    
    return response

@app.put("/metadata/{file_id}", response_model=MetadataResponse)
async def update_metadata(
    file_id: str,
    update: MetadataUpdate,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    metadata = db.query(FileMetadata).filter(
        FileMetadata.file_id == file_id,
        FileMetadata.user_id == user_id
    ).first()
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")
    
    if update.filename:
        metadata.filename = update.filename
    if update.file_path:
        metadata.file_path = update.file_path
    if update.parent_folder_id is not None:
        metadata.parent_folder_id = update.parent_folder_id
    
    metadata.version += 1
    metadata.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(metadata)
    
    cache_delete(f"metadata:{file_id}")
    
    return metadata

@app.delete("/metadata/{file_id}")
async def delete_metadata(
    file_id: str,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    metadata = db.query(FileMetadata).filter(
        FileMetadata.file_id == file_id,
        FileMetadata.user_id == user_id
    ).first()
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")
    
    db.delete(metadata)
    db.commit()
    
    cache_delete(f"metadata:{file_id}")
    
    return {"message": "Metadata deleted successfully"}

@app.get("/search", response_model=SearchResults)
async def search_files(
    query: str = Query(..., min_length=1),
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    # Search in filenames
    files = db.query(FileMetadata).filter(
        FileMetadata.user_id == user_id,
        FileMetadata.filename.ilike(f"%{query}%")
    ).all()
    
    # Search in folder names
    folders = db.query(Folder).filter(
        Folder.user_id == user_id,
        Folder.folder_name.ilike(f"%{query}%")
    ).all()
    
    return SearchResults(
        files=[MetadataResponse.from_orm(f) for f in files],
        folders=[FolderResponse.from_orm(f) for f in folders],
        total=len(files) + len(folders)
    )

@app.post("/folders", response_model=FolderResponse)
async def create_folder(
    folder: FolderCreate,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    # Check if parent folder exists (if specified)
    if folder.parent_folder_id:
        parent = db.query(Folder).filter(
            Folder.folder_id == folder.parent_folder_id,
            Folder.user_id == user_id
        ).first()
        
        if not parent:
            raise HTTPException(status_code=404, detail="Parent folder not found")
    
    db_folder = Folder(
        user_id=user_id,
        folder_name=folder.folder_name,
        parent_folder_id=folder.parent_folder_id
    )
    
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    
    return db_folder

@app.get("/folders/{folder_id}", response_model=FolderContents)
async def get_folder_contents(
    folder_id: uuid.UUID,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    folder = db.query(Folder).filter(
        Folder.folder_id == folder_id,
        Folder.user_id == user_id
    ).first()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Get subfolders
    subfolders = db.query(Folder).filter(
        Folder.parent_folder_id == folder_id,
        Folder.user_id == user_id
    ).all()
    
    # Get files in folder
    files = db.query(FileMetadata).filter(
        FileMetadata.parent_folder_id == folder_id,
        FileMetadata.user_id == user_id
    ).all()
    
    return FolderContents(
        folder=FolderResponse.from_orm(folder),
        subfolders=[FolderResponse.from_orm(f) for f in subfolders],
        files=[MetadataResponse.from_orm(f) for f in files]
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "metadata-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)