import requests
import json

BASE_URL = "http://localhost:9011"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"✓ Health check: {response.status_code}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_register():
    """Test user registration"""
    print("\nTesting user registration...")
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register", json=user_data)
        print(f"✓ Registration response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ User created: {data['user_id']}")
            return data
        else:
            print(f"✗ Registration failed: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Registration error: {e}")
        return None

def test_login(email, password):
    """Test user login"""
    print("\nTesting user login...")
    login_data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        print(f"✓ Login response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Login successful, token received: {data['token_type']}")
            return data['access_token']
        else:
            print(f"✗ Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Login error: {e}")
        return None

def test_profile(token):
    """Test get profile"""
    print("\nTesting get profile...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/profile", headers=headers)
        print(f"✓ Profile response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Profile retrieved: {data['username']} ({data['email']})")
            return data
        else:
            print(f"✗ Profile failed: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Profile error: {e}")
        return None

def test_update_profile(token):
    """Test update profile"""
    print("\nTesting update profile...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.put(f"{BASE_URL}/profile?username=updateduser", headers=headers)
        print(f"✓ Update profile response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Profile updated: {data['username']}")
            return True
        else:
            print(f"✗ Update profile failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Update profile error: {e}")
        return False

def test_logout(token):
    """Test logout"""
    print("\nTesting logout...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/logout", headers=headers)
        print(f"✓ Logout response: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Logout successful")
            return True
        else:
            print(f"✗ Logout failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Logout error: {e}")
        return False

def main():
    print("🚀 Starting Auth Service Tests")
    print("=" * 50)
    
    # Test health
    if not test_health():
        print("Service is not running. Exiting.")
        return
    
    # Test registration
    user = test_register()
    if not user:
        print("Registration failed. Exiting.")
        return
    
    # Test login
    token = test_login(user['email'], 'testpassword123')
    if not token:
        print("Login failed. Exiting.")
        return
    
    # Test profile retrieval
    profile = test_profile(token)
    if not profile:
        print("Profile retrieval failed.")
        return
    
    # Test profile update
    if not test_update_profile(token):
        print("Profile update failed.")
        return
    
    # Test logout
    test_logout(token)
    
    print("\n" + "=" * 50)
    print("✅ All Auth Service tests completed!")

if __name__ == "__main__":
    main()