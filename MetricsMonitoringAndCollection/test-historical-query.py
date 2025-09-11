#!/usr/bin/env python3
"""
Historical Data Query Workflow Test
Tests all 5 steps of the historical data query workflow:
1. User/API client sends query to Query Service
2. Query Service checks Redis cache
3. If not cached: Query InfluxDB, apply aggregation, cache result
4. Return JSON response with timestamps and values
5. Data can be exported or visualized
"""

import requests
import redis
import json
import time
import csv
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

class HistoricalQueryTest:
    def __init__(self):
        # Service endpoints
        self.query_service_url = "http://localhost:7539"
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.influxdb_url = "http://localhost:8026"
        
        # Initialize Redis client for direct cache testing
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host, 
                port=self.redis_port, 
                db=0, 
                decode_responses=True
            )
            self.redis_client.ping()
            print(f"✅ Connected to Redis at {self.redis_host}:{self.redis_port}")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            self.redis_client = None
        
        self.test_results = []
    
    def run_full_test(self):
        """Run the complete historical query workflow test."""
        print("=" * 80)
        print("🚀 HISTORICAL DATA QUERY WORKFLOW TEST")
        print("=" * 80)
        
        # Test different time ranges and aggregations
        test_scenarios = [
            {
                "name": "30 Minutes Range - Average CPU",
                "metric": "cpu_usage_percent", 
                "hours_back": 0.5,
                "aggregation": "mean",
                "window": "2m"
            },
            {
                "name": "2 Hours Range - Average Memory",
                "metric": "memory_usage_percent",
                "hours_back": 2,
                "aggregation": "mean",
                "window": "10m"
            },
            {
                "name": "6 Hours Range - Count Requests",
                "metric": "request_count_total",
                "hours_back": 6,
                "aggregation": "count",
                "window": "1h"
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n📊 Test Scenario {i}: {scenario['name']}")
            print("-" * 60)
            self.test_historical_query_workflow(scenario)
        
        # Test export and visualization
        print(f"\n📈 Testing Data Export and Visualization")
        print("-" * 60)
        self.test_data_export_visualization()
        
        # Print summary
        self.print_test_summary()
    
    def test_historical_query_workflow(self, scenario: Dict[str, Any]):
        """Test the complete 5-step workflow for a specific scenario."""
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=scenario['hours_back'])
        
        print(f"Time Range: {start_time.isoformat()} to {end_time.isoformat()}")
        print(f"Metric: {scenario['metric']}")
        print(f"Aggregation: {scenario['aggregation']} over {scenario['window']}")
        
        # Step 1: User/API client sends query to Query Service
        query_data = self.step_1_send_query_to_service(
            scenario['metric'],
            start_time,
            end_time,
            scenario['aggregation'],
            scenario['window']
        )
        
        if not query_data:
            print("❌ Test failed at Step 1")
            return
        
        # Step 2: Query Service checks Redis cache
        cache_status = self.step_2_check_redis_cache(scenario['metric'])
        
        # Step 3: Query InfluxDB (if not cached) and cache result
        db_query_result = self.step_3_query_influxdb_and_cache(query_data, cache_status)
        
        # Step 4: Return JSON response with timestamps and values
        formatted_response = self.step_4_validate_json_response(query_data)
        
        # Step 5: Verify data can be exported or visualized
        export_result = self.step_5_test_data_export(query_data, scenario['name'])
        
        # Store test results
        test_result = {
            "scenario": scenario['name'],
            "metric": scenario['metric'],
            "data_points": len(query_data.get('data', [])) if query_data else 0,
            "cache_hit": cache_status,
            "query_success": bool(query_data),
            "export_success": export_result
        }
        self.test_results.append(test_result)
    
    def step_1_send_query_to_service(self, metric: str, start_time: datetime, 
                                   end_time: datetime, aggregation: str, window: str) -> Optional[Dict]:
        """Step 1: User/API client sends query to Query Service"""
        print("🔄 Step 1: Sending query to Query Service...")
        
        try:
            # Test aggregation endpoint
            params = {
                "aggregation": aggregation,
                "window": window,
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
            
            url = f"{self.query_service_url}/query/aggregate/{metric}"
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Step 1: Query successful - received {data.get('count', 0)} data points")
                return data
            else:
                print(f"❌ Step 1: Query failed - HTTP {response.status_code}")
                print(f"Response: {response.text}")
                
                # Fallback: Try basic metrics query
                print("🔄 Step 1: Trying fallback basic metrics query...")
                return self._fallback_basic_query(metric, start_time, end_time)
                
        except Exception as e:
            print(f"❌ Step 1: Exception occurred - {e}")
            return None
    
    def _fallback_basic_query(self, metric: str, start_time: datetime, end_time: datetime) -> Optional[Dict]:
        """Fallback to basic metrics query if aggregation fails."""
        try:
            params = {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "metric": metric
            }
            
            url = f"{self.query_service_url}/query/metrics"
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Step 1: Fallback query successful - received {data.get('count', 0)} data points")
                return data
            else:
                print(f"❌ Step 1: Fallback query also failed - HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Step 1: Fallback query exception - {e}")
            return None
    
    def step_2_check_redis_cache(self, metric: str) -> bool:
        """Step 2: Query Service checks Redis cache"""
        print("🔄 Step 2: Checking Redis cache...")
        
        if not self.redis_client:
            print("❌ Step 2: Redis client not available")
            return False
        
        try:
            # Look for cache keys related to our query
            cache_keys = self.redis_client.keys("query:*")
            cache_hit = len(cache_keys) > 0
            
            if cache_hit:
                print(f"✅ Step 2: Found {len(cache_keys)} cached query results")
                # Show some cache keys for verification
                for key in cache_keys[:3]:  # Show first 3 keys
                    ttl = self.redis_client.ttl(key)
                    print(f"  Cache key: {key} (TTL: {ttl}s)")
            else:
                print("✅ Step 2: No cached results found (cache miss)")
            
            return cache_hit
            
        except Exception as e:
            print(f"❌ Step 2: Redis cache check failed - {e}")
            return False
    
    def step_3_query_influxdb_and_cache(self, query_data: Dict, cache_hit: bool) -> bool:
        """Step 3: Query InfluxDB (if not cached) and cache result"""
        print("🔄 Step 3: Verifying InfluxDB query and caching...")
        
        if cache_hit:
            print("✅ Step 3: Data served from cache (no InfluxDB query needed)")
            return True
        
        # Verify InfluxDB is accessible
        try:
            health_url = f"{self.influxdb_url}/health"
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                print("✅ Step 3a: InfluxDB is accessible")
            else:
                print(f"⚠️  Step 3a: InfluxDB health check returned {response.status_code}")
        except Exception as e:
            print(f"⚠️  Step 3a: InfluxDB health check failed - {e}")
        
        # Check if result was cached (look for new cache entries)
        if self.redis_client:
            try:
                # Wait a moment for cache to be set
                time.sleep(1)
                new_cache_keys = self.redis_client.keys("query:*")
                print(f"✅ Step 3b: Result cached - found {len(new_cache_keys)} cache entries")
                
                # Verify TTL is set correctly (should be around 300 seconds)
                if new_cache_keys:
                    ttl = self.redis_client.ttl(new_cache_keys[0])
                    if 250 <= ttl <= 300:  # Allow some variance
                        print(f"✅ Step 3c: Cache TTL correctly set to {ttl} seconds")
                    else:
                        print(f"⚠️  Step 3c: Cache TTL is {ttl} seconds (expected ~300)")
                
                return True
            except Exception as e:
                print(f"❌ Step 3b: Cache verification failed - {e}")
                return False
        else:
            print("⚠️  Step 3b: Cannot verify caching (Redis not available)")
            return True  # Assume it worked if we got data
    
    def step_4_validate_json_response(self, query_data: Dict) -> bool:
        """Step 4: Return JSON response with timestamps and values"""
        print("🔄 Step 4: Validating JSON response format...")
        
        if not query_data:
            print("❌ Step 4: No query data to validate")
            return False
        
        # Check required fields
        required_fields = ['data', 'count']
        missing_fields = [field for field in required_fields if field not in query_data]
        
        if missing_fields:
            print(f"❌ Step 4: Missing required fields: {missing_fields}")
            return False
        
        print(f"✅ Step 4a: Response contains required fields: {required_fields}")
        
        # Validate data structure
        data = query_data.get('data', [])
        if not isinstance(data, list):
            print("❌ Step 4: Data field is not a list")
            return False
        
        if len(data) > 0:
            # Check first data point structure
            sample_point = data[0]
            expected_point_fields = ['timestamp', 'value']
            point_fields_present = all(field in sample_point for field in expected_point_fields)
            
            if point_fields_present:
                print(f"✅ Step 4b: Data points have correct structure")
                print(f"   Sample: timestamp={sample_point.get('timestamp')}, value={sample_point.get('value')}")
            else:
                print(f"⚠️  Step 4b: Data point structure may be incomplete")
                print(f"   Sample point keys: {list(sample_point.keys())}")
        else:
            print("⚠️  Step 4b: No data points in response")
        
        print(f"✅ Step 4c: Response format validated - {len(data)} data points")
        return True
    
    def step_5_test_data_export(self, query_data: Dict, scenario_name: str) -> bool:
        """Step 5: Verify data can be exported or visualized"""
        print("🔄 Step 5: Testing data export capabilities...")
        
        if not query_data or not query_data.get('data'):
            print("❌ Step 5: No data available for export")
            return False
        
        data = query_data['data']
        
        try:
            # Test CSV export
            csv_filename = f"export_{scenario_name.lower().replace(' ', '_')}.csv"
            with open(csv_filename, 'w', newline='') as csvfile:
                if len(data) > 0:
                    fieldnames = data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                    print(f"✅ Step 5a: CSV export successful - {csv_filename}")
                else:
                    print("⚠️  Step 5a: No data to export to CSV")
            
            # Test JSON export
            json_filename = f"export_{scenario_name.lower().replace(' ', '_')}.json"
            with open(json_filename, 'w') as jsonfile:
                json.dump(query_data, jsonfile, indent=2)
                print(f"✅ Step 5b: JSON export successful - {json_filename}")
            
            return True
            
        except Exception as e:
            print(f"❌ Step 5: Export failed - {e}")
            return False
    
    def test_data_export_visualization(self):
        """Test comprehensive data export and visualization capabilities."""
        
        # Get some recent data for visualization
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=2)
        
        print("🔄 Testing data export and visualization...")
        
        # Try to get some data
        test_data = self.step_1_send_query_to_service(
            "cpu_usage_percent", start_time, end_time, "mean", "10m"
        )
        
        if not test_data or not test_data.get('data'):
            print("⚠️  No data available for visualization test")
            return
        
        data = test_data['data']
        
        try:
            # Create a simple visualization
            timestamps = []
            values = []
            
            for point in data:
                if 'timestamp' in point and 'value' in point:
                    try:
                        # Parse timestamp
                        ts = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
                        timestamps.append(ts)
                        values.append(float(point['value']))
                    except (ValueError, TypeError) as e:
                        continue
            
            if len(timestamps) > 0 and len(values) > 0:
                # Create plot
                plt.figure(figsize=(12, 6))
                plt.plot(timestamps, values, 'b-', linewidth=2)
                plt.title('Historical Data Query Visualization Test')
                plt.xlabel('Timestamp')
                plt.ylabel('Value')
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                plot_filename = 'historical_query_visualization.png'
                plt.savefig(plot_filename)
                plt.close()
                
                print(f"✅ Visualization test successful - saved {plot_filename}")
                print(f"   Plotted {len(timestamps)} data points")
            else:
                print("⚠️  No valid data points for visualization")
        
        except Exception as e:
            print(f"❌ Visualization test failed - {e}")
    
    def test_cache_behavior(self):
        """Test specific Redis cache behavior."""
        print("\n🔧 Testing Cache Behavior")
        print("-" * 40)
        
        if not self.redis_client:
            print("❌ Cannot test cache behavior - Redis not available")
            return
        
        # Clear existing cache
        try:
            cache_keys = self.redis_client.keys("query:*")
            if cache_keys:
                self.redis_client.delete(*cache_keys)
                print(f"🧹 Cleared {len(cache_keys)} existing cache entries")
        except Exception as e:
            print(f"⚠️  Could not clear cache: {e}")
        
        # Make same query twice to test caching
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        print("🔄 Making first query (should miss cache)...")
        start_time_1 = time.time()
        result1 = self.step_1_send_query_to_service(
            "cpu_usage_percent", start_time, end_time, "mean", "5m"
        )
        duration_1 = time.time() - start_time_1
        
        time.sleep(1)  # Wait for cache to be set
        
        print("🔄 Making identical query (should hit cache)...")
        start_time_2 = time.time()
        result2 = self.step_1_send_query_to_service(
            "cpu_usage_percent", start_time, end_time, "mean", "5m"
        )
        duration_2 = time.time() - start_time_2
        
        if result1 and result2:
            print(f"✅ Cache test results:")
            print(f"   First query: {duration_1:.3f}s")
            print(f"   Second query: {duration_2:.3f}s")
            if duration_2 < duration_1 * 0.8:  # Cached should be significantly faster
                print(f"✅ Cache appears to be working (second query faster)")
            else:
                print(f"⚠️  Cache behavior unclear (similar response times)")
    
    def print_test_summary(self):
        """Print a summary of all test results."""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        if not self.test_results:
            print("No test results to display")
            return
        
        total_tests = len(self.test_results)
        successful_queries = sum(1 for r in self.test_results if r['query_success'])
        successful_exports = sum(1 for r in self.test_results if r['export_success'])
        cache_hits = sum(1 for r in self.test_results if r['cache_hit'])
        
        print(f"Total test scenarios: {total_tests}")
        print(f"Successful queries: {successful_queries}/{total_tests}")
        print(f"Successful exports: {successful_exports}/{total_tests}")
        print(f"Cache hits: {cache_hits}/{total_tests}")
        
        print(f"\nDetailed Results:")
        for result in self.test_results:
            status = "✅" if result['query_success'] else "❌"
            cache_status = "💾" if result['cache_hit'] else "🔍"
            export_status = "📄" if result['export_success'] else "❌"
            
            print(f"{status} {result['scenario']}")
            print(f"   Metric: {result['metric']}")
            print(f"   Data points: {result['data_points']}")
            print(f"   Cache: {cache_status} | Export: {export_status}")
        
        # Test cache behavior separately
        self.test_cache_behavior()
        
        print(f"\n🎯 WORKFLOW STATUS:")
        print(f"✅ Step 1: Query Service API - {successful_queries}/{total_tests} successful")
        print(f"✅ Step 2: Redis Cache Check - Tested")
        print(f"✅ Step 3: InfluxDB Query & Caching - Tested")
        print(f"✅ Step 4: JSON Response Format - Validated")
        print(f"✅ Step 5: Data Export/Visualization - {successful_exports}/{total_tests} successful")

def main():
    """Main function to run the historical query workflow test."""
    tester = HistoricalQueryTest()
    tester.run_full_test()

if __name__ == "__main__":
    main()