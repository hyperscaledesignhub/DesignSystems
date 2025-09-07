#!/usr/bin/env python3
"""
Setup demo data for the Nearby Friends demo
Creates users, friendships, and initial locations
"""

import asyncio
import aiohttp
import json
import random
import time

API_BASE_URL = "http://localhost:8900"

# Demo users data with San Francisco locations
demo_users = [
    {"name": "Alice Johnson", "email": "alice@demo.com", "lat": 37.7749, "lng": -122.4194},
    {"name": "Bob Smith", "email": "bob@demo.com", "lat": 37.7751, "lng": -122.4196},
    {"name": "Charlie Brown", "email": "charlie@demo.com", "lat": 37.7755, "lng": -122.4186},
    {"name": "Diana Prince", "email": "diana@demo.com", "lat": 37.7742, "lng": -122.4189},
    {"name": "Eve Wilson", "email": "eve@demo.com", "lat": 37.7758, "lng": -122.4205},
    {"name": "Frank Miller", "email": "frank@demo.com", "lat": 37.7735, "lng": -122.4178},
    {"name": "Grace Lee", "email": "grace@demo.com", "lat": 37.7762, "lng": -122.4182},
    {"name": "Henry Davis", "email": "henry@demo.com", "lat": 37.7745, "lng": -122.4210},
    {"name": "Ivy Chen", "email": "ivy@demo.com", "lat": 37.7738, "lng": -122.4195},
    {"name": "Jack Wilson", "email": "jack@demo.com", "lat": 37.7763, "lng": -122.4175},
]

# Friendship connections (realistic social network)
friendships = [
    [0, 1], [0, 2], [0, 3], [0, 4],  # Alice friends with Bob, Charlie, Diana, Eve
    [1, 2], [1, 5], [1, 6],          # Bob friends with Charlie, Frank, Grace
    [2, 3], [2, 7], [2, 8],          # Charlie friends with Diana, Henry, Ivy
    [3, 4], [3, 5], [3, 9],          # Diana friends with Eve, Frank, Jack
    [4, 6], [4, 7], [4, 8],          # Eve friends with Grace, Henry, Ivy
    [5, 6], [5, 7], [5, 9],          # Frank friends with Grace, Henry, Jack
    [6, 7], [6, 8], [6, 9],          # Grace friends with Henry, Ivy, Jack
    [7, 8], [7, 9],                  # Henry friends with Ivy, Jack
    [8, 9]                           # Ivy friends with Jack
]

async def create_demo_users():
    """Create demo users in the system"""
    print("🚀 Creating demo users...")
    
    async with aiohttp.ClientSession() as session:
        created_users = []
        
        for i, user_data in enumerate(demo_users):
            try:
                # Create unique username
                username = user_data["email"].split("@")[0] + "_demo_" + str(int(time.time()))
                
                register_data = {
                    "username": username,
                    "email": user_data["email"],
                    "password": "demo123",
                    "location_sharing_enabled": True
                }
                
                async with session.post(
                    f"{API_BASE_URL}/api/auth/register",
                    json=register_data
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        user_info = {
                            **user_data,
                            "username": username,
                            "user_id": result["user"]["user_id"],
                            "token": result["token"]
                        }
                        created_users.append(user_info)
                        print(f"   ✅ Created: {user_data['name']} (ID: {user_info['user_id']})")
                    else:
                        print(f"   ❌ Failed to create: {user_data['name']} - Status: {response.status}")
                        
            except Exception as e:
                print(f"   ❌ Error creating {user_data['name']}: {e}")
                
        return created_users

async def create_friendships(users):
    """Create friendships between users"""
    print(f"\n👥 Creating {len(friendships)} friendships...")
    
    async with aiohttp.ClientSession() as session:
        for idx1, idx2 in friendships:
            if idx1 < len(users) and idx2 < len(users):
                user1 = users[idx1]
                user2 = users[idx2]
                
                try:
                    async with session.post(
                        f"{API_BASE_URL}/api/friends/add",
                        headers={"Authorization": f"Bearer {user1['token']}"},
                        json={"friend_id": user2['user_id']}
                    ) as response:
                        if response.status in [200, 201]:
                            print(f"   ✅ {user1['name']} ↔ {user2['name']}")
                        else:
                            print(f"   ⚠️  {user1['name']} ↔ {user2['name']} (may already exist)")
                            
                except Exception as e:
                    print(f"   ❌ Error creating friendship {user1['name']} ↔ {user2['name']}: {e}")

async def set_initial_locations(users):
    """Set initial locations for all users"""
    print(f"\n📍 Setting initial locations...")
    
    async with aiohttp.ClientSession() as session:
        for user in users:
            try:
                # Add small random variation to locations
                lat = user["lat"] + (random.random() - 0.5) * 0.002
                lng = user["lng"] + (random.random() - 0.5) * 0.002
                
                async with session.post(
                    f"{API_BASE_URL}/api/location/update",
                    headers={"Authorization": f"Bearer {user['token']}"},
                    json={"latitude": lat, "longitude": lng}
                ) as response:
                    if response.status in [200, 201]:
                        print(f"   ✅ {user['name']}: ({lat:.6f}, {lng:.6f})")
                    else:
                        print(f"   ❌ Failed to set location for {user['name']}")
                        
            except Exception as e:
                print(f"   ❌ Error setting location for {user['name']}: {e}")

async def check_services():
    """Check if all services are running"""
    print("🔍 Checking services...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    health = await response.json()
                    services = health.get("services", {})
                    
                    all_healthy = True
                    for service, status in services.items():
                        icon = "✅" if status == "healthy" else "❌"
                        print(f"   {icon} {service}: {status}")
                        if status != "healthy":
                            all_healthy = False
                    
                    if all_healthy:
                        print("   🎉 All services are healthy!")
                        return True
                    else:
                        print("   ⚠️  Some services are not healthy")
                        return False
                else:
                    print(f"   ❌ API Gateway not responding (Status: {response.status})")
                    return False
                    
    except Exception as e:
        print(f"   ❌ Error checking services: {e}")
        return False

async def generate_sample_activity(users):
    """Generate some sample activity for demo purposes"""
    print(f"\n🎭 Generating sample activity...")
    
    async with aiohttp.ClientSession() as session:
        # Simulate some location updates
        for _ in range(5):
            user = random.choice(users)
            
            # Small movement
            new_lat = user["lat"] + (random.random() - 0.5) * 0.001
            new_lng = user["lng"] + (random.random() - 0.5) * 0.001
            
            try:
                async with session.post(
                    f"{API_BASE_URL}/api/location/update",
                    headers={"Authorization": f"Bearer {user['token']}"},
                    json={"latitude": new_lat, "longitude": new_lng}
                ) as response:
                    if response.status in [200, 201]:
                        print(f"   📱 {user['name']} moved to ({new_lat:.6f}, {new_lng:.6f})")
                        
            except Exception as e:
                print(f"   ❌ Error updating location for {user['name']}: {e}")
                
            await asyncio.sleep(0.5)  # Small delay between updates

async def save_demo_config(users):
    """Save demo configuration for UI"""
    config = {
        "users": [
            {
                "id": user["user_id"],
                "name": user["name"],
                "email": user["email"],
                "username": user["username"],
                "token": user["token"],
                "lat": user["lat"],
                "lng": user["lng"]
            }
            for user in users
        ],
        "created_at": time.time()
    }
    
    with open("demo_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Demo configuration saved to demo_config.json")

async def main():
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║                                                                ║")
    print("║            🎬 NEARBY FRIENDS DEMO DATA SETUP 🎬               ║")
    print("║                                                                ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    
    # Check if services are running
    if not await check_services():
        print("\n❌ Services are not ready. Please run './startup.sh' first.")
        return
    
    # Create demo data
    users = await create_demo_users()
    
    if not users:
        print("❌ Failed to create users. Exiting.")
        return
        
    await create_friendships(users)
    await set_initial_locations(users)
    await generate_sample_activity(users)
    await save_demo_config(users)
    
    print(f"\n╔════════════════════════════════════════════════════════════════╗")
    print(f"║                                                                ║")
    print(f"║                   🎉 DEMO DATA SETUP COMPLETE! 🎉             ║")
    print(f"║                                                                ║")
    print(f"║  ➤ {len(users)} demo users created                                   ║")
    print(f"║  ➤ {len(friendships)} friendships established                       ║")
    print(f"║  ➤ All users have initial locations                           ║")
    print(f"║  ➤ Sample activity generated                                   ║")
    print(f"║                                                                ║")
    print(f"║  Next steps:                                                   ║")
    print(f"║  1. Run: python3 serve_demo.py                                ║")
    print(f"║  2. Open: http://localhost:3000/demo_ui.html                   ║")
    print(f"║  3. Select any user and click 'Login' to start demo           ║")
    print(f"║                                                                ║")
    print(f"╚════════════════════════════════════════════════════════════════╝")

if __name__ == "__main__":
    asyncio.run(main())