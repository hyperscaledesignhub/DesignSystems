#!/usr/bin/env python3
"""
Quick API Performance Monitoring Test

A streamlined version of the comprehensive test for faster execution and debugging.
"""

import asyncio
import aiohttp
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuickAPIPerformanceTest:
    """Quick test for API Performance Monitoring workflow"""
    
    def __init__(self):
        self.services = {
            "enhanced_metrics_source": "http://localhost:3001",
            "metrics_collector": "http://localhost:9847", 
            "query_service": "http://localhost:7539",
            "alert_manager": "http://localhost:6428",
            "dashboard": "http://localhost:5317"
        }
    
    async def quick_step1_test(self) -> Dict[str, Any]:
        """Quick test: API Metrics Exposure"""
        logger.info("🧪 Quick Test Step 1: API Metrics Exposure")
        
        try:
            # Push some test API metrics
            test_metrics = [
                {
                    "name": "api_request_total",
                    "value": 1,
                    "labels": {"endpoint": "/api/test", "method": "GET", "status": "200", "host": "demo-api"},
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "name": "api_request_duration_seconds", 
                    "value": 0.150,
                    "labels": {"endpoint": "/api/test", "method": "GET", "host": "demo-api"},
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "name": "api_error_rate",
                    "value": 1,
                    "labels": {"endpoint": "/api/error", "method": "POST", "host": "demo-api"},
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            # Push metrics
            async with aiohttp.ClientSession() as session:
                for metric in test_metrics:
                    async with session.post(f"{self.services['enhanced_metrics_source']}/push", json=metric) as response:
                        if response.status != 201:
                            logger.warning(f"Failed to push metric {metric['name']}: {response.status}")
            
            await asyncio.sleep(2)  # Wait for metrics to be processed
            
            # Check if metrics are exposed
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.services['enhanced_metrics_source']}/metrics") as response:
                    metrics_content = await response.text()
                    
                    # Check for required API metrics
                    required_metrics = ["api_request_total", "api_request_duration_seconds", "api_error_rate"]
                    missing_metrics = [m for m in required_metrics if m not in metrics_content]
                    
                    # Check for labels
                    has_endpoint_labels = "endpoint=" in metrics_content
                    has_method_labels = "method=" in metrics_content
                    has_status_labels = "status=" in metrics_content
                    
                    success = (response.status == 200 and 
                              len(missing_metrics) == 0 and
                              has_endpoint_labels and has_method_labels)
                    
                    return {
                        "status": "PASS" if success else "FAIL",
                        "metrics_found": [m for m in required_metrics if m in metrics_content],
                        "missing_metrics": missing_metrics,
                        "has_labels": has_endpoint_labels and has_method_labels,
                        "response_status": response.status
                    }
                    
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    async def quick_step2_test(self) -> Dict[str, Any]:
        """Quick test: Metrics Collection"""
        logger.info("🧪 Quick Test Step 2: Metrics Collection")
        
        try:
            # Check metrics collector
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.services['metrics_collector']}/health") as response:
                    collector_healthy = response.status == 200
                    
                # Check if collector has metrics endpoint
                try:
                    async with session.get(f"{self.services['metrics_collector']}/metrics") as response:
                        collector_has_data = response.status == 200
                        if collector_has_data:
                            data = await response.json()
                            metrics_count = len(data.get("metrics", []))
                        else:
                            metrics_count = 0
                except:
                    collector_has_data = False
                    metrics_count = 0
                
                # Check query service for stored data
                try:
                    query_params = {
                        "metric": "api_request_total",
                        "start": int((datetime.utcnow() - timedelta(minutes=5)).timestamp()),
                        "end": int(datetime.utcnow().timestamp())
                    }
                    async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as response:
                        query_has_data = response.status == 200
                        if query_has_data:
                            query_data = await response.json()
                            stored_data_points = len(query_data.get("data", []))
                        else:
                            stored_data_points = 0
                except:
                    query_has_data = False
                    stored_data_points = 0
                
                success = collector_healthy or query_has_data
                
                return {
                    "status": "PASS" if success else "FAIL",
                    "collector_healthy": collector_healthy,
                    "collector_has_data": collector_has_data,
                    "metrics_count": metrics_count,
                    "query_has_data": query_has_data,
                    "stored_data_points": stored_data_points
                }
                
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    async def quick_step3_test(self) -> Dict[str, Any]:
        """Quick test: Alert Configuration"""  
        logger.info("🧪 Quick Test Step 3: Alert Configuration")
        
        try:
            # Push metrics that should trigger alerts
            high_response_time_metric = {
                "name": "api_request_duration_seconds",
                "value": 0.8,  # 800ms - should trigger alert
                "labels": {"endpoint": "/api/slow", "method": "GET", "host": "demo-api"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            high_error_rate_metric = {
                "name": "api_error_rate", 
                "value": 0.05,  # 5% error rate - should trigger alert
                "labels": {"endpoint": "/api/error", "method": "POST", "host": "demo-api"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                # Push threshold-exceeding metrics
                for metric in [high_response_time_metric, high_error_rate_metric]:
                    await session.post(f"{self.services['enhanced_metrics_source']}/push", json=metric)
                
                await asyncio.sleep(3)  # Wait for alerts to be processed
                
                # Check alert manager
                try:
                    async with session.get(f"{self.services['alert_manager']}/health") as response:
                        alert_manager_healthy = response.status == 200
                        
                    # Try to get alerts
                    async with session.get(f"{self.services['alert_manager']}/api/alerts") as response:
                        alerts_accessible = response.status in [200, 404]  # 404 is ok if no alerts
                        alerts_data = {}
                        if response.status == 200:
                            alerts_data = await response.json()
                            
                except Exception as e:
                    alert_manager_healthy = False
                    alerts_accessible = False
                    alerts_data = {"error": str(e)}
                
                success = alert_manager_healthy and alerts_accessible
                
                return {
                    "status": "PASS" if success else "FAIL",
                    "alert_manager_healthy": alert_manager_healthy,
                    "alerts_accessible": alerts_accessible,
                    "test_metrics_pushed": ["high_response_time", "high_error_rate"],
                    "alerts_data": alerts_data
                }
                
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    async def quick_step4_test(self) -> Dict[str, Any]:
        """Quick test: Dashboard Visualization"""
        logger.info("🧪 Quick Test Step 4: Dashboard Visualization")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check dashboard health
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
                
                # Check query service for visualization data
                try:
                    # Test throughput data
                    query_params = {
                        "metric": "api_request_total",
                        "start": int((datetime.utcnow() - timedelta(minutes=30)).timestamp()),
                        "end": int(datetime.utcnow().timestamp())
                    }
                    async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as response:
                        throughput_data_available = response.status == 200
                        if throughput_data_available:
                            throughput_data = await response.json()
                            throughput_points = len(throughput_data.get("data", []))
                        else:
                            throughput_points = 0
                    
                    # Test response time data
                    query_params["metric"] = "api_request_duration_seconds"
                    async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as response:
                        response_time_data_available = response.status == 200
                        if response_time_data_available:
                            response_time_data = await response.json()
                            response_time_points = len(response_time_data.get("data", []))
                        else:
                            response_time_points = 0
                    
                    # Test error rate data
                    query_params["metric"] = "api_error_rate"
                    async with session.get(f"{self.services['query_service']}/api/metrics/query", params=query_params) as response:
                        error_data_available = response.status == 200
                        if error_data_available:
                            error_data = await response.json()
                            error_points = len(error_data.get("data", []))
                        else:
                            error_points = 0
                            
                except Exception as e:
                    throughput_data_available = False
                    response_time_data_available = False
                    error_data_available = False
                    throughput_points = response_time_points = error_points = 0
                
                # Check for any available visualization data
                has_visualization_data = (throughput_points > 0 or 
                                        response_time_points > 0 or 
                                        error_points > 0)
                
                success = dashboard_healthy or has_visualization_data
                
                return {
                    "status": "PASS" if success else "FAIL",
                    "dashboard_healthy": dashboard_healthy,
                    "throughput_data_points": throughput_points,
                    "response_time_data_points": response_time_points,
                    "error_data_points": error_points,
                    "has_visualization_data": has_visualization_data,
                    "dashboard_data": dashboard_data
                }
                
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    async def run_quick_test(self) -> Dict[str, Any]:
        """Run all quick tests"""
        logger.info("🚀 Starting Quick API Performance Monitoring Test")
        start_time = time.time()
        
        # Run all test steps
        results = {}
        
        results["step1_api_metrics"] = await self.quick_step1_test()
        results["step2_metrics_collection"] = await self.quick_step2_test() 
        results["step3_alert_thresholds"] = await self.quick_step3_test()
        results["step4_dashboard"] = await self.quick_step4_test()
        
        # Calculate overall status
        statuses = [r["status"] for r in results.values()]
        passed = statuses.count("PASS")
        failed = statuses.count("FAIL")
        errors = statuses.count("ERROR")
        
        if errors > 0:
            overall_status = "ERROR"
        elif failed > 0:
            overall_status = "PARTIAL"
        else:
            overall_status = "PASS"
        
        # Create summary report
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "test_duration_seconds": time.time() - start_time,
            "overall_status": overall_status,
            "summary": {
                "total_tests": len(results),
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "success_rate": f"{(passed/len(results)*100):.1f}%"
            },
            "test_results": results
        }
        
        return report

async def main():
    """Main execution function"""
    print("🎯 Quick API Performance Monitoring Test")
    print("="*50)
    
    test = QuickAPIPerformanceTest()
    
    try:
        report = await test.run_quick_test()
        
        # Save results
        timestamp = int(time.time())
        results_file = f"api_performance_monitoring_quick_test_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print results
        print(f"\n📊 TEST SUMMARY")
        print("="*30)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Duration: {report['test_duration_seconds']:.1f}s")
        print(f"Success Rate: {report['summary']['success_rate']}")
        
        print(f"\n🔍 STEP RESULTS")
        print("="*20)
        for step_name, result in report['test_results'].items():
            status_emoji = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}.get(result['status'], "❓")
            print(f"{status_emoji} {step_name}: {result['status']}")
            
            # Show key details
            if 'metrics_found' in result:
                print(f"    Metrics found: {result['metrics_found']}")
            if 'missing_metrics' in result:
                print(f"    Missing: {result['missing_metrics']}")
            if 'collector_healthy' in result:
                print(f"    Collector healthy: {result['collector_healthy']}")
            if 'alert_manager_healthy' in result:
                print(f"    Alert manager healthy: {result['alert_manager_healthy']}")
            if 'dashboard_healthy' in result:
                print(f"    Dashboard healthy: {result['dashboard_healthy']}")
            if 'has_visualization_data' in result:
                print(f"    Has visualization data: {result['has_visualization_data']}")
        
        print(f"\n💾 Results saved to: {results_file}")
        
        return report['overall_status'] == 'PASS'
        
    except Exception as e:
        print(f"💥 Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)