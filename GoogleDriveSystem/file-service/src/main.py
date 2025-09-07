from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import os
import uuid
import hashlib
from datetime import datetime
import uvicorn
import magic
import io

from database import get_db, engine
from models import FileModel, SharedFile, Base
from schemas import FileResponse, FileShare, FileList
from storage import upload_to_storage, download_from_storage, delete_from_storage
from auth import verify_auth_token

app = FastAPI(title="File Service", version="1.0.0")

Base.metadata.create_all(bind=engine)

def get_file_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def get_content_type(content: bytes) -> str:
    try:
        return magic.from_buffer(content, mime=True)
    except:
        return "application/octet-stream"

@app.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    if file.size > 10 * 1024 * 1024 * 1024:  # 10GB limit
        raise HTTPException(status_code=413, detail="File too large")
    
    content = await file.read()
    checksum = get_file_checksum(content)
    content_type = get_content_type(content) or file.content_type
    
    file_id = str(uuid.uuid4())
    storage_path = f"{user_id}/{file_id}"
    
    success = await upload_to_storage(storage_path, content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload file")
    
    db_file = FileModel(
        file_id=file_id,
        user_id=user_id,
        filename=file.filename,
        file_size=file.size,
        content_type=content_type,
        storage_path=storage_path,
        checksum=checksum
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return FileResponse(
        file_id=db_file.file_id,
        filename=db_file.filename,
        file_size=db_file.file_size,
        content_type=db_file.content_type,
        created_at=db_file.created_at,
        updated_at=db_file.updated_at,
        is_shared=db_file.is_shared
    )

@app.get("/download/{file_id}")
async def download_file(
    file_id: str,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    db_file = db.query(FileModel).filter(FileModel.file_id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user owns file or has access via sharing
    has_access = (db_file.user_id == user_id or 
                 db.query(SharedFile).filter(
                     SharedFile.file_id == file_id,
                     SharedFile.shared_with_user_id == user_id
                 ).first() is not None)
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    content = await download_from_storage(db_file.storage_path)
    if not content:
        raise HTTPException(status_code=500, detail="Failed to download file")
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type=db_file.content_type,
        headers={"Content-Disposition": f"attachment; filename={db_file.filename}"}
    )

@app.get("/files", response_model=FileList)
async def list_files(
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    files = db.query(FileModel).filter(FileModel.user_id == user_id).all()
    shared_files = db.query(FileModel).join(
        SharedFile, FileModel.file_id == SharedFile.file_id
    ).filter(SharedFile.shared_with_user_id == user_id).all()
    
    all_files = files + shared_files
    file_responses = [
        FileResponse(
            file_id=f.file_id,
            filename=f.filename,
            file_size=f.file_size,
            content_type=f.content_type,
            created_at=f.created_at,
            updated_at=f.updated_at,
            is_shared=f.is_shared
        ) for f in all_files
    ]
    
    return FileList(files=file_responses, total=len(file_responses))

@app.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    db_file = db.query(FileModel).filter(
        FileModel.file_id == file_id,
        FileModel.user_id == user_id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    success = await delete_from_storage(db_file.storage_path)
    if success:
        db.delete(db_file)
        db.commit()
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete file")

@app.put("/files/{file_id}")
async def rename_file(
    file_id: str,
    filename: str,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    db_file = db.query(FileModel).filter(
        FileModel.file_id == file_id,
        FileModel.user_id == user_id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    db_file.filename = filename
    db_file.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "File renamed successfully"}

@app.post("/files/{file_id}/share")
async def share_file(
    file_id: str,
    share_data: FileShare,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    db_file = db.query(FileModel).filter(
        FileModel.file_id == file_id,
        FileModel.user_id == user_id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    existing_share = db.query(SharedFile).filter(
        SharedFile.file_id == file_id,
        SharedFile.shared_with_user_id == share_data.shared_with_user_id
    ).first()
    
    if existing_share:
        raise HTTPException(status_code=400, detail="File already shared with this user")
    
    shared_file = SharedFile(
        file_id=file_id,
        shared_with_user_id=share_data.shared_with_user_id,
        permission=share_data.permission
    )
    db.add(shared_file)
    
    db_file.is_shared = True
    db.commit()
    
    return {"message": "File shared successfully"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "file-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9002)
