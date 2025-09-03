#!/usr/bin/env python3
import requests
import random
import json
import time

API_BASE = "http://localhost:9823"  # Direct business service
SEARCH_BASE = "http://localhost:8921"  # Direct location service

# San Francisco area businesses
SF_BUSINESSES = [
    # Restaurants
    {"name": "Golden Gate Grill", "category": "Restaurant", "lat": 37.7749, "lng": -122.4194, "address": "123 Market St"},
    {"name": "Fisherman's Wharf Seafood", "category": "Restaurant", "lat": 37.8080, "lng": -122.4177, "address": "555 Beach St"},
    {"name": "China Town Express", "category": "Restaurant", "lat": 37.7941, "lng": -122.4078, "address": "888 Grant Ave"},
    {"name": "Mission Burrito House", "category": "Restaurant", "lat": 37.7599, "lng": -122.4148, "address": "2001 Mission St"},
    {"name": "North Beach Pizza", "category": "Restaurant", "lat": 37.8002, "lng": -122.4100, "address": "1499 Stockton St"},
    
    # Cafes
    {"name": "Bay Area Coffee Co", "category": "Cafe", "lat": 37.7751, "lng": -122.4180, "address": "456 Powell St"},
    {"name": "Union Square Cafe", "category": "Cafe", "lat": 37.7879, "lng": -122.4074, "address": "321 Geary St"},
    {"name": "Castro Coffee House", "category": "Cafe", "lat": 37.7609, "lng": -122.4350, "address": "4001 Castro St"},
    {"name": "Haight Street Brew", "category": "Cafe", "lat": 37.7692, "lng": -122.4481, "address": "1500 Haight St"},
    {"name": "Financial District Coffee", "category": "Cafe", "lat": 37.7946, "lng": -122.3999, "address": "101 California St"},
    
    # Hotels
    {"name": "Bay View Hotel", "category": "Hotel", "lat": 37.7879, "lng": -122.4074, "address": "321 Geary St"},
    {"name": "Fisherman's Inn", "category": "Hotel", "lat": 37.8077, "lng": -122.4200, "address": "2500 Mason St"},
    {"name": "Downtown Plaza Hotel", "category": "Hotel", "lat": 37.7855, "lng": -122.4065, "address": "55 Cyril Magnin St"},
    {"name": "Golden Gate Lodge", "category": "Hotel", "lat": 37.8199, "lng": -122.4783, "address": "3400 Scott St"},
    {"name": "Mission Bay Resort", "category": "Hotel", "lat": 37.7708, "lng": -122.3925, "address": "1500 3rd St"},
    
    # Stores
    {"name": "Tech Gadget Store", "category": "Electronics", "lat": 37.7745, "lng": -122.4189, "address": "789 Mission St"},
    {"name": "Union Square Mall", "category": "Shopping", "lat": 37.7880, "lng": -122.4075, "address": "333 Post St"},
    {"name": "Farmers Market", "category": "Grocery", "lat": 37.7858, "lng": -122.4364, "address": "1 Ferry Building"},
    {"name": "Book Paradise", "category": "Books", "lat": 37.7692, "lng": -122.4660, "address": "1644 Haight St"},
    {"name": "Sports World", "category": "Sports", "lat": 37.7785, "lng": -122.4188, "address": "845 Market St"},
]

# Generate random businesses around a point
def generate_random_businesses(center_lat, center_lng, count=50, radius_km=5):
    businesses = []
    categories = ["Restaurant", "Cafe", "Hotel", "Store", "Service", "Bar", "Gym", "Pharmacy"]
    prefixes = ["Golden", "Bay", "Pacific", "Silicon", "Ocean", "Hill", "Park", "City"]
    suffixes = ["Place", "Point", "Center", "Hub", "Spot", "Corner", "Square", "Station"]
    
    for i in range(count):
        # Random offset within radius
        angle = random.uniform(0, 2 * 3.14159)
        distance = random.uniform(0, radius_km / 111)  # Convert km to degrees (rough)
        
        lat = center_lat + distance * random.uniform(-1, 1)
        lng = center_lng + distance * random.uniform(-1, 1)
        
        businesses.append({
            "name": f"{random.choice(prefixes)} {random.choice(suffixes)} #{i+1}",
            "category": random.choice(categories),
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "address": f"{random.randint(1, 9999)} {random.choice(['Market', 'Mission', 'Valencia', 'Folsom', 'Howard'])} St"
        })
    
    return businesses

def create_business(business):
    """Create a single business via API"""
    data = {
        "name": business["name"],
        "latitude": business["lat"],
        "longitude": business["lng"],
        "address": business["address"],
        "city": "San Francisco",
        "state": "CA",
        "country": "USA",
        "category": business["category"]
    }
    
    try:
        response = requests.post(f"{API_BASE}/businesses", json=data, timeout=5)
        if response.status_code == 200:
            print(f"✓ Created: {business['name']}")
            return response.json()
        else:
            print(f"✗ Failed: {business['name']} - {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Error: {business['name']} - {str(e)}")
        return None

def load_demo_data():
    """Load all demo data"""
    print("=" * 60)
    print("LOADING DEMO DATA FOR PROXIMITY SERVICE")
    print("=" * 60)
    
    # Load predefined SF businesses
    print("\n1. Loading San Francisco businesses...")
    created = 0
    for business in SF_BUSINESSES:
        if create_business(business):
            created += 1
        time.sleep(0.1)  # Avoid rate limiting
    
    print(f"\n   Created {created}/{len(SF_BUSINESSES)} SF businesses")
    
    # Generate random businesses
    print("\n2. Generating random businesses...")
    random_businesses = generate_random_businesses(37.7749, -122.4194, count=30, radius_km=3)
    
    created = 0
    for business in random_businesses:
        if create_business(business):
            created += 1
        time.sleep(0.1)
    
    print(f"\n   Created {created}/{len(random_businesses)} random businesses")
    
    # Test search
    print("\n3. Testing search functionality...")
    test_search()
    
    print("\n" + "=" * 60)
    print("DEMO DATA LOADING COMPLETE!")
    print("=" * 60)

def test_search():
    """Test search functionality"""
    test_points = [
        {"name": "Downtown SF", "lat": 37.7749, "lng": -122.4194, "radius": 1000},
        {"name": "Fisherman's Wharf", "lat": 37.8080, "lng": -122.4177, "radius": 500},
        {"name": "Mission District", "lat": 37.7599, "lng": -122.4148, "radius": 2000},
    ]
    
    for point in test_points:
        try:
            response = requests.get(
                f"{SEARCH_BASE}/nearby",
                params={
                    "latitude": point["lat"],
                    "longitude": point["lng"],
                    "radius": point["radius"]
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ {point['name']}: Found {len(data['businesses'])} businesses within {point['radius']}m")
            else:
                print(f"   ✗ {point['name']}: Search failed - {response.status_code}")
                
        except Exception as e:
            print(f"   ✗ {point['name']}: Error - {str(e)}")

def clear_all_data():
    """Clear all businesses (optional)"""
    print("Clearing existing data...")
    # This would require implementing a delete all endpoint
    pass

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_all_data()
    
    load_demo_data()