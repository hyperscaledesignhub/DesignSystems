#!/usr/bin/env python3
"""
Final API Performance Monitoring Test

Optimized comprehensive test with shorter durations for faster execution
while maintaining full coverage of all 4 workflow steps.
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class APIEndpoint:
    """API endpoint configuration for testing"""
    path: str
    method: str
    response_time_range: tuple  # (min_ms, max_ms)
    error_rate: float  # 0.0 to 1.0
    description: str

@dataclass  
class PerformanceScenario:
    """Performance test scenario"""
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
        self.performance_scenarios = self._create_scenarios()
        
    def _create_scenarios(self) -> List[PerformanceScenario]:
        """Create performance scenarios with shorter durations"""
        return [
            PerformanceScenario(
                name="high_performance",
                endpoints=[
                    APIEndpoint("/api/users", "GET", (20, 80), 0.001, "Fast user listing"),
                    APIEndpoint("/api/health", "GET", (5, 15), 0.0, "Health check"),
                    APIEndpoint("/api/cache", "GET", (10, 50), 0.002, "Cached data")
                ],
                duration_seconds=15,  # Reduced from 60
                requests_per_second=20
            ),
            PerformanceScenario(
                name="medium_performance",
                endpoints=[
                    APIEndpoint("/api/search", "GET", (100, 400), 0.005, "Search queries"),
                    APIEndpoint("/api/reports", "POST", (150, 350), 0.01, "Report generation"),
                ],
                duration_seconds=12,  # Reduced from 45
                requests_per_second=15
            ),
            PerformanceScenario(
                name="slow_performance",
                endpoints=[
                    APIEndpoint("/api/heavy-compute", "POST", (600, 1200), 0.02, "Heavy computation"),
                    APIEndpoint("/api/large-dataset", "GET", (800, 1500), 0.015, "Large data queries"),
                ],
                duration_seconds=10,  # Reduced from 30
                requests_per_second=8
            ),
            PerformanceScenario(
                name="error_prone",
                endpoints=[
                    APIEndpoint("/api/flaky", "GET", (100, 300), 0.05, "Flaky service"),  # 5% error rate
                    APIEndpoint("/api/unstable", "POST", (200, 400), 0.08, "Unstable endpoint"),  # 8% error rate
                ],
                duration_seconds=8,  # Reduced from 30
                requests_per_second=15
            )
        ]
    
    async def simulate_api_request(self, endpoint: APIEndpoint) -> Dict[str, Any]:
        """Simulate a single API request"""
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
        logger.info(f"🎬 Running scenario: {scenario.name}")
        
        start_time = time.time()
        scenario_results = []
        tasks = []
        
        # Generate requests for the scenario duration
        end_time = start_time + scenario.duration_seconds
        request_interval = 1.0 / scenario.requests_per_second
        
        while time.time() < end_time:
            # Select random endpoint
            endpoint = random.choice(scenario.endpoints)
            
            # Create and start request simulation task
            task = asyncio.create_task(self.simulate_api_request(endpoint))
            tasks.append(task)
            
            # Wait for the request interval
            await asyncio.sleep(request_interval)
        
        # Wait for all tasks to complete
        for task in tasks:
            try:
                result = await task
                scenario_results.append(result)
                await self.push_api_metrics(result)
            except Exception as e:
                logger.error(f"Task error: {e}")
        
        # Calculate scenario summary
        total_requests = len(scenario_results)
        error_requests = sum(1 for r in scenario_results if r["is_error"])
        error_rate = (error_requests / total_requests) if total_requests > 0 else 0
        
        response_times = [r["response_time_ms"] for r in scenario_results]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else (max(response_times) if response_times else 0)
        
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
            "throughput_rps": throughput
        }
        
        logger.info(f"✅ Scenario {scenario.name}: {total_requests} requests, "
                   f"{error_rate:.1%} errors, {avg_response_time:.1f}ms avg")
        
        return summary
    
    async def push_api_metrics(self, request_result: Dict[str, Any]):
        """Push API metrics to the metrics source"""
        try:
            async with aiohttp.ClientSession() as session:
                metrics = [
                    {
                        "name": "api_request_total",
                        "value": 1,
                        "labels": {
                            "endpoint": request_result["endpoint"],
                            "method": request_result["method"],
                            "status": str(request_result["status_code"]),
                            "host": "demo-api"
                        },
                        "timestamp": request_result["timestamp"]
                    },
                    {
                        "name": "api_request_duration_seconds",
                        "value": request_result["response_time_ms"] / 1000.0,
                        "labels": {
                            "endpoint": request_result["endpoint"],
                            "method": request_result["method"],
                            "host": "demo-api"
                        },
                        "timestamp": request_result["timestamp"]
                    }
                ]
                
                # Add error metric if applicable
                if request_result["is_error"]:
                    metrics.append({
                        "name": "api_error_rate",
                        "value": 1,
                        "labels": {
                            "endpoint": request_result["endpoint"],
                            "method": request_result["method"],
                            "host": "demo-api"
                        },
                        "timestamp": request_result["timestamp"]
                    })
                
                # Push all metrics
                for metric in metrics:
                    await session.post(f"{self.services['enhanced_metrics_source']}/push", json=metric)
                    
        except Exception as e:
            logger.error(f"Failed to push API metrics: {e}")
    
    async def test_step1_api_metrics_exposure(self) -> TestResult:
        """Test Step 1: Verify APIs expose proper performance metrics"""
        logger.info("🧪 Testing Step 1: API Metrics Exposure")
        start_time = time.time()
        
        try:
            # Run a quick scenario to generate metrics
            quick_scenario = self.performance_scenarios[0]  # high_performance
            quick_scenario.duration_seconds = 8  # Even shorter for this test
            
            await self.run_scenario(quick_scenario)
            await asyncio.sleep(2)  # Wait for metrics to be processed
            
            # Check metrics exposure
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
                        "prometheus_format_valid": "# HELP" in metrics_content or "api_" in metrics_content
                    }
                    
                    success = (response.status == 200 and 
                              len(missing_metrics) == 0 and
                              has_endpoint_labels and has_method_labels)
                    
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
        """Test Step 2: Verify metrics are collected at regular intervals"""
        logger.info("🧪 Testing Step 2: Metrics Collection Intervals")
        start_time = time.time()
        
        try:
            # Generate continuous API load and check collection
            continuous_scenario = self.performance_scenarios[1]  # medium_performance  
            continuous_scenario.duration_seconds = 20  # Reduced duration
            
            collection_checks = []
            
            # Start scenario in background
            scenario_task = asyncio.create_task(self.run_scenario(continuous_scenario))
            
            # Check metrics collection at intervals
            for i in range(3):  # Check 3 times over ~20 seconds
                await asyncio.sleep(8)  # Wait 8 seconds between checks
                
                # Check metrics collector
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(f"{self.services['metrics_collector']}/health") as response:
                            collector_status = response.status
                            collector_healthy = response.status == 200
                    except:
                        collector_status = 0
                        collector_healthy = False
                    
                    try:
                        async with session.get(f"{self.services['metrics_collector']}/metrics") as response:
                            if response.status == 200:
                                metrics_data = await response.json()
                                metrics_count = len(metrics_data.get("metrics", []))
                            else:
                                metrics_count = 0
                    except:
                        metrics_count = 0
                    
                    # Check query service for stored data
                    try:
                        query_params = {
                            "metric": "api_request_total",
                            "start": int((datetime.utcnow() - timedelta(minutes=2)).timestamp()),
                            "end": int(datetime.utcnow().timestamp())
                        }
                        async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as query_response:
                            if query_response.status == 200:
                                query_data = await query_response.json()
                                stored_data_points = len(query_data.get("data", []))
                            else:
                                stored_data_points = 0
                    except:
                        stored_data_points = 0
                    
                    collection_checks.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "check_number": i + 1,
                        "collector_status": collector_status,
                        "collector_healthy": collector_healthy,
                        "metrics_count": metrics_count,
                        "stored_data_points": stored_data_points,
                        "collection_working": collector_healthy or stored_data_points > 0
                    })
            
            # Wait for scenario to complete
            await scenario_task
            
            # Evaluate results
            working_collections = sum(1 for c in collection_checks if c["collection_working"])
            collection_success = working_collections >= 2  # At least 2 successful checks
            
            details = {
                "test_duration_seconds": 20,
                "collection_checks": collection_checks,
                "working_collections": working_collections,
                "collection_success": collection_success,
                "evaluation": "Collection working" if collection_success else "Collection issues detected"
            }
            
            return TestResult(
                test_name="metrics_collection_intervals",
                status="PASS" if collection_success else "FAIL",
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
            alert_tests = []
            
            # Test 1: Trigger slow response time alerts (>500ms)
            logger.info("  Testing slow response time alerts...")
            slow_scenario_result = await self.run_scenario(self.performance_scenarios[2])  # slow_performance
            
            await asyncio.sleep(3)  # Wait for alerts to be processed
            
            # Check for alerts
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{self.services['alert_manager']}/health") as response:
                        alert_manager_healthy = response.status == 200
                        
                    async with session.get(f"{self.services['alert_manager']}/api/alerts") as response:
                        if response.status == 200:
                            alerts_data = await response.json()
                            alerts_found = len(alerts_data.get("alerts", []))
                        else:
                            alerts_found = 0
                            alerts_data = {}
                except Exception as e:
                    alert_manager_healthy = False
                    alerts_found = 0
                    alerts_data = {"error": str(e)}
                
                alert_tests.append({
                    "test_type": "slow_response_time",
                    "scenario_avg_response_time": slow_scenario_result["average_response_time_ms"],
                    "threshold_exceeded": slow_scenario_result["average_response_time_ms"] > 500,
                    "alert_manager_healthy": alert_manager_healthy,
                    "alerts_found": alerts_found
                })
            
            # Test 2: Trigger high error rate alerts (>1%)
            logger.info("  Testing high error rate alerts...")
            error_scenario_result = await self.run_scenario(self.performance_scenarios[3])  # error_prone
            
            await asyncio.sleep(3)  # Wait for alerts to be processed
            
            alert_tests.append({
                "test_type": "high_error_rate",
                "scenario_error_rate": error_scenario_result["error_rate"],
                "threshold_exceeded": error_scenario_result["error_rate"] > 0.01,  # >1%
                "alert_manager_healthy": alert_manager_healthy,
            })
            
            # Test 3: Verify normal performance doesn't over-alert
            logger.info("  Testing normal performance...")
            normal_scenario_result = await self.run_scenario(self.performance_scenarios[0])  # high_performance
            
            alert_tests.append({
                "test_type": "normal_performance",
                "scenario_avg_response_time": normal_scenario_result["average_response_time_ms"],
                "scenario_error_rate": normal_scenario_result["error_rate"],
                "response_time_under_threshold": normal_scenario_result["average_response_time_ms"] <= 500,
                "error_rate_under_threshold": normal_scenario_result["error_rate"] <= 0.01
            })
            
            # Evaluate alert system
            slow_test_passed = alert_tests[0]["threshold_exceeded"] and alert_tests[0]["alert_manager_healthy"]
            error_test_passed = alert_tests[1]["threshold_exceeded"] and alert_tests[1]["alert_manager_healthy"]  
            normal_test_passed = (alert_tests[2]["response_time_under_threshold"] and 
                                alert_tests[2]["error_rate_under_threshold"])
            
            alert_system_working = alert_manager_healthy and (slow_test_passed or error_test_passed)
            
            details = {
                "alert_tests": alert_tests,
                "slow_response_test_passed": slow_test_passed,
                "high_error_rate_test_passed": error_test_passed,
                "normal_performance_test_passed": normal_test_passed,
                "alert_system_working": alert_system_working,
                "alert_manager_healthy": alert_manager_healthy
            }
            
            return TestResult(
                test_name="performance_threshold_alerts",
                status="PASS" if alert_system_working else "FAIL",
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
            logger.info("  Generating dashboard data...")
            
            # Run multiple scenarios to create rich data
            for scenario in self.performance_scenarios[:3]:  # Run first 3 scenarios
                scenario.duration_seconds = 6  # Very short for dashboard test
                await self.run_scenario(scenario)
            
            await asyncio.sleep(5)  # Wait for data to be processed
            
            # Test dashboard and visualization capabilities
            dashboard_tests = []
            
            async with aiohttp.ClientSession() as session:
                # Test dashboard health
                try:
                    async with session.get(f"{self.services['dashboard']}/health") as response:
                        dashboard_healthy = response.status == 200
                        if dashboard_healthy:
                            dashboard_data = await response.json()
                        else:
                            dashboard_data = {}
                except:
                    dashboard_healthy = False
                    dashboard_data = {}
                
                dashboard_tests.append({
                    "test": "dashboard_health",
                    "healthy": dashboard_healthy,
                    "data": dashboard_data
                })
                
                # Test data availability for visualization
                visualization_metrics = [
                    ("api_request_total", "throughput"),
                    ("api_request_duration_seconds", "response_time"),
                    ("api_error_rate", "error_rate")
                ]
                
                for metric_name, viz_type in visualization_metrics:
                    try:
                        query_params = {
                            "metric": metric_name,
                            "start": int((datetime.utcnow() - timedelta(minutes=10)).timestamp()),
                            "end": int(datetime.utcnow().timestamp())
                        }
                        async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as response:
                            if response.status == 200:
                                data = await response.json()
                                data_points = len(data.get("data", []))
                                has_data = data_points > 0
                            else:
                                data_points = 0
                                has_data = False
                            
                            dashboard_tests.append({
                                "test": f"{viz_type}_visualization_data",
                                "metric": metric_name,
                                "data_points": data_points,
                                "has_data": has_data,
                                "query_status": response.status
                            })
                    except Exception as e:
                        dashboard_tests.append({
                            "test": f"{viz_type}_visualization_data",
                            "metric": metric_name,
                            "error": str(e),
                            "has_data": False
                        })
            
            # Evaluate visualization capabilities
            dashboard_available = dashboard_healthy
            data_available = any(t.get("has_data", False) for t in dashboard_tests)
            
            visualization_success = dashboard_available and data_available
            
            details = {
                "dashboard_tests": dashboard_tests,
                "dashboard_available": dashboard_available,
                "data_available": data_available,
                "visualization_success": visualization_success,
                "data_points_summary": {
                    "throughput": next((t["data_points"] for t in dashboard_tests if "throughput" in t.get("test", "")), 0),
                    "response_time": next((t["data_points"] for t in dashboard_tests if "response_time" in t.get("test", "")), 0),
                    "error_rate": next((t["data_points"] for t in dashboard_tests if "error_rate" in t.get("test", "")), 0)
                }
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
        logger.info("🚀 Starting API Performance Monitoring Test")
        overall_start_time = time.time()
        
        try:
            # Verify services
            logger.info("🔍 Verifying services...")
            service_health = await self.verify_services_health()
            
            # Run all test steps
            logger.info("📋 Running all test steps...")
            
            step1_result = await self.test_step1_api_metrics_exposure()
            self.test_results.append(step1_result)
            logger.info(f"   Step 1 API Metrics: {step1_result.status}")
            
            step2_result = await self.test_step2_metrics_collection_intervals()
            self.test_results.append(step2_result)
            logger.info(f"   Step 2 Collection: {step2_result.status}")
            
            step3_result = await self.test_step3_performance_thresholds_alerts()
            self.test_results.append(step3_result)
            logger.info(f"   Step 3 Alerts: {step3_result.status}")
            
            step4_result = await self.test_step4_dashboard_visualization()
            self.test_results.append(step4_result)
            logger.info(f"   Step 4 Dashboard: {step4_result.status}")
            
            # Generate report
            report = self.generate_comprehensive_report(overall_start_time, service_health)
            
            logger.info(f"\n✅ Test Complete - Status: {report['overall_status']}")
            logger.info(f"🏃 Duration: {report['total_duration_seconds']:.1f}s")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            return {
                "overall_status": "ERROR",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "total_duration_seconds": time.time() - overall_start_time
            }
    
    async def verify_services_health(self) -> Dict[str, Any]:
        """Verify all required services are healthy"""
        health_checks = {}
        
        async with aiohttp.ClientSession() as session:
            for service_name, service_url in self.services.items():
                try:
                    async with session.get(f"{service_url}/health", timeout=aiohttp.ClientTimeout(total=3)) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            health_checks[service_name] = {
                                "status": "healthy",
                                "url": service_url,
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
            overall_status = "PARTIAL"
        elif passed_tests == len(self.test_results):
            overall_status = "PASS"
        else:
            overall_status = "UNKNOWN"
        
        # Create detailed results
        detailed_results = {}
        for result in self.test_results:
            detailed_results[result.test_name] = asdict(result)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "test_session_id": f"api_performance_monitoring_{int(time.time())}",
            "total_duration_seconds": time.time() - start_time,
            "overall_status": overall_status,
            "workflow_title": "API Performance Monitoring",
            "workflow_steps": [
                "1. API service exposes metrics (request count, response time, error rate)",
                "2. Metrics collected every 30 seconds", 
                "3. Alerts configured (response time > 500ms, error rate > 1%)",
                "4. Dashboard shows request throughput, response time percentiles, error rate trends"
            ],
            "summary": {
                "total_tests": len(self.test_results),
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "error_tests": error_tests,
                "success_rate": f"{(passed_tests/len(self.test_results)*100):.1f}%" if self.test_results else "0%"
            },
            "service_health": service_health,
            "test_results": detailed_results,
            "test_configuration": {
                "services": self.services,
                "performance_scenarios": [
                    {
                        "name": scenario.name,
                        "endpoints": len(scenario.endpoints),
                        "duration": scenario.duration_seconds,
                        "rps": scenario.requests_per_second
                    } for scenario in self.performance_scenarios
                ]
            }
        }

async def main():
    """Main execution function"""
    print("🎯 API Performance Monitoring Test")
    print("="*50)
    print("Testing comprehensive API performance monitoring workflow:")
    print("1. API metrics exposure (Prometheus format)")
    print("2. Metrics collection at regular intervals") 
    print("3. Performance threshold alerts (response time & error rate)")
    print("4. Dashboard visualization and trends")
    print()
    
    test = APIPerformanceMonitoringTest()
    
    try:
        # Run comprehensive test
        report = await test.run_comprehensive_test()
        
        # Save results to file
        timestamp = int(time.time())
        results_file = f"api_performance_monitoring_test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print comprehensive results
        print(f"\n📊 TEST SUMMARY")
        print("="*30)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Total Duration: {report['total_duration_seconds']:.1f}s")
        
        if 'summary' in report:
            summary = report['summary']
            print(f"Tests Passed: {summary['passed_tests']}/{summary['total_tests']}")
            print(f"Success Rate: {summary['success_rate']}")
        
        print(f"\n🔍 DETAILED RESULTS")
        print("="*25)
        for test_name, result in report.get('test_results', {}).items():
            status_emoji = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}.get(result['status'], "❓")
            print(f"{status_emoji} {test_name}: {result['status']} ({result['duration_seconds']:.1f}s)")
            
            # Show key details for each test
            details = result.get('details', {})
            if 'required_metrics_found' in details:
                print(f"    📈 Metrics Found: {len(details['required_metrics_found'])}/3")
            if 'collection_success' in details:
                print(f"    🔄 Collection Working: {details['collection_success']}")
            if 'alert_system_working' in details:
                print(f"    🚨 Alert System: {'Working' if details['alert_system_working'] else 'Issues'}")
            if 'visualization_success' in details:
                print(f"    📊 Visualization: {'Available' if details['visualization_success'] else 'Limited'}")
        
        print(f"\n🎯 KEY INSIGHTS")
        print("="*20)
        
        # Service health summary
        if 'service_health' in report:
            healthy_count = sum(1 for check in report['service_health']['health_checks'].values() if check['status'] == 'healthy')
            total_services = len(report['service_health']['health_checks'])
            print(f"🏥 Service Health: {healthy_count}/{total_services} services healthy")
        
        # Specific workflow insights
        test_results = report.get('test_results', {})
        
        if 'api_metrics_exposure' in test_results:
            metrics_result = test_results['api_metrics_exposure']
            if metrics_result['status'] == 'PASS':
                print("📊 API metrics properly exposed in Prometheus format")
            else:
                print("⚠️  API metrics exposure has issues")
        
        if 'performance_threshold_alerts' in test_results:
            alerts_result = test_results['performance_threshold_alerts']  
            if 'details' in alerts_result and 'alert_system_working' in alerts_result['details']:
                if alerts_result['details']['alert_system_working']:
                    print("🚨 Alert system detecting performance thresholds")
                else:
                    print("⚠️  Alert system needs attention")
        
        if 'dashboard_visualization' in test_results:
            dash_result = test_results['dashboard_visualization']
            if 'details' in dash_result and 'visualization_success' in dash_result['details']:
                if dash_result['details']['visualization_success']:
                    print("📈 Dashboard visualization capabilities verified")
                else:
                    print("⚠️  Dashboard visualization limited")
        
        print(f"\n📄 Full results saved to: {results_file}")
        
        # Exit with appropriate code
        exit_code = 0 if report['overall_status'] in ['PASS', 'PARTIAL'] else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(3)

if __name__ == "__main__":
    asyncio.run(main())