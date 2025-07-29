#!/usr/bin/env python3
"""
5-minute Test for Simplified Concurrent Writes Demo
Tests one scenario at a time with controlled operations
"""
import time
import requests
import json
import random
from datetime import datetime, timedelta

# Test configuration
TEST_DURATION = 5 * 60  # 5 minutes
BASE_URL = "http://localhost:8005"

# Test statistics
test_stats = {
    "total_operations": 0,
    "successful_operations": 0,
    "failed_operations": 0,
    "http_errors": 0,
    "quorum_failures": 0,
    "consistency_checks": 0,
    "scenarios_tested": []
}

def log_event(message, level="INFO"):
    """Log test events with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_scenario(scenario_name, duration_seconds=60):
    """Test a single scenario for specified duration"""
    log_event(f"Testing {scenario_name} for {duration_seconds} seconds")
    
    # Initialize scenario
    try:
        response = requests.get(f"{BASE_URL}/api/initialize_scenario/{scenario_name.replace(' ', '%20')}")
        if response.status_code != 200 or not response.json()["success"]:
            log_event(f"Failed to initialize {scenario_name}", "ERROR")
            return False
    except Exception as e:
        log_event(f"Error initializing {scenario_name}: {str(e)}", "ERROR")
        return False
    
    test_stats["scenarios_tested"].append(scenario_name)
    start_time = time.time()
    
    while time.time() - start_time < duration_seconds:
        # Perform a simple test every 10 seconds
        try:
            # Run simple test with 3 operations
            response = requests.post(
                f"{BASE_URL}/api/simple_concurrent_test",
                json={"num_operations": 3},
                timeout=10
            )
            
            if response.status_code == 200:
                test_stats["successful_operations"] += 3  # Assuming 3 operations
                log_event(f"Simple test executed for {scenario_name}")
            else:
                test_stats["http_errors"] += 1
                log_event(f"HTTP error {response.status_code} for {scenario_name}", "WARNING")
            
        except Exception as e:
            test_stats["failed_operations"] += 1
            log_event(f"Test error for {scenario_name}: {str(e)}", "ERROR")
        
        # Check consistency
        check_consistency(scenario_name)
        
        # Wait before next operation batch
        time.sleep(10)
    
    # Clear scenario
    try:
        response = requests.post(f"{BASE_URL}/api/clear_scenario")
        log_event(f"Cleared {scenario_name}")
    except Exception as e:
        log_event(f"Error clearing scenario: {str(e)}", "WARNING")
    
    return True

def check_consistency(scenario_name):
    """Check data consistency for current scenario"""
    key_map = {
        "Banking Account Balance": "account_balance_demo",
        "E-commerce Inventory": "product_stock_demo",
        "Social Media Counters": "post_likes_demo"
    }
    
    key = key_map.get(scenario_name)
    if not key:
        return
    
    try:
        response = requests.get(f"{BASE_URL}/api/data_consistency/{key}", timeout=5)
        test_stats["consistency_checks"] += 1
        
        if response.status_code == 200:
            data = response.json()
            consistency = data["consistency"]
            
            if consistency["is_consistent"]:
                log_event(f"✅ {scenario_name} is CONSISTENT across {consistency['healthy_nodes']} nodes", "DEBUG")
            else:
                log_event(f"⚠️  {scenario_name} showing {consistency['consistency_level']} consistency", "WARNING")
        else:
            log_event(f"Consistency check failed with status {response.status_code}", "ERROR")
            
    except Exception as e:
        log_event(f"Error checking consistency: {str(e)}", "ERROR")

def check_cluster_health():
    """Check cluster health status"""
    try:
        response = requests.get(f"{BASE_URL}/api/quorum_status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            healthy_nodes = sum(1 for n in data["nodes"].values() if n["status"] == "healthy")
            log_event(f"Cluster health: {healthy_nodes}/3 nodes healthy")
            return healthy_nodes
        else:
            log_event("Failed to check cluster health", "ERROR")
            return 0
    except Exception as e:
        log_event(f"Error checking cluster health: {str(e)}", "ERROR")
        return 0

def print_test_summary():
    """Print test summary"""
    print("\n" + "="*50)
    print("🔥 5-MINUTE SIMPLIFIED DEMO TEST RESULTS")
    print("="*50)
    
    print(f"\n📊 TEST STATISTICS:")
    print(f"   Duration: 5 minutes")
    print(f"   Scenarios Tested: {', '.join(test_stats['scenarios_tested'])}")
    print(f"   Total Operations: ~{test_stats['successful_operations']}")
    print(f"   HTTP Errors: {test_stats['http_errors']}")
    print(f"   Failed Operations: {test_stats['failed_operations']}")
    print(f"   Consistency Checks: {test_stats['consistency_checks']}")
    
    # Final consistency check for all scenarios
    print(f"\n🔒 FINAL CONSISTENCY CHECK:")
    
    scenarios = ["Banking Account Balance", "E-commerce Inventory", "Social Media Counters"]
    keys = ["account_balance_demo", "product_stock_demo", "post_likes_demo"]
    
    all_consistent = True
    for scenario, key in zip(scenarios, keys):
        try:
            # Direct check to database nodes
            nodes = ["localhost:9999", "localhost:10000", "localhost:10001"]
            values = []
            
            for node in nodes:
                try:
                    response = requests.get(f"http://{node}/kv/{key}", timeout=3)
                    if response.status_code == 200 and "value" in response.json():
                        data = json.loads(response.json()["value"])
                        values.append(data.get("current_value", "N/A"))
                except:
                    values.append("Error")
            
            if len(set(v for v in values if v != "Error")) <= 1:
                print(f"   {scenario}: ✅ CONSISTENT (Value: {values[0] if values[0] != 'Error' else 'N/A'})")
            else:
                print(f"   {scenario}: ❌ INCONSISTENT (Values: {values})")
                all_consistent = False
                
        except Exception as e:
            print(f"   {scenario}: ❌ ERROR checking consistency")
            all_consistent = False
    
    # Cluster health
    healthy_nodes = check_cluster_health()
    
    print(f"\n🏥 CLUSTER HEALTH:")
    print(f"   Healthy Nodes: {healthy_nodes}/3")
    print(f"   Database Status: {'✅ HEALTHY' if healthy_nodes == 3 else '⚠️  DEGRADED' if healthy_nodes >= 2 else '❌ CRITICAL'}")
    
    print(f"\n🏆 OVERALL RESULT:")
    if all_consistent and test_stats['http_errors'] == 0:
        print("   ✅ PERFECT - Complete consistency, no errors")
    elif all_consistent:
        print("   ✅ GOOD - Data consistent, some HTTP errors")
    else:
        print("   ⚠️  ISSUES - Some inconsistencies detected")
    
    print("="*50)

def main():
    """Run 5-minute test"""
    print("🔥 Starting 5-minute Simplified Concurrent Writes Demo Test")
    print("⏰ Duration: 5 minutes")
    print("🎯 Testing: Banking, E-commerce, Social Media scenarios")
    print("📊 Monitoring: Operations, Consistency, Cluster Health")
    print("="*50)
    
    start_time = time.time()
    
    # Check initial cluster health
    initial_health = check_cluster_health()
    if initial_health < 2:
        print("❌ Cluster unhealthy. Aborting test.")
        return
    
    # Test each scenario for ~100 seconds (total 300 seconds = 5 minutes)
    scenarios = [
        "Banking Account Balance",
        "E-commerce Inventory", 
        "Social Media Counters"
    ]
    
    for scenario in scenarios:
        remaining_time = TEST_DURATION - (time.time() - start_time)
        if remaining_time <= 0:
            break
            
        scenario_duration = min(100, remaining_time)
        test_scenario(scenario, scenario_duration)
        
        # Brief pause between scenarios
        time.sleep(2)
    
    # Final summary
    print_test_summary()

if __name__ == "__main__":
    main()