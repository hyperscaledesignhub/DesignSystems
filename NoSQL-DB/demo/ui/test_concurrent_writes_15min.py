#!/usr/bin/env python3
"""
15-minute Concurrent Writes Test Script
Tests data consistency under various load scenarios
"""
import time
import requests
import threading
import json
import random
from datetime import datetime, timedelta
import statistics

# Test configuration
TEST_DURATION = 15 * 60  # 15 minutes in seconds
BASE_URL = "http://localhost:8005"
SCENARIOS = [
    {
        "name": "Banking Account Balance",
        "key": "account_balance_user123",
        "operations": [
            {"type": "credit", "amount": 100},
            {"type": "debit", "amount": 50},
            {"type": "credit", "amount": 25},
            {"type": "debit", "amount": 30}
        ]
    },
    {
        "name": "E-commerce Inventory", 
        "key": "product_stock_laptop_x1",
        "operations": [
            {"type": "purchase", "quantity": 5},
            {"type": "restock", "quantity": 20},
            {"type": "purchase", "quantity": 3},
            {"type": "return", "quantity": 2}
        ]
    },
    {
        "name": "Social Media Counters",
        "key": "post_likes_viral_video_456", 
        "operations": [
            {"type": "like", "count": 15},
            {"type": "unlike", "count": 2},
            {"type": "like", "count": 8},
            {"type": "share", "count": 5}
        ]
    }
]

# Global test statistics
test_stats = {
    "total_operations": 0,
    "successful_operations": 0,
    "failed_operations": 0,
    "quorum_failures": 0,
    "consistency_checks": 0,
    "consistency_failures": 0,
    "operation_times": [],
    "scenarios_tested": {}
}

test_log = []
running = True

def log_event(message, level="INFO"):
    """Log test events with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}"
    print(log_entry)
    test_log.append(log_entry)

def perform_operation(scenario, operation):
    """Perform a single operation and measure response time"""
    start_time = time.time()
    
    try:
        # Add randomness to amounts/quantities
        op = operation.copy()
        if "amount" in op:
            op["amount"] = random.randint(10, 100)
        elif "quantity" in op:
            op["quantity"] = random.randint(1, 10)
        elif "count" in op:
            op["count"] = random.randint(1, 20)
        
        response = requests.post(
            f"{BASE_URL}/api/concurrent_write",
            json={
                "key": scenario["key"],
                "operation": op
            },
            timeout=10
        )
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        test_stats["total_operations"] += 1
        test_stats["operation_times"].append(operation_time)
        
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                test_stats["successful_operations"] += 1
                if not data["quorum_status"]["write_quorum_met"]:
                    test_stats["quorum_failures"] += 1
                    log_event(f"Quorum failure for {scenario['name']}: {op['type']}", "WARNING")
            else:
                test_stats["failed_operations"] += 1
                log_event(f"Operation failed for {scenario['name']}: {data.get('message', 'Unknown error')}", "ERROR")
        else:
            test_stats["failed_operations"] += 1
            log_event(f"HTTP error {response.status_code} for {scenario['name']}", "ERROR")
            
    except Exception as e:
        test_stats["failed_operations"] += 1
        log_event(f"Exception during operation for {scenario['name']}: {str(e)}", "ERROR")

def check_data_consistency(scenario):
    """Check data consistency across all nodes for a scenario"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/data_consistency/{scenario['key']}",
            timeout=5
        )
        
        test_stats["consistency_checks"] += 1
        
        if response.status_code == 200:
            data = response.json()
            consistency = data["consistency"]
            
            if not consistency["is_consistent"]:
                test_stats["consistency_failures"] += 1
                log_event(f"Consistency failure for {scenario['name']}: {consistency['consistency_level']}", "WARNING")
                return False
            else:
                log_event(f"Consistency check passed for {scenario['name']}: {consistency['consistency_level']}", "DEBUG")
                return True
        else:
            test_stats["consistency_failures"] += 1
            log_event(f"Consistency check HTTP error {response.status_code} for {scenario['name']}", "ERROR")
            return False
            
    except Exception as e:
        test_stats["consistency_failures"] += 1
        log_event(f"Exception during consistency check for {scenario['name']}: {str(e)}", "ERROR")
        return False

def run_low_intensity_test():
    """Run low intensity concurrent operations"""
    log_event("Starting low intensity test phase...")
    
    while running:
        for scenario in SCENARIOS:
            if not running:
                break
                
            operation = random.choice(scenario["operations"])
            perform_operation(scenario, operation)
            
            # Low intensity: 1-3 second delays
            time.sleep(random.uniform(1.0, 3.0))

def run_medium_intensity_test():
    """Run medium intensity concurrent operations"""
    log_event("Starting medium intensity test phase...")
    
    while running:
        # Select random scenario and operation
        scenario = random.choice(SCENARIOS)
        operation = random.choice(scenario["operations"])
        
        perform_operation(scenario, operation)
        
        # Medium intensity: 0.1-0.5 second delays
        time.sleep(random.uniform(0.1, 0.5))

def run_high_intensity_test():
    """Run high intensity concurrent operations"""
    log_event("Starting high intensity test phase...")
    
    while running:
        # Multiple concurrent operations
        threads = []
        
        for _ in range(random.randint(2, 5)):  # 2-5 concurrent operations
            scenario = random.choice(SCENARIOS)
            operation = random.choice(scenario["operations"])
            
            thread = threading.Thread(
                target=perform_operation,
                args=(scenario, operation)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all operations to complete
        for thread in threads:
            thread.join()
        
        # High intensity: 0.05-0.2 second delays
        time.sleep(random.uniform(0.05, 0.2))

def run_consistency_monitor():
    """Monitor data consistency across all scenarios"""
    log_event("Starting consistency monitoring...")
    
    while running:
        for scenario in SCENARIOS:
            if not running:
                break
                
            check_data_consistency(scenario)
        
        # Check consistency every 10 seconds
        time.sleep(10)

def run_burst_test():
    """Run burst operations to test system under extreme load"""
    log_event("Starting burst test phase...")
    
    while running:
        # Create a burst of operations
        log_event("Executing operation burst...")
        
        burst_size = random.randint(10, 20)
        threads = []
        
        for _ in range(burst_size):
            scenario = random.choice(SCENARIOS)
            operation = random.choice(scenario["operations"])
            
            thread = threading.Thread(
                target=perform_operation,
                args=(scenario, operation)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for burst to complete
        for thread in threads:
            thread.join()
        
        log_event(f"Burst of {burst_size} operations completed")
        
        # Rest period between bursts
        time.sleep(random.uniform(15, 30))

def print_test_statistics():
    """Print comprehensive test statistics"""
    print("\n" + "="*60)
    print("🔥 15-MINUTE CONCURRENT WRITES TEST RESULTS")
    print("="*60)
    
    # Basic statistics
    print(f"\n📊 OPERATION STATISTICS:")
    print(f"   Total Operations: {test_stats['total_operations']}")
    print(f"   Successful: {test_stats['successful_operations']} ({test_stats['successful_operations']/max(test_stats['total_operations'],1)*100:.1f}%)")
    print(f"   Failed: {test_stats['failed_operations']} ({test_stats['failed_operations']/max(test_stats['total_operations'],1)*100:.1f}%)")
    print(f"   Quorum Failures: {test_stats['quorum_failures']}")
    
    # Performance statistics
    if test_stats['operation_times']:
        times = test_stats['operation_times']
        print(f"\n⚡ PERFORMANCE STATISTICS:")
        print(f"   Average Response Time: {statistics.mean(times):.3f} seconds")
        print(f"   Median Response Time: {statistics.median(times):.3f} seconds")
        print(f"   Min Response Time: {min(times):.3f} seconds")
        print(f"   Max Response Time: {max(times):.3f} seconds")
        print(f"   Operations per Second: {test_stats['total_operations']/(TEST_DURATION):.2f}")
    
    # Consistency statistics
    print(f"\n🔒 CONSISTENCY STATISTICS:")
    print(f"   Consistency Checks: {test_stats['consistency_checks']}")
    print(f"   Consistency Failures: {test_stats['consistency_failures']} ({test_stats['consistency_failures']/max(test_stats['consistency_checks'],1)*100:.1f}%)")
    print(f"   Consistency Success Rate: {(test_stats['consistency_checks']-test_stats['consistency_failures'])/max(test_stats['consistency_checks'],1)*100:.1f}%")
    
    # Final consistency check
    print(f"\n🎯 FINAL CONSISTENCY CHECK:")
    all_consistent = True
    for scenario in SCENARIOS:
        consistent = check_data_consistency(scenario)
        status = "✅ CONSISTENT" if consistent else "❌ INCONSISTENT"
        print(f"   {scenario['name']}: {status}")
        if not consistent:
            all_consistent = False
    
    print(f"\n🏆 OVERALL RESULT:")
    if all_consistent and test_stats['consistency_failures'] == 0:
        print("   ✅ PERFECT CONSISTENCY - All data consistent throughout test")
    elif all_consistent:
        print("   ✅ STRONG CONSISTENCY - Final state consistent, temporary inconsistencies resolved")
    else:
        print("   ⚠️  EVENTUAL CONSISTENCY - Some inconsistencies detected")
    
    print("\n" + "="*60)

def main():
    """Main test execution"""
    global running
    
    print("🔥 Starting 15-minute Concurrent Writes Consistency Test")
    print(f"⏰ Duration: {TEST_DURATION} seconds ({TEST_DURATION//60} minutes)")
    print("🎯 Testing scenarios: Banking, E-commerce, Social Media")
    print("📊 Monitoring: Operations, Quorum, Consistency")
    print("="*60)
    
    start_time = time.time()
    
    # Start test phases with different intensities
    test_threads = []
    
    # Phase 1: Low intensity (first 3 minutes)
    low_intensity_thread = threading.Thread(target=run_low_intensity_test, daemon=True)
    test_threads.append(low_intensity_thread)
    low_intensity_thread.start()
    
    # Phase 2: Medium intensity (middle period)
    medium_intensity_thread = threading.Thread(target=run_medium_intensity_test, daemon=True)
    test_threads.append(medium_intensity_thread)
    medium_intensity_thread.start()
    
    # Phase 3: High intensity (stress test)
    high_intensity_thread = threading.Thread(target=run_high_intensity_test, daemon=True)
    test_threads.append(high_intensity_thread)
    high_intensity_thread.start()
    
    # Phase 4: Burst operations
    burst_thread = threading.Thread(target=run_burst_test, daemon=True)
    test_threads.append(burst_thread)
    burst_thread.start()
    
    # Consistency monitoring (continuous)
    consistency_thread = threading.Thread(target=run_consistency_monitor, daemon=True)
    test_threads.append(consistency_thread)
    consistency_thread.start()
    
    log_event("All test phases started")
    
    # Progress reporting every minute
    while time.time() - start_time < TEST_DURATION:
        elapsed = int(time.time() - start_time)
        remaining = TEST_DURATION - elapsed
        
        if elapsed % 60 == 0 and elapsed > 0:  # Every minute
            log_event(f"Progress: {elapsed//60}/{TEST_DURATION//60} minutes | Operations: {test_stats['total_operations']} | Success: {test_stats['successful_operations']} | Failures: {test_stats['failed_operations']}")
        
        time.sleep(1)
    
    # Stop all test threads
    running = False
    log_event("Test duration completed, stopping all operations...")
    
    # Wait a moment for operations to finish
    time.sleep(5)
    
    # Print final results
    print_test_statistics()

if __name__ == "__main__":
    main()