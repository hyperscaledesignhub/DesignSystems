import threading
import requests
import json
from datetime import datetime

# Test configuration
RESERVATION_URL = "http://localhost:5005/reservations"
GUEST_ID = "d94ead52-7568-43f8-a2aa-861e236767e7"
ROOM_TYPE_ID = "1277d80d-b568-4a28-a347-212d35a1ebd5"

results = []

def make_reservation(thread_id, num_rooms):
    """Make a reservation request and store the result"""
    try:
        response = requests.post(
            RESERVATION_URL,
            headers={"Content-Type": "application/json"},
            json={
                "guest_id": GUEST_ID,
                "room_type_id": ROOM_TYPE_ID,
                "check_in": "2026-05-01",
                "check_out": "2026-05-03",
                "num_rooms": num_rooms,
                "total_amount": num_rooms * 400.00
            }
        )
        results.append({
            "thread": thread_id,
            "status": response.status_code,
            "response": response.json() if response.status_code in [200, 201] else response.text
        })
    except Exception as e:
        results.append({
            "thread": thread_id,
            "status": "error",
            "response": str(e)
        })

# First, initialize inventory for May 1-3
print("Initializing inventory for May 1-3, 2026...")
for day in range(1, 3):
    response = requests.post(
        f"http://localhost:5004/reserve?room_type_id={ROOM_TYPE_ID}&hotel_id=default-hotel&check_in=2026-05-0{day}&check_out=2026-05-0{day+1}&num_rooms=0"
    )
    print(f"  Day {day}: {response.json()}")

# Check initial availability
print("\nChecking initial availability...")
response = requests.get(
    f"http://localhost:5004/availability?room_type_id={ROOM_TYPE_ID}&check_in=2026-05-01&check_out=2026-05-03&num_rooms=1"
)
print(f"Available rooms: {response.json()['available_rooms']}")

# Launch 3 threads simultaneously for 4, 5, 2 rooms respectively
print("\nLaunching 3 concurrent reservation requests:")
print("  Thread 1: 4 rooms")
print("  Thread 2: 5 rooms") 
print("  Thread 3: 2 rooms")
print("(Total requested: 11 rooms, Total available: 10 rooms)")
print("Expected: Only 2 requests should succeed (combinations that sum ≤10)\n")

t1 = threading.Thread(target=make_reservation, args=(1, 4))
t2 = threading.Thread(target=make_reservation, args=(2, 5))
t3 = threading.Thread(target=make_reservation, args=(3, 2))

# Start all three threads at the same time
start_time = datetime.now()
t1.start()
t2.start()
t3.start()

# Wait for all to complete
t1.join()
t2.join()
t3.join()
end_time = datetime.now()

print(f"Execution time: {(end_time - start_time).total_seconds():.3f} seconds\n")

# Display results
successful = 0
failed = 0

for result in results:
    print(f"Thread {result['thread']}:")
    print(f"  Status: {result['status']}")
    if result['status'] in [200, 201]:
        successful += 1
        print(f"  Reservation ID: {result['response']['id']}")
        print(f"  Rooms booked: {result['response']['num_rooms']}")
    else:
        failed += 1
        print(f"  Error: {result['response']}")
    print()

print(f"Summary: {successful} succeeded, {failed} failed")

# Check final availability
print("\nChecking final availability...")
response = requests.get(
    f"http://localhost:5004/availability?room_type_id={ROOM_TYPE_ID}&check_in=2026-05-01&check_out=2026-05-03&num_rooms=1"
)
final_available = response.json()['available_rooms']
print(f"Available rooms after concurrent requests: {final_available}")

# Calculate total rooms requested
total_requested = sum(result['response']['num_rooms'] for result in results if result['status'] in [200, 201])
print(f"Total rooms actually booked: {total_requested}")

if total_requested <= 10 and final_available + total_requested == 10:
    print("\n✅ CONCURRENCY CONTROL WORKING CORRECTLY!")
    print("   No overbooking occurred - total booked ≤ available inventory")
    print(f"   {successful} requests succeeded, {failed} were rejected")
else:
    print("\n❌ OVERBOOKING DETECTED!")
    print(f"   Total booked: {total_requested}, Available was: 10")
    print(f"   Remaining: {final_available} (Should equal 10 - {total_requested})")