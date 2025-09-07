from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import gzip
import io
import uuid
from typing import List
import uvicorn
import os

from database import get_db, engine
from models import FileBlock, BlockDeduplication, Base
from schemas import BlockInfo, FileBlocksResponse, ReconstructResponse
from auth import verify_auth_token
from storage import upload_block, download_block, delete_block
from crypto import encrypt_data, decrypt_data, get_hash

app = FastAPI(title="Block Service", version="1.0.0")

Base.metadata.create_all(bind=engine)

# Block size: 4MB
BLOCK_SIZE = int(os.getenv("BLOCK_SIZE", str(4 * 1024 * 1024)))

def split_into_blocks(data: bytes) -> List[bytes]:
    """Split data into blocks of BLOCK_SIZE"""
    blocks = []
    for i in range(0, len(data), BLOCK_SIZE):
        blocks.append(data[i:i + BLOCK_SIZE])
    return blocks

def compress_block(data: bytes) -> bytes:
    """Compress block using gzip"""
    return gzip.compress(data, compresslevel=6)

def decompress_block(data: bytes) -> bytes:
    """Decompress block using gzip"""
    return gzip.decompress(data)

@app.post("/blocks/upload")
async def upload_file_blocks(
    file: UploadFile = File(...),
    file_id: str = None,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """Upload file and split into blocks with compression and encryption"""
    
    # Read file content
    content = await file.read()
    
    # Generate file_id if not provided
    if not file_id:
        file_id = str(uuid.uuid4())
    
    # Split into blocks
    blocks = split_into_blocks(content)
    
    block_infos = []
    total_original = 0
    total_compressed = 0
    
    for order, block_data in enumerate(blocks):
        # Calculate hash for deduplication
        block_hash = get_hash(block_data)
        
        # Check if block already exists (deduplication)
        existing = db.query(BlockDeduplication).filter(
            BlockDeduplication.hash == block_hash
        ).first()
        
        if existing:
            # Block already exists, increment reference count
            existing.reference_count += 1
            storage_path = existing.storage_path
            compressed_size = len(await download_block(storage_path))
        else:
            # Compress block
            compressed = compress_block(block_data)
            
            # Encrypt compressed block
            encrypted, iv = encrypt_data(compressed)
            
            # Store encrypted block with IV prepended
            storage_data = iv + encrypted
            storage_path = f"{block_hash[:2]}/{block_hash}"
            
            # Upload to storage
            success = await upload_block(storage_path, storage_data)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to upload block")
            
            # Add to deduplication table
            dedup = BlockDeduplication(
                hash=block_hash,
                reference_count=1,
                storage_path=storage_path
            )
            db.add(dedup)
            
            compressed_size = len(storage_data)
        
        # Add block info
        block_info = FileBlock(
            file_id=file_id,
            block_hash=block_hash,
            block_order=order,
            block_size=len(block_data),
            compressed_size=compressed_size,
            storage_path=storage_path
        )
        db.add(block_info)
        
        block_infos.append(block_info)
        total_original += len(block_data)
        total_compressed += compressed_size
    
    db.commit()
    
    return {
        "file_id": file_id,
        "blocks": len(block_infos),
        "original_size": total_original,
        "compressed_size": total_compressed,
        "compression_ratio": f"{(1 - total_compressed/total_original) * 100:.1f}%"
    }

@app.get("/blocks/{block_id}")
async def download_block_by_id(
    block_id: uuid.UUID,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """Download a specific block"""
    
    block = db.query(FileBlock).filter(FileBlock.block_id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    
    # Download encrypted block from storage
    storage_data = await download_block(block.storage_path)
    if not storage_data:
        raise HTTPException(status_code=500, detail="Failed to download block")
    
    # Extract IV and encrypted data
    iv = storage_data[:16]
    encrypted = storage_data[16:]
    
    # Decrypt
    compressed = decrypt_data(encrypted, iv)
    
    # Decompress
    data = decompress_block(compressed)
    
    return StreamingResponse(io.BytesIO(data))

@app.post("/blocks/reconstruct")
async def reconstruct_file(
    file_id: str,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """Reconstruct file from blocks"""
    
    # Get all blocks for file in order
    blocks = db.query(FileBlock).filter(
        FileBlock.file_id == file_id
    ).order_by(FileBlock.block_order).all()
    
    if not blocks:
        raise HTTPException(status_code=404, detail="No blocks found for file")
    
    reconstructed = bytearray()
    
    for block in blocks:
        # Download encrypted block from storage
        storage_data = await download_block(block.storage_path)
        if not storage_data:
            raise HTTPException(status_code=500, detail=f"Failed to download block {block.block_id}")
        
        # Extract IV and encrypted data
        iv = storage_data[:16]
        encrypted = storage_data[16:]
        
        # Decrypt
        compressed = decrypt_data(encrypted, iv)
        
        # Decompress
        data = decompress_block(compressed)
        
        reconstructed.extend(data)
    
    return StreamingResponse(
        io.BytesIO(reconstructed),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_id}"}
    )

@app.get("/blocks/file/{file_id}", response_model=FileBlocksResponse)
async def get_file_blocks(
    file_id: str,
    user_id: str = Depends(verify_auth_token),
    db: Session = Depends(get_db)
):
    """Get all blocks info for a file"""
    
    blocks = db.query(FileBlock).filter(
        FileBlock.file_id == file_id
    ).order_by(FileBlock.block_order).all()
    
    if not blocks:
        raise HTTPException(status_code=404, detail="No blocks found for file")
    
    total_size = sum(b.block_size for b in blocks)
    compressed_size = sum(b.compressed_size for b in blocks)
    
    return FileBlocksResponse(
        file_id=file_id,
        blocks=[BlockInfo.from_orm(b) for b in blocks],
        total_size=total_size,
        compressed_size=compressed_size,
        block_count=len(blocks)
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "block-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)