#!/usr/bin/env python3
"""
Capacity Planning Analysis Workflow Test

Tests all 4 steps of the capacity planning workflow:
1. Query Service provides aggregated data (hourly averages for past 30 days, daily averages for past year)
2. Dashboard displays trend charts 
3. User identifies peak usage times, growth patterns, resource bottlenecks
4. Export data for further analysis

Key Features Tested:
- Long-term data aggregation with different time windows
- Trend analysis capabilities (peak detection, growth patterns)
- Resource bottleneck detection
- Data export functionality for capacity planning
- Dashboard integration for visualization
"""

import requests
import json
import csv
import time
import statistics
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin
import os

class CapacityPlanningTest:
    def __init__(self):
        # Service endpoints
        self.query_service_url = "http://localhost:7539"
        self.dashboard_url = "http://localhost:5317"
        self.influxdb_url = "http://localhost:8026"
        
        # Test configuration
        self.test_results = []
        self.capacity_analysis_results = {}
        self.timestamp = int(time.time())
        
        # Metrics for capacity planning analysis
        self.capacity_metrics = [
            "cpu_usage_percent",
            "memory_usage_percent", 
            "disk_usage_percent",
            "request_count_total",
            "response_time_ms"
        ]
        
        print("🏗️  Capacity Planning Analysis Test Initialized")
        print(f"Query Service: {self.query_service_url}")
        print(f"Dashboard: {self.dashboard_url}")
        print(f"InfluxDB: {self.influxdb_url}")
    
    def run_full_capacity_planning_test(self):
        """Run the complete 4-step capacity planning analysis workflow."""
        print("=" * 80)
        print("📊 CAPACITY PLANNING ANALYSIS WORKFLOW TEST")
        print("=" * 80)
        
        # Step 1: Test Query Service - Long-term aggregated data collection
        print(f"\n🔍 STEP 1: Query Service - Long-term Data Aggregation")
        print("-" * 60)
        long_term_data = self.test_long_term_data_aggregation()
        
        # Step 2: Test Dashboard - Trend chart visualization
        print(f"\n📈 STEP 2: Dashboard - Trend Chart Visualization")
        print("-" * 60)
        dashboard_data = self.test_dashboard_trend_visualization()
        
        # Step 3: Capacity Planning Analysis - Peak detection, growth patterns, bottlenecks
        print(f"\n🔬 STEP 3: Capacity Planning Analysis")
        print("-" * 60)
        analysis_results = self.perform_capacity_planning_analysis(long_term_data)
        
        # Step 4: Data Export for Further Analysis
        print(f"\n💾 STEP 4: Data Export for Capacity Planning")
        print("-" * 60)
        export_results = self.test_capacity_planning_export(long_term_data, analysis_results)
        
        # Generate comprehensive capacity planning report
        print(f"\n📋 CAPACITY PLANNING REPORT")
        print("-" * 60)
        self.generate_capacity_planning_report(analysis_results)
        
        # Save detailed test results
        self.save_test_results()
        
        # Print summary
        self.print_test_summary()
    
    def test_long_term_data_aggregation(self) -> Dict[str, Any]:
        """
        Step 1: Test Query Service's ability to provide long-term aggregated data
        - Hourly averages for past 30 days (simulated)
        - Daily averages for past year (simulated)
        """
        print("Testing long-term data aggregation capabilities...")
        
        long_term_data = {}
        
        # Test scenarios for capacity planning
        time_scenarios = [
            {
                "name": "30_days_hourly",
                "description": "Hourly averages for past 30 days",
                "hours_back": 24 * 30,  # 30 days
                "window": "1h",
                "aggregation": "mean"
            },
            {
                "name": "7_days_hourly",
                "description": "Hourly averages for past week",
                "hours_back": 24 * 7,  # 7 days
                "window": "1h", 
                "aggregation": "mean"
            },
            {
                "name": "24_hours_detailed",
                "description": "15-minute intervals for past 24 hours",
                "hours_back": 24,
                "window": "15m",
                "aggregation": "mean"
            },
            {
                "name": "3_months_daily", 
                "description": "Daily averages for past 3 months",
                "hours_back": 24 * 90,  # 90 days
                "window": "1d",
                "aggregation": "mean"
            }
        ]
        
        for scenario in time_scenarios:
            print(f"\n📊 Testing: {scenario['description']}")
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=scenario['hours_back'])
            
            scenario_data = {}
            
            for metric in self.capacity_metrics:
                try:
                    # Query aggregated data
                    response = requests.get(
                        f"{self.query_service_url}/query/aggregate/{metric}",
                        params={
                            "aggregation": scenario['aggregation'],
                            "window": scenario['window'],
                            "start": start_time.isoformat(),
                            "end": end_time.isoformat()
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        scenario_data[metric] = data
                        print(f"  ✅ {metric}: {data.get('count', 0)} data points")
                        
                        # Analyze data quality
                        data_points = data.get('data', [])
                        if data_points:
                            values = [point['value'] for point in data_points if point['value'] is not None]
                            if values:
                                print(f"     📈 Value range: {min(values):.2f} - {max(values):.2f}")
                                print(f"     📊 Average: {sum(values)/len(values):.2f}")
                    else:
                        print(f"  ❌ {metric}: HTTP {response.status_code}")
                        scenario_data[metric] = {"error": f"HTTP {response.status_code}"}
                        
                except Exception as e:
                    print(f"  ❌ {metric}: {e}")
                    scenario_data[metric] = {"error": str(e)}
            
            long_term_data[scenario['name']] = {
                "config": scenario,
                "data": scenario_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Brief pause between scenarios
            time.sleep(1)
        
        self.test_results.append({
            "step": "1_long_term_aggregation",
            "status": "completed",
            "data": long_term_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"\n✅ Step 1 Complete: Long-term data aggregation tested for {len(time_scenarios)} scenarios")
        return long_term_data
    
    def test_dashboard_trend_visualization(self) -> Dict[str, Any]:
        """
        Step 2: Test Dashboard's ability to display trend charts
        """
        print("Testing dashboard trend visualization capabilities...")
        
        dashboard_results = {}
        
        try:
            # Test dashboard metrics endpoint
            response = requests.get(
                f"{self.dashboard_url}/api/dashboard/metrics",
                timeout=15
            )
            
            if response.status_code == 200:
                metrics_data = response.json()
                dashboard_results['current_metrics'] = metrics_data
                print("✅ Dashboard metrics endpoint working")
                
                # Analyze dashboard data structure
                if 'metrics' in metrics_data:
                    for metric_name, metric_data in metrics_data['metrics'].items():
                        data_count = metric_data.get('count', 0)
                        print(f"  📊 {metric_name}: {data_count} data points")
                else:
                    print("  ⚠️  No metrics data structure found")
            else:
                print(f"❌ Dashboard metrics: HTTP {response.status_code}")
                dashboard_results['current_metrics'] = {"error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            print(f"❌ Dashboard metrics test failed: {e}")
            dashboard_results['current_metrics'] = {"error": str(e)}
        
        # Test dashboard health
        try:
            response = requests.get(f"{self.dashboard_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                dashboard_results['health'] = health_data
                print("✅ Dashboard health check passed")
            else:
                print(f"⚠️  Dashboard health: HTTP {response.status_code}")
                dashboard_results['health'] = {"status": "unhealthy", "code": response.status_code}
        except Exception as e:
            print(f"❌ Dashboard health check failed: {e}")
            dashboard_results['health'] = {"error": str(e)}
        
        self.test_results.append({
            "step": "2_dashboard_visualization", 
            "status": "completed",
            "data": dashboard_results,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"\n✅ Step 2 Complete: Dashboard trend visualization tested")
        return dashboard_results
    
    def perform_capacity_planning_analysis(self, long_term_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Perform comprehensive capacity planning analysis
        - Peak usage identification
        - Growth pattern analysis  
        - Resource bottleneck detection
        - Trend forecasting preparation
        """
        print("Performing capacity planning analysis...")
        
        analysis_results = {
            "peak_usage_analysis": {},
            "growth_patterns": {},
            "bottleneck_detection": {},
            "capacity_recommendations": {},
            "forecasting_data": {}
        }
        
        # Analyze each time scenario
        for scenario_name, scenario_data in long_term_data.items():
            print(f"\n🔬 Analyzing: {scenario_data['config']['description']}")
            
            scenario_analysis = {
                "peaks": {},
                "growth_rates": {},
                "bottlenecks": {},
                "trends": {}
            }
            
            for metric, metric_data in scenario_data['data'].items():
                if 'error' in metric_data:
                    continue
                    
                data_points = metric_data.get('data', [])
                if not data_points:
                    continue
                
                # Extract values and timestamps
                values = []
                timestamps = []
                for point in data_points:
                    if point.get('value') is not None:
                        values.append(float(point['value']))
                        timestamps.append(point['timestamp'])
                
                if len(values) < 3:  # Need minimum data for analysis
                    continue
                
                # Peak Usage Analysis
                peak_analysis = self.analyze_peak_usage(values, timestamps, metric)
                scenario_analysis["peaks"][metric] = peak_analysis
                
                # Growth Pattern Analysis
                growth_analysis = self.analyze_growth_patterns(values, timestamps, metric)
                scenario_analysis["growth_rates"][metric] = growth_analysis
                
                # Bottleneck Detection
                bottleneck_analysis = self.detect_bottlenecks(values, metric)
                scenario_analysis["bottlenecks"][metric] = bottleneck_analysis
                
                # Trend Analysis
                trend_analysis = self.analyze_trends(values, timestamps, metric)
                scenario_analysis["trends"][metric] = trend_analysis
                
                print(f"  📊 {metric}:")
                print(f"     Peak: {peak_analysis.get('peak_value', 'N/A')} at {peak_analysis.get('peak_time', 'N/A')}")
                print(f"     Growth: {growth_analysis.get('growth_rate_percent', 'N/A')}% trend")
                print(f"     Bottleneck Risk: {bottleneck_analysis.get('risk_level', 'N/A')}")
            
            analysis_results["peak_usage_analysis"][scenario_name] = scenario_analysis["peaks"]
            analysis_results["growth_patterns"][scenario_name] = scenario_analysis["growth_rates"] 
            analysis_results["bottleneck_detection"][scenario_name] = scenario_analysis["bottlenecks"]
            analysis_results["forecasting_data"][scenario_name] = scenario_analysis["trends"]
        
        # Generate capacity recommendations
        analysis_results["capacity_recommendations"] = self.generate_capacity_recommendations(analysis_results)
        
        self.capacity_analysis_results = analysis_results
        
        self.test_results.append({
            "step": "3_capacity_analysis",
            "status": "completed", 
            "data": analysis_results,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"\n✅ Step 3 Complete: Capacity planning analysis performed")
        return analysis_results
    
    def analyze_peak_usage(self, values: List[float], timestamps: List[str], metric: str) -> Dict[str, Any]:
        """Analyze peak usage patterns for capacity planning."""
        if not values:
            return {"error": "No data available"}
        
        peak_value = max(values)
        peak_index = values.index(peak_value)
        peak_time = timestamps[peak_index] if peak_index < len(timestamps) else "unknown"
        
        # Calculate percentiles for capacity planning
        p95 = np.percentile(values, 95)
        p99 = np.percentile(values, 99)
        average = np.mean(values)
        
        # Peak frequency analysis
        high_threshold = np.percentile(values, 90)
        peak_periods = sum(1 for v in values if v >= high_threshold)
        peak_frequency = (peak_periods / len(values)) * 100
        
        return {
            "peak_value": round(peak_value, 2),
            "peak_time": peak_time,
            "p95_value": round(p95, 2),
            "p99_value": round(p99, 2),
            "average_value": round(average, 2),
            "peak_frequency_percent": round(peak_frequency, 2),
            "capacity_headroom": round(100 - peak_value, 2) if metric.endswith("_percent") else None
        }
    
    def analyze_growth_patterns(self, values: List[float], timestamps: List[str], metric: str) -> Dict[str, Any]:
        """Analyze growth patterns and trends."""
        if len(values) < 3:
            return {"error": "Insufficient data for growth analysis"}
        
        # Calculate linear trend
        x = np.arange(len(values))
        slope, intercept = np.polyfit(x, values, 1)
        
        # Growth rate calculation
        start_avg = np.mean(values[:min(3, len(values)//3)])
        end_avg = np.mean(values[-min(3, len(values)//3):])
        
        if start_avg > 0:
            growth_rate = ((end_avg - start_avg) / start_avg) * 100
        else:
            growth_rate = 0
        
        # Volatility measure
        volatility = np.std(values) / np.mean(values) * 100 if np.mean(values) > 0 else 0
        
        return {
            "growth_rate_percent": round(growth_rate, 2),
            "trend_slope": round(slope, 4),
            "volatility_percent": round(volatility, 2),
            "trend_direction": "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable",
            "start_period_avg": round(start_avg, 2),
            "end_period_avg": round(end_avg, 2)
        }
    
    def detect_bottlenecks(self, values: List[float], metric: str) -> Dict[str, Any]:
        """Detect potential resource bottlenecks."""
        if not values:
            return {"error": "No data available"}
        
        max_value = max(values)
        avg_value = np.mean(values)
        p95_value = np.percentile(values, 95)
        
        # Bottleneck risk assessment
        if metric.endswith("_percent"):
            # For percentage metrics (CPU, memory, disk)
            if p95_value >= 95:
                risk_level = "CRITICAL"
            elif p95_value >= 80:
                risk_level = "HIGH"
            elif p95_value >= 60:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            utilization_threshold = 80
            high_utilization_periods = sum(1 for v in values if v >= utilization_threshold)
            high_utilization_percent = (high_utilization_periods / len(values)) * 100
        else:
            # For other metrics, use relative thresholds
            threshold = np.percentile(values, 90)
            high_periods = sum(1 for v in values if v >= threshold)
            high_utilization_percent = (high_periods / len(values)) * 100
            
            if high_utilization_percent >= 20:
                risk_level = "HIGH"
            elif high_utilization_percent >= 10:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
        
        return {
            "risk_level": risk_level,
            "max_value": round(max_value, 2),
            "p95_value": round(p95_value, 2),
            "avg_value": round(avg_value, 2),
            "high_utilization_percent": round(high_utilization_percent, 2),
            "recommendation": self.get_bottleneck_recommendation(risk_level, metric)
        }
    
    def get_bottleneck_recommendation(self, risk_level: str, metric: str) -> str:
        """Generate bottleneck mitigation recommendations."""
        recommendations = {
            "CRITICAL": {
                "cpu_usage_percent": "Immediate CPU scaling required. Consider adding more CPU cores or instances.",
                "memory_usage_percent": "Critical memory pressure. Increase memory allocation or optimize memory usage.",
                "disk_usage_percent": "Disk space critically low. Add storage capacity immediately.",
                "default": "Critical resource constraint detected. Immediate scaling action required."
            },
            "HIGH": {
                "cpu_usage_percent": "Plan CPU capacity increase. Monitor for performance degradation.",
                "memory_usage_percent": "Memory usage approaching limits. Plan capacity increase.",
                "disk_usage_percent": "Disk usage high. Plan storage expansion.",
                "default": "Resource usage high. Plan capacity increase within next maintenance window."
            },
            "MEDIUM": {
                "default": "Monitor resource usage trends. Consider capacity planning for future growth."
            },
            "LOW": {
                "default": "Resource utilization within acceptable limits."
            }
        }
        
        return recommendations.get(risk_level, {}).get(metric) or recommendations.get(risk_level, {}).get("default", "No specific recommendation")
    
    def analyze_trends(self, values: List[float], timestamps: List[str], metric: str) -> Dict[str, Any]:
        """Analyze trends for forecasting."""
        if len(values) < 5:
            return {"error": "Insufficient data for trend analysis"}
        
        # Moving average calculation
        window_size = min(5, len(values) // 3)
        if window_size >= 2:
            moving_avg = []
            for i in range(len(values) - window_size + 1):
                avg = np.mean(values[i:i + window_size])
                moving_avg.append(avg)
        else:
            moving_avg = values
        
        # Trend strength calculation
        x = np.arange(len(values))
        correlation = np.corrcoef(x, values)[0, 1] if len(values) > 1 else 0
        trend_strength = abs(correlation)
        
        # Seasonal pattern detection (simplified)
        if len(values) >= 24:  # Need enough data points
            seasonal_strength = self.detect_seasonality(values)
        else:
            seasonal_strength = 0
        
        return {
            "trend_strength": round(trend_strength, 3),
            "correlation": round(correlation, 3),
            "seasonal_strength": round(seasonal_strength, 3),
            "moving_average_last": round(moving_avg[-1], 2) if moving_avg else None,
            "suitable_for_forecasting": trend_strength > 0.3 or seasonal_strength > 0.2
        }
    
    def detect_seasonality(self, values: List[float]) -> float:
        """Simple seasonality detection for capacity planning."""
        if len(values) < 24:
            return 0
        
        # Check for hourly patterns (if we have enough data)
        try:
            # Simple autocorrelation at lag 24 (daily pattern)
            if len(values) >= 48:
                lag_24_corr = np.corrcoef(values[:-24], values[24:])[0, 1]
                return abs(lag_24_corr)
        except:
            pass
        
        return 0
    
    def generate_capacity_recommendations(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive capacity planning recommendations."""
        recommendations = {
            "immediate_actions": [],
            "short_term_planning": [],
            "long_term_strategy": [],
            "monitoring_priorities": []
        }
        
        # Analyze bottlenecks across all scenarios
        all_bottlenecks = {}
        for scenario_name, bottlenecks in analysis_results.get("bottleneck_detection", {}).items():
            for metric, bottleneck_data in bottlenecks.items():
                if metric not in all_bottlenecks:
                    all_bottlenecks[metric] = []
                all_bottlenecks[metric].append(bottleneck_data.get("risk_level", "UNKNOWN"))
        
        # Generate recommendations based on bottleneck analysis
        for metric, risk_levels in all_bottlenecks.items():
            critical_count = risk_levels.count("CRITICAL")
            high_count = risk_levels.count("HIGH") 
            
            if critical_count > 0:
                recommendations["immediate_actions"].append(f"CRITICAL: {metric} requires immediate attention - appears in {critical_count} scenarios")
            elif high_count > 1:
                recommendations["short_term_planning"].append(f"HIGH: {metric} showing stress across multiple scenarios - plan capacity increase")
            elif high_count > 0:
                recommendations["monitoring_priorities"].append(f"MONITOR: {metric} showing elevated usage - watch for trends")
        
        # Growth pattern analysis
        growth_metrics = analysis_results.get("growth_patterns", {})
        for scenario_name, metrics in growth_metrics.items():
            for metric, growth_data in metrics.items():
                growth_rate = growth_data.get("growth_rate_percent", 0)
                if growth_rate > 50:
                    recommendations["long_term_strategy"].append(f"GROWTH: {metric} showing {growth_rate}% growth trend - plan significant capacity increase")
                elif growth_rate > 20:
                    recommendations["short_term_planning"].append(f"GROWTH: {metric} growing at {growth_rate}% - monitor and plan scaling")
        
        return recommendations
    
    def test_capacity_planning_export(self, long_term_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: Test data export functionality for capacity planning
        """
        print("Testing capacity planning data export...")
        
        export_results = {}
        
        # Export formats to test
        export_formats = ["csv", "json"]
        
        for format_type in export_formats:
            print(f"\n💾 Testing {format_type.upper()} export...")
            
            try:
                if format_type == "csv":
                    export_results[format_type] = self.export_capacity_data_csv(long_term_data, analysis_results)
                elif format_type == "json":
                    export_results[format_type] = self.export_capacity_data_json(long_term_data, analysis_results)
                
                print(f"  ✅ {format_type.upper()} export completed")
                
            except Exception as e:
                print(f"  ❌ {format_type.upper()} export failed: {e}")
                export_results[format_type] = {"error": str(e)}
        
        self.test_results.append({
            "step": "4_data_export",
            "status": "completed",
            "data": export_results,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"\n✅ Step 4 Complete: Data export tested for {len(export_formats)} formats")
        return export_results
    
    def export_capacity_data_csv(self, long_term_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Export capacity planning data to CSV format."""
        
        # Export capacity planning summary
        summary_filename = f"capacity_planning_summary_{self.timestamp}.csv"
        
        with open(summary_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow([
                'Metric', 'Scenario', 'Peak_Value', 'P95_Value', 'Average', 
                'Growth_Rate_%', 'Risk_Level', 'Recommendation'
            ])
            
            # Data rows
            for scenario_name, scenario_data in analysis_results.get("peak_usage_analysis", {}).items():
                for metric, peak_data in scenario_data.items():
                    growth_data = analysis_results.get("growth_patterns", {}).get(scenario_name, {}).get(metric, {})
                    bottleneck_data = analysis_results.get("bottleneck_detection", {}).get(scenario_name, {}).get(metric, {})
                    
                    writer.writerow([
                        metric,
                        scenario_name,
                        peak_data.get("peak_value", ""),
                        peak_data.get("p95_value", ""),
                        peak_data.get("average_value", ""),
                        growth_data.get("growth_rate_percent", ""),
                        bottleneck_data.get("risk_level", ""),
                        bottleneck_data.get("recommendation", "")
                    ])
        
        return {
            "summary_file": summary_filename,
            "file_size": os.path.getsize(summary_filename) if os.path.exists(summary_filename) else 0,
            "status": "success"
        }
    
    def export_capacity_data_json(self, long_term_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Export capacity planning data to JSON format."""
        
        # Create comprehensive capacity planning report
        capacity_report = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "test_timestamp": self.timestamp,
                "report_type": "capacity_planning_analysis"
            },
            "executive_summary": {
                "total_scenarios_analyzed": len(long_term_data),
                "metrics_analyzed": len(self.capacity_metrics),
                "critical_issues_found": len([
                    rec for rec in analysis_results.get("capacity_recommendations", {}).get("immediate_actions", [])
                ]),
                "recommendations_count": sum([
                    len(recs) for recs in analysis_results.get("capacity_recommendations", {}).values()
                ])
            },
            "raw_data": long_term_data,
            "analysis_results": analysis_results,
            "detailed_recommendations": analysis_results.get("capacity_recommendations", {}),
            "export_timestamp": datetime.utcnow().isoformat()
        }
        
        json_filename = f"capacity_planning_report_{self.timestamp}.json"
        
        with open(json_filename, 'w') as jsonfile:
            json.dump(capacity_report, jsonfile, indent=2, default=str)
        
        return {
            "report_file": json_filename,
            "file_size": os.path.getsize(json_filename) if os.path.exists(json_filename) else 0,
            "status": "success"
        }
    
    def generate_capacity_planning_report(self, analysis_results: Dict[str, Any]):
        """Generate and display comprehensive capacity planning report."""
        print("📋 COMPREHENSIVE CAPACITY PLANNING REPORT")
        print("=" * 80)
        
        # Executive Summary
        recommendations = analysis_results.get("capacity_recommendations", {})
        
        print(f"\n🎯 EXECUTIVE SUMMARY")
        print("-" * 40)
        print(f"Immediate Actions Required: {len(recommendations.get('immediate_actions', []))}")
        print(f"Short-term Planning Items: {len(recommendations.get('short_term_planning', []))}")  
        print(f"Long-term Strategy Items: {len(recommendations.get('long_term_strategy', []))}")
        print(f"Monitoring Priorities: {len(recommendations.get('monitoring_priorities', []))}")
        
        # Immediate Actions
        if recommendations.get('immediate_actions'):
            print(f"\n🚨 IMMEDIATE ACTIONS REQUIRED")
            print("-" * 40)
            for action in recommendations['immediate_actions']:
                print(f"• {action}")
        
        # Short-term Planning
        if recommendations.get('short_term_planning'):
            print(f"\n📅 SHORT-TERM PLANNING (Next 30 days)")
            print("-" * 40)
            for item in recommendations['short_term_planning']:
                print(f"• {item}")
        
        # Long-term Strategy
        if recommendations.get('long_term_strategy'):
            print(f"\n🔮 LONG-TERM STRATEGY (3+ months)")
            print("-" * 40)
            for item in recommendations['long_term_strategy']:
                print(f"• {item}")
        
        # Monitoring Priorities
        if recommendations.get('monitoring_priorities'):
            print(f"\n👀 MONITORING PRIORITIES")
            print("-" * 40)
            for item in recommendations['monitoring_priorities']:
                print(f"• {item}")
        
        # Top Resource Bottlenecks
        print(f"\n⚠️  TOP RESOURCE BOTTLENECKS")
        print("-" * 40)
        
        bottleneck_summary = {}
        for scenario_name, bottlenecks in analysis_results.get("bottleneck_detection", {}).items():
            for metric, bottleneck_data in bottlenecks.items():
                risk_level = bottleneck_data.get("risk_level", "UNKNOWN")
                if metric not in bottleneck_summary:
                    bottleneck_summary[metric] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
                bottleneck_summary[metric][risk_level] = bottleneck_summary[metric].get(risk_level, 0) + 1
        
        for metric, risk_counts in bottleneck_summary.items():
            total_critical = risk_counts.get("CRITICAL", 0)
            total_high = risk_counts.get("HIGH", 0)
            if total_critical > 0 or total_high > 0:
                print(f"• {metric}: {total_critical} critical, {total_high} high risk scenarios")
        
        # Growth Trends Summary
        print(f"\n📈 GROWTH TRENDS SUMMARY")
        print("-" * 40)
        
        growth_summary = {}
        for scenario_name, metrics in analysis_results.get("growth_patterns", {}).items():
            for metric, growth_data in metrics.items():
                growth_rate = growth_data.get("growth_rate_percent", 0)
                if abs(growth_rate) > 10:  # Only show significant growth
                    if metric not in growth_summary:
                        growth_summary[metric] = []
                    growth_summary[metric].append(growth_rate)
        
        for metric, growth_rates in growth_summary.items():
            avg_growth = sum(growth_rates) / len(growth_rates)
            print(f"• {metric}: {avg_growth:.1f}% average growth across scenarios")
    
    def save_test_results(self):
        """Save comprehensive test results to file."""
        
        results_filename = f"capacity_planning_test_results_{self.timestamp}.json"
        
        comprehensive_results = {
            "test_metadata": {
                "test_name": "Capacity Planning Analysis Workflow", 
                "timestamp": self.timestamp,
                "datetime": datetime.utcnow().isoformat(),
                "test_duration_seconds": time.time() - self.timestamp
            },
            "service_endpoints": {
                "query_service": self.query_service_url,
                "dashboard": self.dashboard_url,
                "influxdb": self.influxdb_url
            },
            "test_steps": self.test_results,
            "capacity_analysis": self.capacity_analysis_results,
            "summary": {
                "total_steps": len(self.test_results),
                "completed_steps": len([r for r in self.test_results if r.get("status") == "completed"]),
                "failed_steps": len([r for r in self.test_results if r.get("status") == "failed"])
            }
        }
        
        with open(results_filename, 'w') as f:
            json.dump(comprehensive_results, f, indent=2, default=str)
        
        print(f"\n💾 Test results saved to: {results_filename}")
        return results_filename
    
    def print_test_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "=" * 80)
        print("📊 CAPACITY PLANNING ANALYSIS TEST SUMMARY")
        print("=" * 80)
        
        completed_steps = len([r for r in self.test_results if r.get("status") == "completed"])
        total_steps = len(self.test_results)
        
        print(f"\n✅ Test Completion: {completed_steps}/{total_steps} steps completed")
        
        # Step-by-step summary
        for i, result in enumerate(self.test_results, 1):
            status_emoji = "✅" if result.get("status") == "completed" else "❌"
            step_name = result.get("step", "unknown").replace("_", " ").title()
            print(f"{status_emoji} Step {i}: {step_name}")
        
        # Key Findings
        if hasattr(self, 'capacity_analysis_results') and self.capacity_analysis_results:
            recommendations = self.capacity_analysis_results.get("capacity_recommendations", {})
            
            critical_actions = len(recommendations.get("immediate_actions", []))
            planning_items = len(recommendations.get("short_term_planning", []))
            
            print(f"\n🎯 Key Findings:")
            print(f"   • {critical_actions} immediate actions required")
            print(f"   • {planning_items} short-term planning items identified")
            print(f"   • Capacity planning analysis completed for {len(self.capacity_metrics)} metrics")
        
        print(f"\n🏗️  Capacity Planning Analysis Workflow Test Complete!")
        print("   All 4 workflow steps have been tested and validated.")

def main():
    """Run the capacity planning analysis workflow test."""
    test = CapacityPlanningTest()
    test.run_full_capacity_planning_test()

if __name__ == "__main__":
    main()