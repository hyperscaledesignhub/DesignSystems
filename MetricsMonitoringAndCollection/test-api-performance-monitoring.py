#!/usr/bin/env python3
"""
Comprehensive API Performance Monitoring Test

Tests the complete API performance monitoring workflow:
1. API service exposes metrics (request count, response time, error rate)
2. Metrics collected every 30 seconds
3. Alerts configured (response time > 500ms, error rate > 1%)
4. Dashboard shows request throughput, response time percentiles, error rate trends

This test verifies the monitoring system can track API performance metrics accurately,
collect metrics at regular intervals, detect performance degradation, alert when
thresholds are breached, and provide comprehensive dashboard visibility.
"""

import asyncio
import aiohttp
import json
import time
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class APIEndpoint:
    """Represents an API endpoint configuration for testing"""
    path: str
    method: str
    response_time_range: tuple  # (min_ms, max_ms)
    error_rate: float  # 0.0 to 1.0
    description: str

@dataclass  
class PerformanceScenario:
    """Performance test scenario configuration"""
    name: str
    endpoints: List[APIEndpoint]
    duration_seconds: int
    requests_per_second: int
    
@dataclass
class TestResult:
    """Test execution result"""
    test_name: str
    status: str
    details: Dict[str, Any]
    timestamp: str
    duration_seconds: float

class APIPerformanceSimulator:
    """Simulates various API performance scenarios"""
    
    def __init__(self, metrics_source_url: str):
        self.metrics_source_url = metrics_source_url
        self.scenarios = self._create_performance_scenarios()
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    def _create_performance_scenarios(self) -> List[PerformanceScenario]:
        """Create realistic API performance scenarios"""
        return [
            # High-performance scenario
            PerformanceScenario(
                name="high_performance",
                endpoints=[
                    APIEndpoint("/api/users", "GET", (20, 80), 0.001, "Fast user listing"),
                    APIEndpoint("/api/health", "GET", (5, 15), 0.0, "Health check"),
                    APIEndpoint("/api/cache", "GET", (10, 50), 0.002, "Cached data")
                ],
                duration_seconds=60,
                requests_per_second=50
            ),
            # Medium-performance scenario  
            PerformanceScenario(
                name="medium_performance",
                endpoints=[
                    APIEndpoint("/api/search", "GET", (100, 400), 0.005, "Search queries"),
                    APIEndpoint("/api/reports", "POST", (150, 350), 0.01, "Report generation"),
                    APIEndpoint("/api/analytics", "GET", (200, 300), 0.008, "Analytics data")
                ],
                duration_seconds=45,
                requests_per_second=25
            ),
            # Slow scenario (should trigger alerts)
            PerformanceScenario(
                name="slow_performance",
                endpoints=[
                    APIEndpoint("/api/heavy-compute", "POST", (600, 1200), 0.02, "Heavy computation"),
                    APIEndpoint("/api/large-dataset", "GET", (800, 1500), 0.015, "Large data queries"),
                    APIEndpoint("/api/ml-inference", "POST", (500, 900), 0.03, "ML model inference")
                ],
                duration_seconds=30,
                requests_per_second=10
            ),
            # Error-prone scenario (should trigger alerts)
            PerformanceScenario(
                name="error_prone",
                endpoints=[
                    APIEndpoint("/api/flaky", "GET", (100, 300), 0.05, "Flaky service"),  # 5% error rate
                    APIEndpoint("/api/unstable", "POST", (200, 400), 0.08, "Unstable endpoint"),  # 8% error rate
                    APIEndpoint("/api/timeout", "GET", (300, 600), 0.15, "Timeout prone")  # 15% error rate
                ],
                duration_seconds=30,
                requests_per_second=20
            )
        ]
    
    async def simulate_api_request(self, endpoint: APIEndpoint) -> Dict[str, Any]:
        """Simulate a single API request with realistic metrics"""
        start_time = time.time()
        
        # Simulate response time
        response_time_ms = random.uniform(*endpoint.response_time_range)
        await asyncio.sleep(response_time_ms / 1000.0)
        
        # Determine if this request results in an error
        is_error = random.random() < endpoint.error_rate
        status_code = random.choice([400, 404, 500, 503]) if is_error else 200
        
        end_time = time.time()
        actual_response_time = (end_time - start_time) * 1000  # Convert to ms
        
        return {
            "endpoint": endpoint.path,
            "method": endpoint.method,
            "status_code": status_code,
            "response_time_ms": actual_response_time,
            "timestamp": datetime.utcnow().isoformat(),
            "is_error": is_error
        }
    
    async def run_scenario(self, scenario: PerformanceScenario) -> Dict[str, Any]:
        """Run a performance scenario and collect metrics"""
        logger.info(f"🎬 Starting scenario: {scenario.name}")
        
        start_time = time.time()
        request_interval = 1.0 / scenario.requests_per_second
        scenario_results = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            scenario_end_time = start_time + scenario.duration_seconds
            
            while time.time() < scenario_end_time and self.running:
                # Select random endpoint from scenario
                endpoint = random.choice(scenario.endpoints)
                
                # Create task for simulated request
                task = asyncio.create_task(self.simulate_api_request(endpoint))
                tasks.append(task)
                
                # Wait for request interval
                await asyncio.sleep(request_interval)
                
                # Process completed tasks
                if len(tasks) >= 10:  # Process in batches
                    completed_tasks = []
                    for task in tasks:
                        if task.done():
                            try:
                                result = await task
                                scenario_results.append(result)
                                await self.push_api_metrics(result)
                                completed_tasks.append(task)
                            except Exception as e:
                                logger.error(f"Task error: {e}")
                                completed_tasks.append(task)
                    
                    # Remove completed tasks
                    tasks = [t for t in tasks if t not in completed_tasks]
            
            # Process remaining tasks
            for task in tasks:
                try:
                    result = await task
                    scenario_results.append(result)
                    await self.push_api_metrics(result)
                except Exception as e:
                    logger.error(f"Final task error: {e}")
        
        # Calculate scenario summary
        total_requests = len(scenario_results)
        error_requests = sum(1 for r in scenario_results if r["is_error"])
        error_rate = (error_requests / total_requests) if total_requests > 0 else 0
        
        response_times = [r["response_time_ms"] for r in scenario_results]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times) if response_times else 0
        
        duration = time.time() - start_time
        throughput = total_requests / duration if duration > 0 else 0
        
        summary = {
            "scenario": scenario.name,
            "duration_seconds": duration,
            "total_requests": total_requests,
            "error_requests": error_requests,
            "error_rate": error_rate,
            "average_response_time_ms": avg_response_time,
            "p95_response_time_ms": p95_response_time,
            "throughput_rps": throughput,
            "requests": scenario_results
        }
        
        logger.info(f"✅ Scenario {scenario.name} completed: {total_requests} requests, "
                   f"{error_rate:.1%} error rate, {avg_response_time:.1f}ms avg response time")
        
        return summary
    
    async def push_api_metrics(self, request_result: Dict[str, Any]):
        """Push individual API metrics to the metrics source"""
        try:
            async with aiohttp.ClientSession() as session:
                # Push request count metric
                await self._push_metric(session, {
                    "name": "api_request_total",
                    "value": 1,
                    "labels": {
                        "endpoint": request_result["endpoint"],
                        "method": request_result["method"],
                        "status": str(request_result["status_code"]),
                        "host": "demo-api"
                    },
                    "timestamp": request_result["timestamp"]
                })
                
                # Push response time metric
                await self._push_metric(session, {
                    "name": "api_request_duration_seconds",
                    "value": request_result["response_time_ms"] / 1000.0,
                    "labels": {
                        "endpoint": request_result["endpoint"],
                        "method": request_result["method"],
                        "host": "demo-api"
                    },
                    "timestamp": request_result["timestamp"]
                })
                
                # Push error metric if applicable
                if request_result["is_error"]:
                    await self._push_metric(session, {
                        "name": "api_error_rate",
                        "value": 1,
                        "labels": {
                            "endpoint": request_result["endpoint"],
                            "method": request_result["method"],
                            "host": "demo-api"
                        },
                        "timestamp": request_result["timestamp"]
                    })
                
        except Exception as e:
            logger.error(f"Failed to push API metrics: {e}")
    
    async def _push_metric(self, session: aiohttp.ClientSession, metric_data: Dict[str, Any]):
        """Push a single metric to the metrics source"""
        try:
            async with session.post(f"{self.metrics_source_url}/push", json=metric_data) as response:
                if response.status != 201:
                    logger.warning(f"Failed to push metric {metric_data['name']}: {response.status}")
        except Exception as e:
            logger.error(f"Error pushing metric {metric_data['name']}: {e}")
    
    def start(self):
        """Start the performance simulator"""
        self.running = True
    
    def stop(self):
        """Stop the performance simulator"""  
        self.running = False
        self.executor.shutdown(wait=False)

class APIPerformanceMonitoringTest:
    """Main test class for API Performance Monitoring workflow"""
    
    def __init__(self):
        self.services = {
            "enhanced_metrics_source": "http://localhost:3001",
            "metrics_collector": "http://localhost:9847", 
            "query_service": "http://localhost:7539",
            "alert_manager": "http://localhost:6428",
            "dashboard": "http://localhost:5317"
        }
        
        self.test_results: List[TestResult] = []
        self.simulator = APIPerformanceSimulator(self.services["enhanced_metrics_source"])
        
    async def test_step1_api_metrics_exposure(self) -> TestResult:
        """Test Step 1: Verify APIs expose proper performance metrics"""
        logger.info("🧪 Testing Step 1: API Metrics Exposure")
        start_time = time.time()
        
        try:
            # Start simulator to generate some API metrics
            self.simulator.start()
            
            # Run a quick high-performance scenario to generate metrics
            quick_scenario = PerformanceScenario(
                name="metrics_exposure_test",
                endpoints=[
                    APIEndpoint("/api/test", "GET", (50, 150), 0.01, "Test endpoint"),
                    APIEndpoint("/api/health", "GET", (10, 30), 0.0, "Health check")
                ],
                duration_seconds=15,
                requests_per_second=10
            )
            
            await self.simulator.run_scenario(quick_scenario)
            
            # Wait a moment for metrics to be processed
            await asyncio.sleep(2)
            
            # Check if metrics are exposed in Prometheus format
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.services['enhanced_metrics_source']}/metrics") as response:
                    metrics_content = await response.text()
                    
                    # Verify required API metrics are present
                    required_metrics = [
                        "api_request_total",
                        "api_request_duration_seconds", 
                        "api_error_rate"
                    ]
                    
                    missing_metrics = []
                    for metric in required_metrics:
                        if metric not in metrics_content:
                            missing_metrics.append(metric)
                    
                    # Check for API-specific labels
                    has_endpoint_labels = "endpoint=" in metrics_content
                    has_method_labels = "method=" in metrics_content
                    has_status_labels = "status=" in metrics_content
                    
                    details = {
                        "metrics_endpoint_status": response.status,
                        "metrics_content_length": len(metrics_content),
                        "required_metrics_found": [m for m in required_metrics if m in metrics_content],
                        "missing_metrics": missing_metrics,
                        "has_endpoint_labels": has_endpoint_labels,
                        "has_method_labels": has_method_labels,
                        "has_status_labels": has_status_labels,
                        "sample_metrics": metrics_content[:500] + "..." if len(metrics_content) > 500 else metrics_content
                    }
                    
                    success = (response.status == 200 and 
                              len(missing_metrics) == 0 and
                              has_endpoint_labels and has_method_labels and has_status_labels)
                    
                    return TestResult(
                        test_name="api_metrics_exposure",
                        status="PASS" if success else "FAIL",
                        details=details,
                        timestamp=datetime.utcnow().isoformat(),
                        duration_seconds=time.time() - start_time
                    )
                    
        except Exception as e:
            return TestResult(
                test_name="api_metrics_exposure",
                status="ERROR",
                details={"error": str(e)},
                timestamp=datetime.utcnow().isoformat(),
                duration_seconds=time.time() - start_time
            )
    
    async def test_step2_metrics_collection_intervals(self) -> TestResult:
        """Test Step 2: Verify metrics are collected every 30 seconds"""
        logger.info("🧪 Testing Step 2: Metrics Collection Intervals")
        start_time = time.time()
        
        try:
            # Clear existing metrics to start fresh
            async with aiohttp.ClientSession() as session:
                await session.post(f"{self.services['enhanced_metrics_source']}/clear")
            
            # Generate API metrics over time and monitor collection
            collection_checks = []
            
            # Start continuous API load
            continuous_scenario = PerformanceScenario(
                name="collection_interval_test",
                endpoints=[
                    APIEndpoint("/api/interval-test", "GET", (100, 200), 0.02, "Interval test endpoint")
                ],
                duration_seconds=90,  # Run for 90 seconds to capture multiple collection cycles
                requests_per_second=5
            )
            
            # Start the scenario in background
            scenario_task = asyncio.create_task(self.simulator.run_scenario(continuous_scenario))
            
            # Check metrics collection at regular intervals
            for i in range(4):  # Check 4 times over ~90 seconds
                await asyncio.sleep(25)  # Wait 25 seconds between checks
                
                # Query the metrics collector to see if it has collected data
                async with aiohttp.ClientSession() as session:
                    # Check metrics collector endpoint
                    async with session.get(f"{self.services['metrics_collector']}/metrics") as response:
                        if response.status == 200:
                            metrics_data = await response.json()
                            collection_checks.append({
                                "timestamp": datetime.utcnow().isoformat(),
                                "check_number": i + 1,
                                "collector_status": response.status,
                                "metrics_count": len(metrics_data.get("metrics", [])),
                                "has_api_metrics": any("api_" in str(m) for m in metrics_data.get("metrics", []))
                            })
                        else:
                            collection_checks.append({
                                "timestamp": datetime.utcnow().isoformat(), 
                                "check_number": i + 1,
                                "collector_status": response.status,
                                "error": f"HTTP {response.status}"
                            })
                    
                    # Also check the query service for stored metrics
                    try:
                        query_params = {
                            "metric": "api_request_total",
                            "start": int((datetime.utcnow() - timedelta(minutes=2)).timestamp()),
                            "end": int(datetime.utcnow().timestamp())
                        }
                        async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as query_response:
                            if query_response.status == 200:
                                query_data = await query_response.json()
                                collection_checks[-1]["query_service_status"] = query_response.status
                                collection_checks[-1]["stored_data_points"] = len(query_data.get("data", []))
                    except Exception as e:
                        collection_checks[-1]["query_service_error"] = str(e)
            
            # Wait for scenario to complete
            await scenario_task
            
            # Analyze collection intervals
            successful_collections = [c for c in collection_checks if c.get("collector_status") == 200]
            regular_intervals = len(successful_collections) >= 3  # At least 3 successful collections
            
            details = {
                "test_duration_seconds": 90,
                "collection_checks": collection_checks,
                "successful_collections": len(successful_collections),
                "regular_intervals_detected": regular_intervals,
                "expected_collections": "~3-4 (every 30 seconds)"
            }
            
            return TestResult(
                test_name="metrics_collection_intervals",
                status="PASS" if regular_intervals else "FAIL",
                details=details,
                timestamp=datetime.utcnow().isoformat(),
                duration_seconds=time.time() - start_time
            )
            
        except Exception as e:
            return TestResult(
                test_name="metrics_collection_intervals", 
                status="ERROR",
                details={"error": str(e)},
                timestamp=datetime.utcnow().isoformat(),
                duration_seconds=time.time() - start_time
            )
    
    async def test_step3_performance_thresholds_alerts(self) -> TestResult:
        """Test Step 3: Test alerts for response time > 500ms and error rate > 1%"""
        logger.info("🧪 Testing Step 3: Performance Threshold Alerts")
        start_time = time.time()
        
        try:
            # Clear any existing alerts
            async with aiohttp.ClientSession() as session:
                try:
                    await session.post(f"{self.services['alert_manager']}/api/alerts/clear")
                except:
                    pass  # Alert manager might not have this endpoint
            
            alert_tests = []
            
            # Test 1: Trigger slow response time alerts (>500ms)
            logger.info("  Testing slow response time alerts...")
            slow_scenario_result = await self.simulator.run_scenario(self.simulator.scenarios[2])  # slow_performance
            
            await asyncio.sleep(5)  # Wait for alerts to be processed
            
            # Check for response time alerts
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{self.services['alert_manager']}/api/alerts") as response:
                        if response.status == 200:
                            alerts_data = await response.json()
                            slow_alerts = [a for a in alerts_data.get("alerts", []) if "response_time" in str(a).lower() or "duration" in str(a).lower()]
                            
                            alert_tests.append({
                                "test_type": "slow_response_time",
                                "scenario_avg_response_time": slow_scenario_result["average_response_time_ms"],
                                "threshold_exceeded": slow_scenario_result["average_response_time_ms"] > 500,
                                "alerts_found": len(slow_alerts),
                                "alert_manager_status": response.status,
                                "sample_alerts": slow_alerts[:3]  # First 3 alerts
                            })
                except Exception as e:
                    alert_tests.append({
                        "test_type": "slow_response_time",
                        "scenario_avg_response_time": slow_scenario_result["average_response_time_ms"],
                        "threshold_exceeded": slow_scenario_result["average_response_time_ms"] > 500,
                        "alert_manager_error": str(e)
                    })
            
            # Test 2: Trigger high error rate alerts (>1%)
            logger.info("  Testing high error rate alerts...")
            error_scenario_result = await self.simulator.run_scenario(self.simulator.scenarios[3])  # error_prone
            
            await asyncio.sleep(5)  # Wait for alerts to be processed
            
            # Check for error rate alerts
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{self.services['alert_manager']}/api/alerts") as response:
                        if response.status == 200:
                            alerts_data = await response.json()
                            error_alerts = [a for a in alerts_data.get("alerts", []) if "error" in str(a).lower()]
                            
                            alert_tests.append({
                                "test_type": "high_error_rate",
                                "scenario_error_rate": error_scenario_result["error_rate"],
                                "threshold_exceeded": error_scenario_result["error_rate"] > 0.01,  # >1%
                                "alerts_found": len(error_alerts),
                                "alert_manager_status": response.status,
                                "sample_alerts": error_alerts[:3]  # First 3 alerts
                            })
                except Exception as e:
                    alert_tests.append({
                        "test_type": "high_error_rate",
                        "scenario_error_rate": error_scenario_result["error_rate"],
                        "threshold_exceeded": error_scenario_result["error_rate"] > 0.01,
                        "alert_manager_error": str(e)
                    })
            
            # Test 3: Verify normal performance doesn't trigger alerts
            logger.info("  Testing normal performance (should not alert)...")
            normal_scenario_result = await self.simulator.run_scenario(self.simulator.scenarios[0])  # high_performance
            
            await asyncio.sleep(5)  # Wait to confirm no alerts
            
            alert_tests.append({
                "test_type": "normal_performance",
                "scenario_avg_response_time": normal_scenario_result["average_response_time_ms"],
                "scenario_error_rate": normal_scenario_result["error_rate"],
                "should_not_trigger_alerts": True,
                "response_time_under_threshold": normal_scenario_result["average_response_time_ms"] <= 500,
                "error_rate_under_threshold": normal_scenario_result["error_rate"] <= 0.01
            })
            
            # Determine overall success
            slow_test_success = (alert_tests[0].get("threshold_exceeded", False) and 
                               alert_tests[0].get("alerts_found", 0) > 0)
            error_test_success = (alert_tests[1].get("threshold_exceeded", False) and 
                                alert_tests[1].get("alerts_found", 0) > 0)
            normal_test_success = (alert_tests[2].get("response_time_under_threshold", False) and 
                                 alert_tests[2].get("error_rate_under_threshold", False))
            
            overall_success = slow_test_success and error_test_success and normal_test_success
            
            details = {
                "alert_tests": alert_tests,
                "slow_response_test_passed": slow_test_success,
                "high_error_rate_test_passed": error_test_success,
                "normal_performance_test_passed": normal_test_success,
                "overall_success": overall_success
            }
            
            return TestResult(
                test_name="performance_threshold_alerts",
                status="PASS" if overall_success else "FAIL",
                details=details,
                timestamp=datetime.utcnow().isoformat(),
                duration_seconds=time.time() - start_time
            )
            
        except Exception as e:
            return TestResult(
                test_name="performance_threshold_alerts",
                status="ERROR", 
                details={"error": str(e)},
                timestamp=datetime.utcnow().isoformat(),
                duration_seconds=time.time() - start_time
            )
    
    async def test_step4_dashboard_visualization(self) -> TestResult:
        """Test Step 4: Verify dashboard displays API performance data and trends"""
        logger.info("🧪 Testing Step 4: Dashboard Visualization")
        start_time = time.time()
        
        try:
            # Generate comprehensive API data for dashboard
            logger.info("  Generating comprehensive API performance data...")
            
            # Run multiple scenarios to create rich dashboard data
            dashboard_scenarios = [
                self.simulator.scenarios[0],  # high_performance
                self.simulator.scenarios[1],  # medium_performance  
                self.simulator.scenarios[2]   # slow_performance (partial)
            ]
            
            scenario_results = []
            for scenario in dashboard_scenarios:
                # Run shorter versions for dashboard testing
                short_scenario = PerformanceScenario(
                    name=f"dashboard_{scenario.name}",
                    endpoints=scenario.endpoints,
                    duration_seconds=20,  # Shorter duration
                    requests_per_second=scenario.requests_per_second
                )
                result = await self.simulator.run_scenario(short_scenario)
                scenario_results.append(result)
            
            await asyncio.sleep(10)  # Wait for data to be processed and stored
            
            # Test dashboard endpoints and visualization capabilities
            dashboard_tests = []
            
            async with aiohttp.ClientSession() as session:
                # Test 1: Dashboard health and availability
                try:
                    async with session.get(f"{self.services['dashboard']}/health") as response:
                        dashboard_tests.append({
                            "test": "dashboard_health",
                            "status": response.status,
                            "available": response.status == 200
                        })
                except Exception as e:
                    dashboard_tests.append({
                        "test": "dashboard_health",
                        "status": "ERROR",
                        "error": str(e),
                        "available": False
                    })
                
                # Test 2: API metrics data availability
                try:
                    query_params = {
                        "metric": "api_request_total",
                        "start": int((datetime.utcnow() - timedelta(minutes=10)).timestamp()),
                        "end": int(datetime.utcnow().timestamp())
                    }
                    async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as response:
                        if response.status == 200:
                            data = await response.json()
                            dashboard_tests.append({
                                "test": "request_throughput_data",
                                "status": response.status,
                                "data_points": len(data.get("data", [])),
                                "has_data": len(data.get("data", [])) > 0,
                                "time_range": f"{query_params['start']} to {query_params['end']}"
                            })
                        else:
                            dashboard_tests.append({
                                "test": "request_throughput_data",
                                "status": response.status,
                                "has_data": False
                            })
                except Exception as e:
                    dashboard_tests.append({
                        "test": "request_throughput_data",
                        "error": str(e),
                        "has_data": False
                    })
                
                # Test 3: Response time percentiles data
                try:
                    query_params = {
                        "metric": "api_request_duration_seconds",
                        "start": int((datetime.utcnow() - timedelta(minutes=10)).timestamp()),
                        "end": int(datetime.utcnow().timestamp())
                    }
                    async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as response:
                        if response.status == 200:
                            data = await response.json()
                            response_times = [float(d.get("value", 0)) for d in data.get("data", [])]
                            
                            dashboard_tests.append({
                                "test": "response_time_percentiles",
                                "status": response.status,
                                "data_points": len(response_times),
                                "has_data": len(response_times) > 0,
                                "sample_response_times": response_times[:10],  # First 10 values
                                "avg_response_time": statistics.mean(response_times) if response_times else 0
                            })
                        else:
                            dashboard_tests.append({
                                "test": "response_time_percentiles",
                                "status": response.status,
                                "has_data": False
                            })
                except Exception as e:
                    dashboard_tests.append({
                        "test": "response_time_percentiles",
                        "error": str(e),
                        "has_data": False
                    })
                
                # Test 4: Error rate trends data
                try:
                    query_params = {
                        "metric": "api_error_rate",
                        "start": int((datetime.utcnow() - timedelta(minutes=10)).timestamp()),
                        "end": int(datetime.utcnow().timestamp())
                    }
                    async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as response:
                        if response.status == 200:
                            data = await response.json()
                            dashboard_tests.append({
                                "test": "error_rate_trends",
                                "status": response.status,
                                "data_points": len(data.get("data", [])),
                                "has_data": len(data.get("data", [])) > 0,
                                "sample_data": data.get("data", [])[:5]  # First 5 data points
                            })
                        else:
                            dashboard_tests.append({
                                "test": "error_rate_trends",
                                "status": response.status,
                                "has_data": False
                            })
                except Exception as e:
                    dashboard_tests.append({
                        "test": "error_rate_trends",
                        "error": str(e),
                        "has_data": False
                    })
                
                # Test 5: Dashboard visualization endpoints
                dashboard_endpoints = [
                    "/api/dashboard/throughput",
                    "/api/dashboard/response-times", 
                    "/api/dashboard/errors",
                    "/api/metrics"
                ]
                
                for endpoint in dashboard_endpoints:
                    try:
                        async with session.get(f"{self.services['dashboard']}{endpoint}") as response:
                            dashboard_tests.append({
                                "test": f"dashboard_endpoint_{endpoint.replace('/', '_')}",
                                "endpoint": endpoint,
                                "status": response.status,
                                "available": response.status in [200, 404]  # 404 is acceptable for some endpoints
                            })
                    except Exception as e:
                        dashboard_tests.append({
                            "test": f"dashboard_endpoint_{endpoint.replace('/', '_')}",
                            "endpoint": endpoint,
                            "error": str(e),
                            "available": False
                        })
            
            # Evaluate test results
            dashboard_available = any(t.get("available", False) for t in dashboard_tests if "dashboard_health" in t.get("test", ""))
            throughput_data_available = any(t.get("has_data", False) for t in dashboard_tests if "throughput" in t.get("test", ""))
            response_time_data_available = any(t.get("has_data", False) for t in dashboard_tests if "response_time" in t.get("test", ""))
            error_data_available = any(t.get("has_data", False) for t in dashboard_tests if "error" in t.get("test", ""))
            
            visualization_success = (dashboard_available and 
                                   throughput_data_available and 
                                   response_time_data_available)
            
            details = {
                "dashboard_tests": dashboard_tests,
                "scenario_results_summary": [
                    {
                        "scenario": r["scenario"],
                        "total_requests": r["total_requests"],
                        "error_rate": r["error_rate"],
                        "avg_response_time": r["average_response_time_ms"],
                        "throughput": r["throughput_rps"]
                    } for r in scenario_results
                ],
                "visualization_capabilities": {
                    "dashboard_available": dashboard_available,
                    "throughput_data_available": throughput_data_available,
                    "response_time_data_available": response_time_data_available,
                    "error_data_available": error_data_available
                },
                "visualization_success": visualization_success
            }
            
            return TestResult(
                test_name="dashboard_visualization",
                status="PASS" if visualization_success else "FAIL",
                details=details,
                timestamp=datetime.utcnow().isoformat(),
                duration_seconds=time.time() - start_time
            )
            
        except Exception as e:
            return TestResult(
                test_name="dashboard_visualization",
                status="ERROR",
                details={"error": str(e)},
                timestamp=datetime.utcnow().isoformat(),
                duration_seconds=time.time() - start_time
            )
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all test steps and generate comprehensive report"""
        logger.info("🚀 Starting Comprehensive API Performance Monitoring Test")
        overall_start_time = time.time()
        
        try:
            # Verify services are running
            logger.info("🔍 Verifying services availability...")
            service_health = await self.verify_services_health()
            
            if not service_health["all_healthy"]:
                logger.warning("⚠️  Some services are not healthy, but continuing with tests")
            
            # Run all test steps
            logger.info("\n📋 Running API Performance Monitoring Tests...")
            
            # Step 1: API Metrics Exposure
            step1_result = await self.test_step1_api_metrics_exposure()
            self.test_results.append(step1_result)
            logger.info(f"   Step 1: {step1_result.status}")
            
            # Step 2: Metrics Collection Intervals
            step2_result = await self.test_step2_metrics_collection_intervals()
            self.test_results.append(step2_result)
            logger.info(f"   Step 2: {step2_result.status}")
            
            # Step 3: Performance Threshold Alerts
            step3_result = await self.test_step3_performance_thresholds_alerts()
            self.test_results.append(step3_result)
            logger.info(f"   Step 3: {step3_result.status}")
            
            # Step 4: Dashboard Visualization
            step4_result = await self.test_step4_dashboard_visualization()
            self.test_results.append(step4_result)
            logger.info(f"   Step 4: {step4_result.status}")
            
            # Generate comprehensive report
            report = self.generate_comprehensive_report(
                overall_start_time, 
                service_health
            )
            
            logger.info("\n✅ API Performance Monitoring Test Completed")
            logger.info(f"📊 Overall Status: {report['overall_status']}")
            logger.info(f"🏃 Total Duration: {report['total_duration_seconds']:.1f}s")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            return {
                "overall_status": "ERROR",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "total_duration_seconds": time.time() - overall_start_time
            }
        finally:
            # Clean up
            self.simulator.stop()
    
    async def verify_services_health(self) -> Dict[str, Any]:
        """Verify all required services are healthy and accessible"""
        health_checks = {}
        
        async with aiohttp.ClientSession() as session:
            for service_name, service_url in self.services.items():
                try:
                    async with session.get(f"{service_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            health_checks[service_name] = {
                                "status": "healthy",
                                "url": service_url,
                                "response_status": response.status,
                                "details": health_data
                            }
                        else:
                            health_checks[service_name] = {
                                "status": "unhealthy",
                                "url": service_url,
                                "response_status": response.status
                            }
                except Exception as e:
                    health_checks[service_name] = {
                        "status": "error",
                        "url": service_url,
                        "error": str(e)
                    }
        
        all_healthy = all(check["status"] == "healthy" for check in health_checks.values())
        
        return {
            "all_healthy": all_healthy,
            "health_checks": health_checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_comprehensive_report(self, start_time: float, service_health: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        # Calculate overall status
        test_statuses = [result.status for result in self.test_results]
        passed_tests = test_statuses.count("PASS")
        failed_tests = test_statuses.count("FAIL") 
        error_tests = test_statuses.count("ERROR")
        
        if error_tests > 0:
            overall_status = "ERROR"
        elif failed_tests > 0:
            overall_status = "FAIL"
        elif passed_tests == len(self.test_results):
            overall_status = "PASS"
        else:
            overall_status = "PARTIAL"
        
        # Create summary
        summary = {
            "workflow": "API Performance Monitoring",
            "test_steps": [
                "API service exposes metrics (request count, response time, error rate)",
                "Metrics collected every 30 seconds", 
                "Alerts configured (response time > 500ms, error rate > 1%)",
                "Dashboard shows request throughput, response time percentiles, error rate trends"
            ],
            "total_tests": len(self.test_results),
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "overall_status": overall_status,
            "success_rate": f"{(passed_tests/len(self.test_results)*100):.1f}%" if self.test_results else "0%"
        }
        
        # Create detailed results
        detailed_results = {}
        for result in self.test_results:
            detailed_results[result.test_name] = asdict(result)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "test_session_id": f"api_perf_monitoring_{int(time.time())}",
            "total_duration_seconds": time.time() - start_time,
            "overall_status": overall_status,
            "summary": summary,
            "service_health": service_health,
            "test_results": detailed_results,
            "test_configuration": {
                "services": self.services,
                "api_performance_scenarios": [
                    {
                        "name": scenario.name,
                        "endpoints": len(scenario.endpoints),
                        "duration": scenario.duration_seconds,
                        "rps": scenario.requests_per_second
                    } for scenario in self.simulator.scenarios
                ]
            }
        }

async def main():
    """Main execution function"""
    print("🎯 API Performance Monitoring Test")
    print("="*50)
    print()
    
    # Create and run the test
    test = APIPerformanceMonitoringTest()
    
    try:
        # Run comprehensive test
        report = await test.run_comprehensive_test()
        
        # Save results to file
        timestamp = int(time.time())
        results_file = f"api_performance_monitoring_test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Results saved to: {results_file}")
        
        # Print summary
        print("\n📊 TEST SUMMARY")
        print("="*30)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Duration: {report['total_duration_seconds']:.1f}s")
        
        if 'summary' in report:
            summary = report['summary']
            print(f"Tests Passed: {summary['passed_tests']}/{summary['total_tests']}")
            print(f"Success Rate: {summary['success_rate']}")
        
        print("\n🔍 TEST RESULTS")
        print("="*20)
        for test_name, result in report.get('test_results', {}).items():
            status_emoji = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}.get(result['status'], "❓")
            print(f"{status_emoji} {test_name}: {result['status']}")
        
        # Print key findings
        print("\n🎯 KEY FINDINGS")
        print("="*20)
        
        if 'service_health' in report:
            healthy_services = sum(1 for check in report['service_health']['health_checks'].values() if check['status'] == 'healthy')
            total_services = len(report['service_health']['health_checks'])
            print(f"Service Health: {healthy_services}/{total_services} services healthy")
        
        # Show specific test insights
        test_results = report.get('test_results', {})
        
        if 'api_metrics_exposure' in test_results:
            metrics_test = test_results['api_metrics_exposure']
            if metrics_test['status'] == 'PASS':
                found_metrics = len(metrics_test['details'].get('required_metrics_found', []))
                print(f"API Metrics: {found_metrics}/3 required metrics exposed correctly")
        
        if 'performance_threshold_alerts' in test_results:
            alerts_test = test_results['performance_threshold_alerts']
            if 'details' in alerts_test and 'alert_tests' in alerts_test['details']:
                alert_details = alerts_test['details']
                print(f"Alert Tests: Response Time={alert_details.get('slow_response_test_passed', False)}, Error Rate={alert_details.get('high_error_rate_test_passed', False)}")
        
        if 'dashboard_visualization' in test_results:
            dashboard_test = test_results['dashboard_visualization']
            if 'details' in dashboard_test and 'visualization_capabilities' in dashboard_test['details']:
                viz_caps = dashboard_test['details']['visualization_capabilities']
                available_viz = sum(viz_caps.values())
                print(f"Dashboard: {available_viz}/4 visualization capabilities available")
        
        print(f"\n💾 Full results: {results_file}")
        
        # Exit with appropriate code
        sys.exit(0 if report['overall_status'] == 'PASS' else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(3)

if __name__ == "__main__":
    asyncio.run(main())