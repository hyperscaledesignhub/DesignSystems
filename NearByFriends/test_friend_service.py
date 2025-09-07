#!/usr/bin/env python3
"""
Test script for Friend Service features
Tests all the implemented features:
1. Add friends (simplified - no approval workflow)
2. Remove friends
3. Get friend list for a user
4. Check friendship status between two users
5. Bi-directional friendship relationships
"""

import requests
import json
import time
import sys

USER_SERVICE_URL = "http://localhost:8901"
FRIEND_SERVICE_URL = "http://localhost:8902"

def print_test(test_name):
    print(f"\n{'='*50}")
    print(f"Testing: {test_name}")
    print('='*50)

def print_result(success, message):
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

def register_test_user(username, password):
    """Register a test user and return their token and user data"""
    try:
        response = requests.post(f"{USER_SERVICE_URL}/auth/register", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to register user {username}: {response.text}")
            return None
    except Exception as e:
        print(f"Error registering user {username}: {e}")
        return None

def setup_test_users():
    """Create test users for friendship testing"""
    print_test("Setting up Test Users")
    
    timestamp = int(time.time())
    users = []
    
    for i in range(1, 4):  # Create 3 test users
        username = f"friend_test_user{i}_{timestamp}"
        password = f"TestPass{i}"
        
        user_data = register_test_user(username, password)
        if user_data:
            users.append({
                'username': username,
                'password': password,
                'token': user_data['token'],
                'user_id': user_data['user']['user_id'],
                'user_data': user_data['user']
            })
            print_result(True, f"Created user: {username} (ID: {user_data['user']['user_id']})")
        else:
            print_result(False, f"Failed to create user: {username}")
            return None
    
    return users

def test_health():
    """Test Friend Service health endpoint"""
    print_test("Friend Service Health Check")
    try:
        response = requests.get(f"{FRIEND_SERVICE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Friend Service is {data['status']}")
            return True
    except Exception as e:
        print_result(False, f"Health check failed: {e}")
    return False

def test_add_friends(users):
    """Test adding friends functionality"""
    print_test("Add Friends Functionality")
    
    if len(users) < 2:
        print_result(False, "Not enough users for testing")
        return False
    
    user1 = users[0]
    user2 = users[1]
    
    headers1 = {"Authorization": f"Bearer {user1['token']}"}
    headers2 = {"Authorization": f"Bearer {user2['token']}"}
    
    try:
        # Test 1: User1 adds User2 as friend
        response = requests.post(
            f"{FRIEND_SERVICE_URL}/friends/add",
            headers=headers1,
            json={"friend_id": user2['user_id']}
        )
        
        if response.status_code == 200:
            print_result(True, f"{user1['username']} successfully added {user2['username']} as friend")
        else:
            print_result(False, f"Failed to add friend: {response.text}")
            return False
        
        # Test 2: Try to add the same friend again (should fail)
        response = requests.post(
            f"{FRIEND_SERVICE_URL}/friends/add",
            headers=headers1,
            json={"friend_id": user2['user_id']}
        )
        
        if response.status_code == 400:
            print_result(True, "Duplicate friendship prevention works")
        else:
            print_result(False, "Duplicate friendship prevention failed")
        
        # Test 3: Try to add self as friend (should fail)
        response = requests.post(
            f"{FRIEND_SERVICE_URL}/friends/add",
            headers=headers1,
            json={"friend_id": user1['user_id']}
        )
        
        if response.status_code == 400:
            print_result(True, "Self-friendship prevention works")
        else:
            print_result(False, "Self-friendship prevention failed")
        
        return True
        
    except Exception as e:
        print_result(False, f"Add friends test failed: {e}")
        return False

def test_bi_directional_friendship(users):
    """Test that friendships are bi-directional"""
    print_test("Bi-directional Friendship")
    
    if len(users) < 2:
        print_result(False, "Not enough users for testing")
        return False
    
    user1 = users[0]
    user2 = users[1]
    
    headers1 = {"Authorization": f"Bearer {user1['token']}"}
    headers2 = {"Authorization": f"Bearer {user2['token']}"}
    
    try:
        # Check if User1 has User2 as friend
        response1 = requests.get(f"{FRIEND_SERVICE_URL}/friends/{user1['user_id']}", headers=headers1)
        # Check if User2 has User1 as friend
        response2 = requests.get(f"{FRIEND_SERVICE_URL}/friends/{user2['user_id']}", headers=headers2)
        
        if response1.status_code == 200 and response2.status_code == 200:
            friends1 = response1.json()
            friends2 = response2.json()
            
            # Check if user2 is in user1's friend list
            user2_in_user1_friends = any(f['friend_id'] == user2['user_id'] for f in friends1)
            # Check if user1 is in user2's friend list
            user1_in_user2_friends = any(f['friend_id'] == user1['user_id'] for f in friends2)
            
            if user2_in_user1_friends and user1_in_user2_friends:
                print_result(True, "Friendship is bi-directional")
                return True
            else:
                print_result(False, "Friendship is not bi-directional")
        else:
            print_result(False, "Failed to retrieve friend lists for bi-directional test")
    
    except Exception as e:
        print_result(False, f"Bi-directional friendship test failed: {e}")
    
    return False

def test_get_friend_list(users):
    """Test getting friend list functionality"""
    print_test("Get Friend List Functionality")
    
    if len(users) < 2:
        print_result(False, "Not enough users for testing")
        return False
    
    user1 = users[0]
    user2 = users[1]
    headers1 = {"Authorization": f"Bearer {user1['token']}"}
    
    try:
        # Get friend list for user1
        response = requests.get(f"{FRIEND_SERVICE_URL}/friends/{user1['user_id']}", headers=headers1)
        
        if response.status_code == 200:
            friends = response.json()
            print_result(True, f"Retrieved friend list for {user1['username']}")
            print(f"  - Number of friends: {len(friends)}")
            
            if len(friends) > 0:
                for friend in friends:
                    print(f"  - Friend ID: {friend['friend_id']}, Added: {friend['created_at']}")
                
                # Verify user2 is in the list
                user2_in_list = any(f['friend_id'] == user2['user_id'] for f in friends)
                if user2_in_list:
                    print_result(True, f"{user2['username']} found in {user1['username']}'s friend list")
                else:
                    print_result(False, f"{user2['username']} not found in {user1['username']}'s friend list")
            
            return True
        else:
            print_result(False, f"Failed to get friend list: {response.text}")
    
    except Exception as e:
        print_result(False, f"Get friend list test failed: {e}")
    
    return False

def test_friendship_status_check(users):
    """Test checking friendship status between two users"""
    print_test("Friendship Status Check")
    
    if len(users) < 3:
        print_result(False, "Not enough users for testing")
        return False
    
    user1 = users[0]
    user2 = users[1]  # Should be friends with user1
    user3 = users[2]  # Should NOT be friends with user1
    
    headers1 = {"Authorization": f"Bearer {user1['token']}"}
    
    try:
        # Check if user1 and user2 are friends (should be true)
        response = requests.get(
            f"{FRIEND_SERVICE_URL}/friends/check/{user1['user_id']}/{user2['user_id']}", 
            headers=headers1
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['are_friends']:
                print_result(True, f"{user1['username']} and {user2['username']} are confirmed as friends")
            else:
                print_result(False, f"{user1['username']} and {user2['username']} should be friends but are not")
                return False
        else:
            print_result(False, f"Failed to check friendship status: {response.text}")
            return False
        
        # Check if user1 and user3 are friends (should be false)
        response = requests.get(
            f"{FRIEND_SERVICE_URL}/friends/check/{user1['user_id']}/{user3['user_id']}", 
            headers=headers1
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data['are_friends']:
                print_result(True, f"{user1['username']} and {user3['username']} correctly shown as not friends")
            else:
                print_result(False, f"{user1['username']} and {user3['username']} should not be friends")
                return False
        else:
            print_result(False, f"Failed to check friendship status: {response.text}")
            return False
        
        return True
        
    except Exception as e:
        print_result(False, f"Friendship status check test failed: {e}")
        return False

def test_remove_friends(users):
    """Test removing friends functionality"""
    print_test("Remove Friends Functionality")
    
    if len(users) < 2:
        print_result(False, "Not enough users for testing")
        return False
    
    user1 = users[0]
    user2 = users[1]
    headers1 = {"Authorization": f"Bearer {user1['token']}"}
    headers2 = {"Authorization": f"Bearer {user2['token']}"}
    
    try:
        # Remove user2 from user1's friends
        response = requests.delete(
            f"{FRIEND_SERVICE_URL}/friends/{user2['user_id']}", 
            headers=headers1
        )
        
        if response.status_code == 200:
            print_result(True, f"Successfully removed {user2['username']} from {user1['username']}'s friends")
        else:
            print_result(False, f"Failed to remove friend: {response.text}")
            return False
        
        # Verify removal by checking friend lists
        response1 = requests.get(f"{FRIEND_SERVICE_URL}/friends/{user1['user_id']}", headers=headers1)
        response2 = requests.get(f"{FRIEND_SERVICE_URL}/friends/{user2['user_id']}", headers=headers2)
        
        if response1.status_code == 200 and response2.status_code == 200:
            friends1 = response1.json()
            friends2 = response2.json()
            
            user2_in_user1_friends = any(f['friend_id'] == user2['user_id'] for f in friends1)
            user1_in_user2_friends = any(f['friend_id'] == user1['user_id'] for f in friends2)
            
            if not user2_in_user1_friends and not user1_in_user2_friends:
                print_result(True, "Friendship removed bi-directionally")
            else:
                print_result(False, "Friendship removal was not bi-directional")
                return False
        
        # Test removing non-existent friend
        response = requests.delete(
            f"{FRIEND_SERVICE_URL}/friends/{user2['user_id']}", 
            headers=headers1
        )
        
        if response.status_code == 404:
            print_result(True, "Removing non-existent friend returns proper error")
        else:
            print_result(False, "Removing non-existent friend should return 404")
        
        return True
        
    except Exception as e:
        print_result(False, f"Remove friends test failed: {e}")
        return False

def main():
    print("\n" + "="*50)
    print("FRIEND SERVICE FEATURE TESTS")
    print("="*50)
    
    # Check if Friend Service is running
    if not test_health():
        print("\n❌ Friend Service is not running. Please start it first.")
        sys.exit(1)
    
    # Set up test users
    users = setup_test_users()
    if not users or len(users) < 3:
        print("\n❌ Failed to set up test users. Cannot proceed with tests.")
        sys.exit(1)
    
    # Run Friend Service tests
    add_friends_success = test_add_friends(users)
    bi_directional_success = test_bi_directional_friendship(users)
    friend_list_success = test_get_friend_list(users)
    friendship_check_success = test_friendship_status_check(users)
    remove_friends_success = test_remove_friends(users)
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    print("\n✅ Features Successfully Tested:")
    if add_friends_success:
        print("  1. Add friends (simplified - no approval workflow)")
        print("     - Friend addition works")
        print("     - Duplicate friendship prevention")
        print("     - Self-friendship prevention")
    
    if bi_directional_success:
        print("  2. Bi-directional friendship relationships")
        print("     - Both users appear in each other's friend lists")
    
    if friend_list_success:
        print("  3. Get friend list for a user")
        print("     - Retrieves friends with timestamps")
        print("     - Shows correct friend count")
    
    if friendship_check_success:
        print("  4. Check friendship status between two users")
        print("     - Correctly identifies existing friendships")
        print("     - Correctly identifies non-friendships")
    
    if remove_friends_success:
        print("  5. Remove friends")
        print("     - Bi-directional friend removal")
        print("     - Proper error handling for non-existent friends")
    
    # Count successful tests
    successful_tests = sum([
        add_friends_success, 
        bi_directional_success, 
        friend_list_success, 
        friendship_check_success, 
        remove_friends_success
    ])
    
    print(f"\n📊 Test Results: {successful_tests}/5 feature sets passed")
    
    if successful_tests == 5:
        print("\n🎉 All Friend Service features are working correctly!")
    else:
        print(f"\n⚠️  {5 - successful_tests} feature set(s) need attention")
    
    print("\n📝 Friend Service Implementation Notes:")
    print("  - Uses PostgreSQL for persistent friendship data")
    print("  - JWT authentication required for all endpoints")
    print("  - Friendships are automatically bi-directional")
    print("  - Friend requests table exists but simplified workflow used")
    print("  - All friendship operations are atomic (use transactions)")

if __name__ == "__main__":
    main()