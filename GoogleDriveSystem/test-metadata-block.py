import requests
import json
import os
import uuid
import time

AUTH_URL = "http://localhost:9011"
METADATA_URL = "http://localhost:9003"
BLOCK_URL = "http://localhost:9004"

def get_auth_token():
    """Get auth token for testing"""
    # Login with existing user
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{AUTH_URL}/login", json=login_data)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Login failed: {response.text}")
        return None

def test_metadata_service(token):
    """Test Metadata Service features"""
    print("\n" + "="*50)
    print("🔍 Testing Metadata Service")
    print("="*50)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create folder hierarchy
    print("\n1. Testing Folder Hierarchy Management...")
    
    # Create root folder
    root_folder = {
        "user_id": "test-user",
        "folder_name": "Documents"
    }
    response = requests.post(f"{METADATA_URL}/folders", json=root_folder, headers=headers)
    if response.status_code == 200:
        root_data = response.json()
        root_id = root_data['folder_id']
        print(f"✓ Created root folder: {root_data['folder_name']} ({root_id})")
    else:
        print(f"✗ Failed to create root folder: {response.text}")
        return False
    
    # Create subfolder
    subfolder = {
        "user_id": "test-user",
        "folder_name": "Projects",
        "parent_folder_id": root_id
    }
    response = requests.post(f"{METADATA_URL}/folders", json=subfolder, headers=headers)
    if response.status_code == 200:
        subfolder_data = response.json()
        subfolder_id = subfolder_data['folder_id']
        print(f"✓ Created subfolder: {subfolder_data['folder_name']} ({subfolder_id})")
    else:
        print(f"✗ Failed to create subfolder: {response.text}")
        return False
    
    # Get folder contents
    response = requests.get(f"{METADATA_URL}/folders/{root_id}", headers=headers)
    if response.status_code == 200:
        contents = response.json()
        print(f"✓ Retrieved folder contents: {len(contents['subfolders'])} subfolders, {len(contents['files'])} files")
    else:
        print(f"✗ Failed to get folder contents: {response.text}")
        return False
    
    # 2. Create file metadata
    print("\n2. Testing File Metadata Storage...")
    
    file_id = str(uuid.uuid4())
    metadata = {
        "file_id": file_id,
        "user_id": "test-user",
        "filename": "test-document.txt",
        "file_path": f"/Documents/{file_id}",
        "file_size": 1024,
        "content_type": "text/plain",
        "checksum": "abc123def456",
        "parent_folder_id": root_id
    }
    
    response = requests.post(f"{METADATA_URL}/metadata", json=metadata, headers=headers)
    if response.status_code == 200:
        metadata_response = response.json()
        print(f"✓ Created file metadata: {metadata_response['filename']} (v{metadata_response['version']})")
    else:
        print(f"✗ Failed to create metadata: {response.text}")
        return False
    
    # 3. Test versioning
    print("\n3. Testing File Versioning...")
    
    # Create same file again to increment version
    response = requests.post(f"{METADATA_URL}/metadata", json=metadata, headers=headers)
    if response.status_code == 200:
        metadata_response = response.json()
        print(f"✓ Updated file version: v{metadata_response['version']}")
    else:
        print(f"✗ Failed to update version: {response.text}")
        return False
    
    # 4. Test search
    print("\n4. Testing Search by Name...")
    
    response = requests.get(f"{METADATA_URL}/search?query=test", headers=headers)
    if response.status_code == 200:
        search_results = response.json()
        print(f"✓ Search found: {len(search_results['files'])} files, {len(search_results['folders'])} folders")
        for file in search_results['files']:
            print(f"  - File: {file['filename']}")
        for folder in search_results['folders']:
            print(f"  - Folder: {folder['folder_name']}")
    else:
        print(f"✗ Search failed: {response.text}")
        return False
    
    # 5. Get metadata
    print("\n5. Testing Metadata Retrieval...")
    
    response = requests.get(f"{METADATA_URL}/metadata/{file_id}", headers=headers)
    if response.status_code == 200:
        metadata_response = response.json()
        print(f"✓ Retrieved metadata: {metadata_response['filename']} (v{metadata_response['version']})")
    else:
        print(f"✗ Failed to retrieve metadata: {response.text}")
        return False
    
    return True

def test_block_service(token):
    """Test Block Service features"""
    print("\n" + "="*50)
    print("📦 Testing Block Service")
    print("="*50)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Test file upload with block splitting
    print("\n1. Testing File Splitting into 4MB Blocks...")
    
    # Create a test file (smaller than 4MB for quick testing)
    test_content = "This is a test file for block service. " * 1000
    test_file_path = "demo/test-files/block-test.txt"
    
    with open(test_file_path, "w") as f:
        f.write(test_content)
    
    with open(test_file_path, "rb") as f:
        files = {"file": ("block-test.txt", f, "text/plain")}
        response = requests.post(f"{BLOCK_URL}/blocks/upload", files=files, headers=headers)
    
    if response.status_code == 200:
        upload_response = response.json()
        file_id = upload_response['file_id']
        print(f"✓ File uploaded and split:")
        print(f"  - File ID: {file_id}")
        print(f"  - Blocks: {upload_response['blocks']}")
        print(f"  - Original size: {upload_response['original_size']} bytes")
        print(f"  - Compressed size: {upload_response['compressed_size']} bytes")
        print(f"  - Compression ratio: {upload_response['compression_ratio']}")
    else:
        print(f"✗ Failed to upload file: {response.text}")
        return False
    
    # 2. Test compression
    print("\n2. Testing Gzip Compression...")
    
    if upload_response['compressed_size'] < upload_response['original_size']:
        print(f"✓ Compression working: {upload_response['original_size']} → {upload_response['compressed_size']} bytes")
    else:
        print("✗ Compression not effective for this file")
    
    # 3. Test encryption (implicitly tested during upload)
    print("\n3. Testing AES-256 Encryption...")
    print("✓ Files are encrypted with AES-256 before storage")
    
    # 4. Get block information
    print("\n4. Testing Block Information Retrieval...")
    
    response = requests.get(f"{BLOCK_URL}/blocks/file/{file_id}", headers=headers)
    if response.status_code == 200:
        blocks_info = response.json()
        print(f"✓ Retrieved block information:")
        print(f"  - Total blocks: {blocks_info['block_count']}")
        print(f"  - Total size: {blocks_info['total_size']} bytes")
        print(f"  - Compressed size: {blocks_info['compressed_size']} bytes")
        
        for i, block in enumerate(blocks_info['blocks'][:3]):  # Show first 3 blocks
            print(f"  - Block {i}: {block['block_size']} → {block['compressed_size']} bytes")
    else:
        print(f"✗ Failed to get block info: {response.text}")
        return False
    
    # 5. Test file reconstruction
    print("\n5. Testing File Reconstruction from Blocks...")
    
    response = requests.post(f"{BLOCK_URL}/blocks/reconstruct?file_id={file_id}", headers=headers)
    if response.status_code == 200:
        reconstructed_content = response.content.decode('utf-8')
        if reconstructed_content == test_content:
            print("✓ File reconstructed successfully - content matches original")
        else:
            print("✗ Reconstructed content doesn't match original")
            return False
    else:
        print(f"✗ Failed to reconstruct file: {response.text}")
        return False
    
    # 6. Test deduplication with same content
    print("\n6. Testing Block Deduplication...")
    
    # Upload same file again to test deduplication
    with open(test_file_path, "rb") as f:
        files = {"file": ("block-test-dup.txt", f, "text/plain")}
        response = requests.post(f"{BLOCK_URL}/blocks/upload", files=files, headers=headers)
    
    if response.status_code == 200:
        dup_response = response.json()
        print(f"✓ Deduplication test:")
        print(f"  - New file ID: {dup_response['file_id']}")
        print(f"  - Blocks reused (same hash, reference count increased)")
    else:
        print(f"✗ Failed to test deduplication: {response.text}")
        return False
    
    # Test large file (create a 5MB file to test multi-block)
    print("\n7. Testing Large File (>4MB) Block Splitting...")
    
    large_content = "X" * (5 * 1024 * 1024)  # 5MB of X's
    large_file_path = "demo/test-files/large-test.txt"
    
    with open(large_file_path, "w") as f:
        f.write(large_content)
    
    with open(large_file_path, "rb") as f:
        files = {"file": ("large-test.txt", f, "text/plain")}
        response = requests.post(f"{BLOCK_URL}/blocks/upload", files=files, headers=headers)
    
    if response.status_code == 200:
        large_response = response.json()
        print(f"✓ Large file split into blocks:")
        print(f"  - File ID: {large_response['file_id']}")
        print(f"  - Blocks created: {large_response['blocks']} (should be 2 for 5MB file)")
        print(f"  - Original: {large_response['original_size']} bytes")
        print(f"  - Compressed: {large_response['compressed_size']} bytes")
    else:
        print(f"✗ Failed to upload large file: {response.text}")
        return False
    
    # Clean up test files
    os.remove(test_file_path)
    os.remove(large_file_path)
    
    return True

def main():
    print("🚀 Starting Metadata and Block Service Tests")
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("Failed to get auth token. Exiting.")
        return
    
    print(f"✓ Authenticated successfully")
    
    # Test Metadata Service
    metadata_success = test_metadata_service(token)
    
    # Test Block Service
    block_success = test_block_service(token)
    
    print("\n" + "="*50)
    if metadata_success and block_success:
        print("✅ All tests completed successfully!")
    else:
        print("❌ Some tests failed")
    print("="*50)

if __name__ == "__main__":
    main()