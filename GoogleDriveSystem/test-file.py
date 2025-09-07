import requests
import json
import os

AUTH_URL = "http://localhost:9011"
FILE_URL = "http://localhost:9012"

def register_and_login(email, username, password):
    """Register a user and get auth token"""
    # Try to register
    user_data = {
        "email": email,
        "username": username,
        "password": password
    }
    
    response = requests.post(f"{AUTH_URL}/register", json=user_data)
    if response.status_code == 200:
        user = response.json()
        print(f"✓ User registered: {user['username']} ({user['email']})")
    elif "already registered" in response.text:
        print(f"✓ User already exists: {username}")
    else:
        print(f"Registration failed: {response.text}")
        return None
    
    # Login (works whether user was just created or already existed)
    login_data = {
        "email": email,
        "password": password
    }
    
    response = requests.post(f"{AUTH_URL}/login", json=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return None
    
    token_data = response.json()
    print(f"✓ Login successful for {username}")
    
    # Get user profile to get user_id
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    response = requests.get(f"{AUTH_URL}/profile", headers=headers)
    if response.status_code == 200:
        user = response.json()
        return user['user_id'], token_data['access_token']
    else:
        print(f"Failed to get user profile: {response.text}")
        return None

def test_file_upload(token):
    """Test file upload"""
    print("\nTesting file upload...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Upload a file
    with open("demo/test-files/sample.txt", "rb") as f:
        files = {"file": ("sample.txt", f, "text/plain")}
        response = requests.post(f"{FILE_URL}/upload", files=files, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ File uploaded successfully: {data['file_id']}")
        return data['file_id']
    else:
        print(f"✗ File upload failed: {response.text}")
        return None

def test_file_list(token):
    """Test file listing"""
    print("\nTesting file listing...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(f"{FILE_URL}/files", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Listed {data['total']} files")
        for file in data['files']:
            print(f"  - {file['filename']} ({file['file_size']} bytes)")
        return data['files']
    else:
        print(f"✗ File listing failed: {response.text}")
        return []

def test_file_download(token, file_id, expected_filename):
    """Test file download"""
    print("\nTesting file download...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(f"{FILE_URL}/download/{file_id}", headers=headers)
    if response.status_code == 200:
        print(f"✓ File downloaded successfully: {len(response.content)} bytes")
        # Check if content matches
        with open("demo/test-files/sample.txt", "rb") as f:
            original_content = f.read()
        
        if response.content == original_content:
            print("✓ Downloaded content matches original")
            return True
        else:
            print("✗ Downloaded content doesn't match original")
            return False
    else:
        print(f"✗ File download failed: {response.text}")
        return False

def test_file_rename(token, file_id, new_name):
    """Test file rename"""
    print("\nTesting file rename...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.put(f"{FILE_URL}/files/{file_id}?filename={new_name}", headers=headers)
    if response.status_code == 200:
        print(f"✓ File renamed successfully to {new_name}")
        return True
    else:
        print(f"✗ File rename failed: {response.text}")
        return False

def test_file_sharing(token1, token2, file_id, user2_id):
    """Test file sharing"""
    print("\nTesting file sharing...")
    headers1 = {
        "Authorization": f"Bearer {token1}"
    }
    headers2 = {
        "Authorization": f"Bearer {token2}"
    }
    
    # Share file from user1 to user2
    share_data = {
        "shared_with_user_id": user2_id,
        "permission": "read"
    }
    
    response = requests.post(f"{FILE_URL}/files/{file_id}/share", json=share_data, headers=headers1)
    if response.status_code == 200:
        print("✓ File shared successfully")
        
        # Check if user2 can see the shared file
        response = requests.get(f"{FILE_URL}/files", headers=headers2)
        if response.status_code == 200:
            data = response.json()
            shared_files = [f for f in data['files'] if f['file_id'] == file_id]
            if shared_files:
                print("✓ Shared file visible to recipient")
                return True
            else:
                print("✗ Shared file not visible to recipient")
                return False
        else:
            print(f"✗ Failed to check shared files: {response.text}")
            return False
    else:
        print(f"✗ File sharing failed: {response.text}")
        return False

def test_file_deletion(token, file_id):
    """Test file deletion"""
    print("\nTesting file deletion...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.delete(f"{FILE_URL}/files/{file_id}", headers=headers)
    if response.status_code == 200:
        print("✓ File deleted successfully")
        
        # Verify file is no longer in list
        response = requests.get(f"{FILE_URL}/files", headers=headers)
        if response.status_code == 200:
            data = response.json()
            remaining_files = [f for f in data['files'] if f['file_id'] == file_id]
            if not remaining_files:
                print("✓ File removed from listing")
                return True
            else:
                print("✗ File still appears in listing")
                return False
        else:
            print(f"✗ Failed to verify deletion: {response.text}")
            return False
    else:
        print(f"✗ File deletion failed: {response.text}")
        return False

def main():
    print("🚀 Starting File Service Tests")
    print("=" * 50)
    
    # Create two users for sharing tests
    print("Setting up test users...")
    user1_data = register_and_login("user1@test.com", "user1", "password123")
    user2_data = register_and_login("user2@test.com", "user2", "password123")
    
    if not user1_data or not user2_data:
        print("Failed to set up test users. Exiting.")
        return
    
    user1_id, token1 = user1_data
    user2_id, token2 = user2_data
    
    # Test file upload
    file_id = test_file_upload(token1)
    if not file_id:
        print("File upload failed. Exiting.")
        return
    
    # Test file listing
    files = test_file_list(token1)
    if not files:
        print("File listing failed.")
        return
    
    # Test file download
    if not test_file_download(token1, file_id, "sample.txt"):
        print("File download failed.")
        return
    
    # Test file rename
    if not test_file_rename(token1, file_id, "renamed_sample.txt"):
        print("File rename failed.")
        return
    
    # Test file sharing
    if not test_file_sharing(token1, token2, file_id, user2_id):
        print("File sharing failed.")
        return
    
    # Test file deletion
    if not test_file_deletion(token1, file_id):
        print("File deletion failed.")
        return
    
    print("\n" + "=" * 50)
    print("✅ All File Service tests completed successfully!")

if __name__ == "__main__":
    main()