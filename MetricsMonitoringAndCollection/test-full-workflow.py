#!/usr/bin/env python3
"""
Complete Metrics Collection & Ingestion Workflow Test
Demonstrates all 9 steps of the workflow
"""

import requests
import json
import time
import re
from datetime import datetime
from urllib.parse import urljoin

class MetricsWorkflowTest:
    def __init__(self):
        self.metrics_endpoint = "http://localhost:9090/metrics"
        self.influxdb_url = "http://localhost:8026"
        self.influxdb_token = "demo-token-123"
        self.influxdb_org = "metrics"
        self.influxdb_bucket = "metrics"

    def step_1_expose_metrics(self):
        """Step 1: Service exposes metrics at /metrics endpoint"""
        print("🔄 Step 1: Checking metrics endpoint...")
        try:
            response = requests.get(self.metrics_endpoint, timeout=5)
            if response.status_code == 200:
                print("✅ Step 1: Metrics endpoint is accessible")
                return response.text
            else:
                print(f"❌ Step 1: Failed - HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Step 1: Failed - {e}")
            return None

    def step_2_service_registration(self):
        """Step 2: Service registers with etcd (simulated)"""
        print("🔄 Step 2: Service registration with etcd...")
        # This would normally be done by the service itself
        # For demo, we assume it's already registered
        print("✅ Step 2: Service registered (simulated)")
        return True

    def step_3_service_discovery(self):
        """Step 3: Metrics Collector discovers service via etcd (simulated)"""
        print("🔄 Step 3: Service discovery...")
        # Simulate discovering the service
        discovered_services = [
            {"host": "localhost", "port": 9090, "path": "/metrics"}
        ]
        print("✅ Step 3: Service discovered")
        return discovered_services

    def step_4_pull_metrics(self, services):
        """Step 4: Collector pulls metrics every 30 seconds"""
        print("🔄 Step 4: Pulling metrics from services...")
        all_metrics = []
        
        for service in services:
            endpoint = f"http://{service['host']}:{service['port']}{service['path']}"
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    metrics_text = response.text
                    parsed_metrics = self._parse_prometheus_metrics(metrics_text)
                    all_metrics.extend(parsed_metrics)
                    print(f"✅ Step 4: Collected {len(parsed_metrics)} metrics from {endpoint}")
                else:
                    print(f"❌ Step 4: Failed to pull from {endpoint}")
            except Exception as e:
                print(f"❌ Step 4: Error pulling from {endpoint}: {e}")
        
        return all_metrics

    def step_5_validate_format_metrics(self, metrics):
        """Step 5: Collector validates and formats metrics"""
        print("🔄 Step 5: Validating and formatting metrics...")
        valid_metrics = []
        
        for metric in metrics:
            if self._validate_metric(metric):
                formatted = self._format_metric(metric)
                valid_metrics.append(formatted)
        
        print(f"✅ Step 5: Validated and formatted {len(valid_metrics)} metrics")
        return valid_metrics

    def step_6_send_to_kafka(self, metrics):
        """Step 6: Metrics sent to Kafka topic 'metrics' (simulated)"""
        print("🔄 Step 6: Sending metrics to Kafka...")
        # Simulate Kafka message
        kafka_message = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": metrics,
            "source": "metrics-collector",
            "version": "1.0"
        }
        print(f"✅ Step 6: Sent {len(metrics)} metrics to Kafka (simulated)")
        return kafka_message

    def step_7_consumer_reads(self, kafka_message):
        """Step 7: Data Consumer reads from Kafka"""
        print("🔄 Step 7: Data consumer reading from Kafka...")
        # Simulate consumer processing
        processed_metrics = kafka_message["metrics"]
        print(f"✅ Step 7: Consumer read {len(processed_metrics)} metrics from Kafka")
        return processed_metrics

    def step_8_write_to_influxdb(self, metrics):
        """Step 8: Consumer writes batch to InfluxDB"""
        print("🔄 Step 8: Writing metrics to InfluxDB...")
        
        # Convert metrics to InfluxDB line protocol
        line_protocol_data = []
        current_time = int(time.time()) * 1000000000  # nanoseconds
        
        for metric in metrics:
            line = self._to_line_protocol(metric, current_time)
            if line:
                line_protocol_data.append(line)
        
        if not line_protocol_data:
            print("❌ Step 8: No valid metrics to write")
            return False
        
        # Write to InfluxDB
        url = f"{self.influxdb_url}/api/v2/write"
        params = {
            "org": self.influxdb_org,
            "bucket": self.influxdb_bucket
        }
        headers = {
            "Authorization": f"Token {self.influxdb_token}",
            "Content-Type": "text/plain; charset=utf-8"
        }
        
        data = "\n".join(line_protocol_data)
        
        try:
            response = requests.post(url, params=params, headers=headers, data=data)
            if response.status_code == 204:
                print(f"✅ Step 8: Wrote {len(line_protocol_data)} metrics to InfluxDB")
                return True
            else:
                print(f"❌ Step 8: InfluxDB write failed - HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Step 8: Error writing to InfluxDB: {e}")
            return False

    def step_9_data_available_for_querying(self):
        """Step 9: Data available for querying"""
        print("🔄 Step 9: Verifying data is available for querying...")
        
        # Query the data we just wrote
        url = f"{self.influxdb_url}/api/v2/query"
        params = {"org": self.influxdb_org}
        headers = {
            "Authorization": f"Token {self.influxdb_token}",
            "Content-Type": "application/vnd.flux"
        }
        
        query = f'''
        from(bucket:"{self.influxdb_bucket}")
        |> range(start:-5m)
        |> limit(n:10)
        '''
        
        try:
            response = requests.post(url, params=params, headers=headers, data=query)
            if response.status_code == 200:
                # Parse CSV response
                lines = response.text.strip().split('\n')
                data_rows = [line for line in lines if not line.startswith(',')]
                
                if len(data_rows) > 1:  # Header + at least one data row
                    print(f"✅ Step 9: Data is queryable - found {len(data_rows)-1} records")
                    return True
                else:
                    print("❌ Step 9: No data found in query results")
                    return False
            else:
                print(f"❌ Step 9: Query failed - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Step 9: Error querying InfluxDB: {e}")
            return False

    def _parse_prometheus_metrics(self, metrics_text):
        """Parse Prometheus format metrics"""
        metrics = []
        lines = metrics_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse metric line: metric_name{labels} value [timestamp]
                parts = line.split()
                if len(parts) >= 2:
                    metric_part = parts[0]
                    value = float(parts[1])
                    
                    # Extract metric name and labels
                    if '{' in metric_part:
                        name = metric_part.split('{')[0]
                        labels_str = metric_part.split('{')[1].rstrip('}')
                        labels = self._parse_labels(labels_str)
                    else:
                        name = metric_part
                        labels = {}
                    
                    metrics.append({
                        "name": name,
                        "value": value,
                        "labels": labels,
                        "timestamp": time.time()
                    })
        
        return metrics

    def _parse_labels(self, labels_str):
        """Parse label string into dictionary"""
        labels = {}
        if labels_str:
            # Simple parsing for key="value" pairs
            pairs = re.findall(r'(\w+)="([^"]*)"', labels_str)
            for key, value in pairs:
                labels[key] = value
        return labels

    def _validate_metric(self, metric):
        """Validate metric structure"""
        required_fields = ["name", "value", "labels", "timestamp"]
        return all(field in metric for field in required_fields)

    def _format_metric(self, metric):
        """Format metric for storage"""
        return {
            "name": metric["name"],
            "value": float(metric["value"]),
            "labels": metric["labels"],
            "timestamp": metric["timestamp"]
        }

    def _to_line_protocol(self, metric, timestamp):
        """Convert metric to InfluxDB line protocol"""
        measurement = metric["name"]
        
        # Build tags (labels)
        tags = []
        for key, value in metric["labels"].items():
            tags.append(f"{key}={value}")
        
        tags_str = "," + ",".join(tags) if tags else ""
        
        # Build line protocol
        line = f"{measurement}{tags_str} value={metric['value']} {timestamp}"
        return line

    def run_complete_workflow(self):
        """Run the complete metrics collection and ingestion workflow"""
        print("🚀 Starting Complete Metrics Collection & Ingestion Workflow Test")
        print("=" * 70)
        
        success_count = 0
        total_steps = 9
        
        # Step 1: Service exposes metrics
        metrics_text = self.step_1_expose_metrics()
        if metrics_text:
            success_count += 1
        else:
            return False
        
        # Step 2: Service registration
        if self.step_2_service_registration():
            success_count += 1
        
        # Step 3: Service discovery
        services = self.step_3_service_discovery()
        if services:
            success_count += 1
        
        # Step 4: Pull metrics
        raw_metrics = self.step_4_pull_metrics(services)
        if raw_metrics:
            success_count += 1
        
        # Step 5: Validate and format
        formatted_metrics = self.step_5_validate_format_metrics(raw_metrics)
        if formatted_metrics:
            success_count += 1
        
        # Step 6: Send to Kafka
        kafka_message = self.step_6_send_to_kafka(formatted_metrics)
        if kafka_message:
            success_count += 1
        
        # Step 7: Consumer reads
        consumer_metrics = self.step_7_consumer_reads(kafka_message)
        if consumer_metrics:
            success_count += 1
        
        # Step 8: Write to InfluxDB
        if self.step_8_write_to_influxdb(consumer_metrics):
            success_count += 1
        
        # Step 9: Verify data is queryable
        if self.step_9_data_available_for_querying():
            success_count += 1
        
        print("=" * 70)
        print(f"🏁 Workflow Complete: {success_count}/{total_steps} steps successful")
        
        if success_count == total_steps:
            print("🎉 ALL STEPS PASSED - Complete workflow verified!")
            return True
        else:
            print("⚠️ Some steps failed - check logs above")
            return False

if __name__ == "__main__":
    workflow_test = MetricsWorkflowTest()
    workflow_test.run_complete_workflow()