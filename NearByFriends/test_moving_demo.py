#!/usr/bin/env python3
"""
Test script to simulate the Moving Demo functionality
"""
import json
import requests
import time

def test_moving_demo():
    print("🧪 Testing Moving Demo functionality...")
    
    # Load demo user
    with open('demo_config.json', 'r') as f:
        config = json.load(f)
        alice = config['users'][0]  # Alice Johnson
    
    print(f"👤 Testing with user: {alice['name']} (ID: {alice['id']})")
    
    # Define the route (same as in JavaScript)
    route = [
        {"lat": 37.7749, "lng": -122.4194, "name": "Starting Point"},
        {"lat": 37.7755, "lng": -122.4200, "name": "North Point"},
        {"lat": 37.7760, "lng": -122.4180, "name": "East Point"},
        {"lat": 37.7750, "lng": -122.4170, "name": "Southeast Point"},
        {"lat": 37.7740, "lng": -122.4190, "name": "Final Point"}
    ]
    
    headers = {
        'Authorization': f'Bearer {alice["token"]}',
        'Content-Type': 'application/json'
    }
    
    print(f"🗺️  Moving through {len(route)} points...")
    
    for i, point in enumerate(route):
        print(f"📍 Point {i+1}/{len(route)}: {point['name']} at ({point['lat']}, {point['lng']})")
        
        # Update location
        data = {'latitude': point['lat'], 'longitude': point['lng']}
        
        try:
            response = requests.post('http://localhost:8900/api/location/update', 
                                   headers=headers, json=data, timeout=5)
            
            if response.status_code == 200:
                print(f"  ✅ Location updated successfully")
            else:
                print(f"  ❌ Location update failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        if i < len(route) - 1:  # Don't sleep after the last point
            print(f"  ⏳ Waiting 3 seconds before next move...")
            time.sleep(3)
    
    print("🎉 Moving Demo test completed!")

if __name__ == "__main__":
    test_moving_demo()