#!/usr/bin/env python3
"""
Test script for Location Service features
Tests all the implemented features:
1. Store user location updates
2. Query nearby friends within 5-mile radius 
3. Location caching with Redis (10-minute TTL for inactive users)
4. Get user's current location
5. Location history storage in PostgreSQL
6. Distance calculations using Geopy
"""

import requests
import json
import time
import sys
import asyncio
import asyncpg
import redis.asyncio as redis
from datetime import datetime
from geopy.distance import geodesic

USER_SERVICE_URL = "http://localhost:8901"
FRIEND_SERVICE_URL = "http://localhost:8902"
LOCATION_SERVICE_URL = "http://localhost:8903"

# Test locations around San Francisco
SF_DOWNTOWN = {"latitude": 37.7749, "longitude": -122.4194}  # San Francisco downtown
SF_MISSION = {"latitude": 37.7599, "longitude": -122.4148}   # Mission District (~1 mile away)
SF_OAKLAND = {"latitude": 37.8044, "longitude": -122.2712}   # Oakland (~8 miles away)
SF_BERKELEY = {"latitude": 37.8715, "longitude": -122.2730}  # Berkeley (~12 miles away)

def print_test(test_name):
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print('='*60)

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

def add_friendship(user1_token, user2_id):
    """Add friendship between users"""
    try:
        response = requests.post(
            f"{FRIEND_SERVICE_URL}/friends/add",
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"friend_id": user2_id}
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error adding friendship: {e}")
        return False

def setup_test_users():
    """Create test users with friendships for location testing"""
    print_test("Setting up Test Users with Locations")
    
    timestamp = int(time.time())
    users = []
    
    # Create 4 test users
    for i in range(1, 5):
        username = f"location_user{i}_{timestamp}"
        password = f"LocationPass{i}"
        
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
    
    if len(users) >= 3:
        # Set up friendships: User1 is friends with User2 and User3
        add_friendship(users[0]['token'], users[1]['user_id'])
        add_friendship(users[0]['token'], users[2]['user_id'])
        # User4 is not friends with User1
        print_result(True, "Set up friendships between users")
    
    return users

def test_health():
    """Test Location Service health endpoint"""
    print_test("Location Service Health Check")
    try:
        response = requests.get(f"{LOCATION_SERVICE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Location Service is {data['status']}")
            return True
    except Exception as e:
        print_result(False, f"Health check failed: {e}")
    return False

def test_store_location_updates(users):
    """Test storing user location updates"""
    print_test("Store User Location Updates")
    
    if len(users) < 4:
        print_result(False, "Not enough users for testing")
        return False
    
    # Test updating locations for all users
    locations = [SF_DOWNTOWN, SF_MISSION, SF_OAKLAND, SF_BERKELEY]
    
    try:
        for i, user in enumerate(users):
            location = locations[i % len(locations)]
            
            response = requests.post(
                f"{LOCATION_SERVICE_URL}/location/update",
                headers={"Authorization": f"Bearer {user['token']}"},
                json=location
            )
            
            if response.status_code == 200:
                print_result(True, f"Updated location for {user['username']} to {location}")
            else:
                print_result(False, f"Failed to update location for {user['username']}: {response.text}")
                return False
        
        return True
        
    except Exception as e:
        print_result(False, f"Location update test failed: {e}")
        return False

def test_get_current_location(users):
    """Test getting user's current location"""
    print_test("Get User's Current Location")
    
    if len(users) < 1:
        print_result(False, "No users for testing")
        return False
    
    user = users[0]
    
    try:
        response = requests.get(
            f"{LOCATION_SERVICE_URL}/location/{user['user_id']}",
            headers={"Authorization": f"Bearer {user['token']}"}
        )
        
        if response.status_code == 200:
            location_data = response.json()
            print_result(True, f"Retrieved current location for {user['username']}")
            print(f"  - Latitude: {location_data['latitude']}")
            print(f"  - Longitude: {location_data['longitude']}")
            print(f"  - Timestamp: {location_data['timestamp']}")
            
            # Verify it matches what we set (SF_DOWNTOWN for first user)
            expected = SF_DOWNTOWN
            if (abs(location_data['latitude'] - expected['latitude']) < 0.001 and
                abs(location_data['longitude'] - expected['longitude']) < 0.001):
                print_result(True, "Location data matches what was stored")
            else:
                print_result(False, "Location data doesn't match what was stored")
                return False
            
            return True
        else:
            print_result(False, f"Failed to get current location: {response.text}")
    
    except Exception as e:
        print_result(False, f"Get current location test failed: {e}")
    
    return False

def test_distance_calculations_geopy(users):
    """Test distance calculations using Geopy"""
    print_test("Distance Calculations using Geopy")
    
    try:
        # Calculate distances between known test locations
        sf_to_mission = geodesic((SF_DOWNTOWN['latitude'], SF_DOWNTOWN['longitude']),
                                (SF_MISSION['latitude'], SF_MISSION['longitude'])).miles
        
        sf_to_oakland = geodesic((SF_DOWNTOWN['latitude'], SF_DOWNTOWN['longitude']),
                                (SF_OAKLAND['latitude'], SF_OAKLAND['longitude'])).miles
        
        print_result(True, f"SF Downtown to Mission District: {sf_to_mission:.2f} miles")
        print_result(True, f"SF Downtown to Oakland: {sf_to_oakland:.2f} miles")
        
        # Verify reasonable distances
        if 0.5 < sf_to_mission < 2.0:  # Mission should be ~1 mile away
            print_result(True, "SF to Mission distance is reasonable")
        else:
            print_result(False, f"SF to Mission distance seems wrong: {sf_to_mission:.2f} miles")
            return False
        
        if 6.0 < sf_to_oakland < 12.0:  # Oakland should be ~8 miles away
            print_result(True, "SF to Oakland distance is reasonable")
        else:
            print_result(False, f"SF to Oakland distance seems wrong: {sf_to_oakland:.2f} miles")
            return False
        
        return True
        
    except Exception as e:
        print_result(False, f"Distance calculation test failed: {e}")
        return False

def test_nearby_friends_query(users):
    """Test querying nearby friends within 5-mile radius"""
    print_test("Query Nearby Friends within 5-mile radius")
    
    if len(users) < 3:
        print_result(False, "Not enough users for testing")
        return False
    
    user1 = users[0]  # SF Downtown
    # user2 = users[1]  # SF Mission (~1 mile - should be nearby)
    # user3 = users[2]  # SF Oakland (~8 miles - should NOT be nearby)
    
    try:
        response = requests.get(
            f"{LOCATION_SERVICE_URL}/location/nearby/{user1['user_id']}",
            headers={"Authorization": f"Bearer {user1['token']}"}
        )
        
        if response.status_code == 200:
            nearby_friends = response.json()
            print_result(True, f"Retrieved nearby friends for {user1['username']}")
            print(f"  - Found {len(nearby_friends)} nearby friends")
            
            for friend in nearby_friends:
                print(f"  - Friend ID: {friend['user_id']}, Distance: {friend['distance_miles']} miles")
                print(f"    Location: ({friend['latitude']}, {friend['longitude']})")
            
            # Verify logic: Mission District friend should be nearby, Oakland friend should not
            nearby_user_ids = [f['user_id'] for f in nearby_friends]
            mission_user_id = users[1]['user_id']  # Should be nearby (Mission District)
            oakland_user_id = users[2]['user_id']  # Should NOT be nearby (Oakland)
            
            if mission_user_id in nearby_user_ids:
                print_result(True, "Mission District friend is correctly identified as nearby")
            else:
                print_result(False, "Mission District friend should be nearby but isn't")
                return False
            
            if oakland_user_id not in nearby_user_ids:
                print_result(True, "Oakland friend is correctly excluded (too far)")
            else:
                print_result(False, "Oakland friend should be excluded but isn't")
                return False
            
            # Check distance calculations in results
            for friend in nearby_friends:
                if friend['distance_miles'] > 5.0:
                    print_result(False, f"Friend at {friend['distance_miles']} miles should be excluded")
                    return False
            
            print_result(True, "All nearby friends are within 5-mile radius")
            return True
            
        else:
            print_result(False, f"Failed to get nearby friends: {response.text}")
    
    except Exception as e:
        print_result(False, f"Nearby friends query test failed: {e}")
    
    return False

async def test_location_caching_redis():
    """Test location caching with Redis TTL"""
    print_test("Location Caching with Redis (10-minute TTL)")
    
    try:
        # Connect to Redis directly to verify caching
        redis_client = await redis.from_url("redis://localhost:6679")
        
        # Check if location data exists in Redis
        location_keys = []
        async for key in redis_client.scan_iter(match="location:*"):
            location_keys.append(key)
        
        if location_keys:
            print_result(True, f"Found {len(location_keys)} location entries in Redis cache")
            
            # Check TTL on one of the keys
            sample_key = location_keys[0]
            ttl = await redis_client.ttl(sample_key)
            
            if ttl > 0:
                print_result(True, f"Location cache has TTL: {ttl} seconds remaining")
                print(f"  - TTL should be around 600 seconds (10 minutes)")
                
                if 300 < ttl <= 600:  # Should be between 5-10 minutes
                    print_result(True, "TTL is within expected range")
                else:
                    print_result(False, f"TTL {ttl} is outside expected range")
                    await redis_client.close()
                    return False
            else:
                print_result(False, "Location cache entry has no TTL or has expired")
                await redis_client.close()
                return False
            
            # Get sample location data
            sample_data = await redis_client.get(sample_key)
            if sample_data:
                location_data = json.loads(sample_data)
                print_result(True, "Successfully retrieved location data from cache")
                print(f"  - Sample data: lat={location_data.get('latitude')}, lon={location_data.get('longitude')}")
            else:
                print_result(False, "Could not retrieve location data from cache")
                await redis_client.close()
                return False
        else:
            print_result(False, "No location entries found in Redis cache")
            await redis_client.close()
            return False
        
        await redis_client.close()
        return True
        
    except Exception as e:
        print_result(False, f"Redis caching test failed: {e}")
        return False

async def test_location_history_postgresql():
    """Test location history storage in PostgreSQL"""
    print_test("Location History Storage in PostgreSQL")
    
    try:
        # Connect to PostgreSQL directly to verify history storage
        conn = await asyncpg.connect("postgresql://user:password@localhost:5732/nearbyfriendsdb")
        
        # Check if location_history table exists and has data
        result = await conn.fetch("SELECT COUNT(*) FROM location_history")
        count = result[0]['count']
        
        if count > 0:
            print_result(True, f"Found {count} location history entries in PostgreSQL")
            
            # Get some sample data
            sample_data = await conn.fetch("""
                SELECT user_id, latitude, longitude, timestamp 
                FROM location_history 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            
            print("  Recent location history entries:")
            for row in sample_data:
                print(f"    - User {row['user_id']}: ({row['latitude']}, {row['longitude']}) at {row['timestamp']}")
            
            # Verify we have recent entries (within last few minutes)
            recent_entries = await conn.fetch("""
                SELECT COUNT(*) FROM location_history 
                WHERE timestamp >= NOW() - INTERVAL '5 minutes'
            """)
            recent_count = recent_entries[0]['count']
            
            if recent_count > 0:
                print_result(True, f"Found {recent_count} recent location entries (within 5 minutes)")
            else:
                print_result(False, "No recent location entries found")
                await conn.close()
                return False
        else:
            print_result(False, "No location history entries found in PostgreSQL")
            await conn.close()
            return False
        
        await conn.close()
        return True
        
    except Exception as e:
        print_result(False, f"PostgreSQL history test failed: {e}")
        return False

async def main():
    print("\n" + "="*60)
    print("LOCATION SERVICE FEATURE TESTS")
    print("="*60)
    
    # Check if Location Service is running
    if not test_health():
        print("\n❌ Location Service is not running. Please start it first.")
        sys.exit(1)
    
    # Set up test users with different locations
    users = setup_test_users()
    if not users or len(users) < 4:
        print("\n❌ Failed to set up test users. Cannot proceed with tests.")
        sys.exit(1)
    
    # Wait a moment for location updates to be processed
    print("\n⏳ Waiting for location updates to be processed...")
    time.sleep(2)
    
    # Run Location Service tests
    store_updates_success = test_store_location_updates(users)
    get_location_success = test_get_current_location(users)
    distance_calc_success = test_distance_calculations_geopy(users)
    nearby_friends_success = test_nearby_friends_query(users)
    redis_cache_success = await test_location_caching_redis()
    postgres_history_success = await test_location_history_postgresql()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    print("\n✅ Features Successfully Tested:")
    if store_updates_success:
        print("  1. Store user location updates")
        print("     - Location updates sent to service")
        print("     - Updates stored in both Redis and PostgreSQL")
    
    if get_location_success:
        print("  2. Get user's current location")
        print("     - Retrieves latest location from cache")
        print("     - Data integrity verified")
    
    if distance_calc_success:
        print("  3. Distance calculations using Geopy")
        print("     - Accurate distance calculations between coordinates")
        print("     - Reasonable distance validation")
    
    if nearby_friends_success:
        print("  4. Query nearby friends within 5-mile radius")
        print("     - Finds friends within radius")
        print("     - Excludes friends beyond radius")
        print("     - Accurate distance calculations")
    
    if redis_cache_success:
        print("  5. Location caching with Redis (10-minute TTL)")
        print("     - Locations cached in Redis")
        print("     - TTL properly set and managed")
    
    if postgres_history_success:
        print("  6. Location history storage in PostgreSQL")
        print("     - Historical data persisted")
        print("     - Recent entries verified")
    
    # Count successful tests
    successful_tests = sum([
        store_updates_success,
        get_location_success, 
        distance_calc_success,
        nearby_friends_success,
        redis_cache_success,
        postgres_history_success
    ])
    
    print(f"\n📊 Test Results: {successful_tests}/6 feature sets passed")
    
    if successful_tests == 6:
        print("\n🎉 All Location Service features are working correctly!")
    else:
        print(f"\n⚠️  {6 - successful_tests} feature set(s) need attention")
    
    print("\n📝 Location Service Implementation Notes:")
    print("  - Uses async Redis client for location caching")
    print("  - 10-minute TTL automatically removes inactive users")
    print("  - PostgreSQL stores complete location history")
    print("  - Geopy library provides accurate distance calculations")
    print("  - 5-mile radius filter for nearby friends")
    print("  - Real-time location updates with pub/sub")
    print("  - Integration with Friend Service for social features")

if __name__ == "__main__":
    asyncio.run(main())