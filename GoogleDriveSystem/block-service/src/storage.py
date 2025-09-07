from minio import Minio
from minio.error import S3Error
import os
import io

client = Minio(
    os.getenv("STORAGE_ENDPOINT", "localhost:9000"),
    access_key=os.getenv("STORAGE_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("STORAGE_SECRET_KEY", "minioadmin"),
    secure=False
)

BUCKET_NAME = os.getenv("STORAGE_BUCKET", "blocks")

def ensure_bucket_exists():
    try:
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
    except S3Error as e:
        print(f"Error creating bucket: {e}")

ensure_bucket_exists()

async def upload_block(object_name: str, data: bytes) -> bool:
    try:
        client.put_object(
            BUCKET_NAME,
            object_name,
            io.BytesIO(data),
            length=len(data)
        )
        return True
    except S3Error as e:
        print(f"Error uploading block: {e}")
        return False

async def download_block(object_name: str) -> bytes:
    try:
        response = client.get_object(BUCKET_NAME, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        print(f"Error downloading block: {e}")
        return None

async def delete_block(object_name: str) -> bool:
    try:
        client.remove_object(BUCKET_NAME, object_name)
        return True
    except S3Error as e:
        print(f"Error deleting block: {e}")
        return False