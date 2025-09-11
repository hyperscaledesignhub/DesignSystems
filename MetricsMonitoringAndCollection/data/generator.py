#!/usr/bin/env python3
"""
Data Generator for Metrics Monitoring System Demo
Generates realistic metrics data for testing and demonstration
"""

import time
import random
import json
import requests
from datetime import datetime
from typing import Dict, List, Any
import threading
import argparse

class MetricsGenerator:
    def __init__(self, collector_url: str = "http://localhost:9847"):
        self.collector_url = collector_url
        self.running = False
        self.threads = []
        
        # Define metric patterns
        self.metric_patterns = {
            'cpu': self.generate_cpu_metrics,
            'memory': self.generate_memory_metrics,
            'disk': self.generate_disk_metrics,
            'network': self.generate_network_metrics,
            'application': self.generate_application_metrics,
            'database': self.generate_database_metrics,
            'cache': self.generate_cache_metrics,
            'queue': self.generate_queue_metrics
        }
        
        # Simulated hosts
        self.hosts = [
            'web-server-01', 'web-server-02', 'web-server-03',
            'api-server-01', 'api-server-02',
            'db-master-01', 'db-replica-01',
            'cache-server-01',
            'queue-server-01'
        ]

    def generate_cpu_metrics(self) -> List[Dict[str, Any]]:
        """Generate CPU usage metrics"""
        metrics = []
        for host in self.hosts[:5]:  # Only web and api servers
            # Base load with some variation
            base_load = 30 if 'web' in host else 50
            load = base_load + random.gauss(20, 10)
            load = max(0, min(100, load))  # Clamp between 0-100
            
            metrics.append({
                'name': 'cpu.usage',
                'value': round(load, 2),
                'labels': {
                    'host': host,
                    'type': 'percentage'
                },
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Add per-core metrics
            for core in range(4):
                core_load = load + random.gauss(0, 5)
                metrics.append({
                    'name': 'cpu.core.usage',
                    'value': round(max(0, min(100, core_load)), 2),
                    'labels': {
                        'host': host,
                        'core': str(core),
                        'type': 'percentage'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        return metrics

    def generate_memory_metrics(self) -> List[Dict[str, Any]]:
        """Generate memory usage metrics"""
        metrics = []
        for host in self.hosts[:5]:
            # Memory usage typically more stable
            base_usage = 60 if 'web' in host else 70
            usage = base_usage + random.gauss(10, 5)
            usage = max(0, min(100, usage))
            
            total_gb = 16 if 'web' in host else 32
            used_gb = (usage / 100) * total_gb
            
            metrics.extend([
                {
                    'name': 'memory.usage',
                    'value': round(usage, 2),
                    'labels': {'host': host, 'type': 'percentage'},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'memory.used',
                    'value': round(used_gb, 2),
                    'labels': {'host': host, 'unit': 'GB'},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'memory.available',
                    'value': round(total_gb - used_gb, 2),
                    'labels': {'host': host, 'unit': 'GB'},
                    'timestamp': datetime.utcnow().isoformat()
                }
            ])
        
        return metrics

    def generate_disk_metrics(self) -> List[Dict[str, Any]]:
        """Generate disk usage metrics"""
        metrics = []
        for host in self.hosts:
            # Disk usage changes slowly
            base_usage = 40 + random.random() * 30
            
            metrics.extend([
                {
                    'name': 'disk.usage',
                    'value': round(base_usage, 2),
                    'labels': {'host': host, 'device': '/dev/sda1', 'type': 'percentage'},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'disk.io.read',
                    'value': round(random.random() * 100, 2),
                    'labels': {'host': host, 'device': '/dev/sda1', 'unit': 'MB/s'},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'disk.io.write',
                    'value': round(random.random() * 50, 2),
                    'labels': {'host': host, 'device': '/dev/sda1', 'unit': 'MB/s'},
                    'timestamp': datetime.utcnow().isoformat()
                }
            ])
        
        return metrics

    def generate_network_metrics(self) -> List[Dict[str, Any]]:
        """Generate network metrics"""
        metrics = []
        for host in self.hosts[:5]:
            # Network traffic with spikes
            base_in = 100 + random.random() * 500
            base_out = 50 + random.random() * 300
            
            # Occasional spikes
            if random.random() > 0.9:
                base_in *= 3
                base_out *= 3
            
            metrics.extend([
                {
                    'name': 'network.throughput.in',
                    'value': round(base_in, 2),
                    'labels': {'host': host, 'interface': 'eth0', 'unit': 'Mbps'},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'network.throughput.out',
                    'value': round(base_out, 2),
                    'labels': {'host': host, 'interface': 'eth0', 'unit': 'Mbps'},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'network.packets.dropped',
                    'value': round(random.random() * 10),
                    'labels': {'host': host, 'interface': 'eth0'},
                    'timestamp': datetime.utcnow().isoformat()
                }
            ])
        
        return metrics

    def generate_application_metrics(self) -> List[Dict[str, Any]]:
        """Generate application-level metrics"""
        metrics = []
        endpoints = ['/api/users', '/api/products', '/api/orders', '/api/search']
        
        for host in self.hosts[:3]:  # Web servers only
            for endpoint in endpoints:
                # Request rate varies by endpoint
                base_rate = 100 if 'search' in endpoint else 50
                rate = base_rate + random.gauss(20, 10)
                
                # Response time
                base_time = 50 if 'search' in endpoint else 20
                response_time = base_time + random.gauss(10, 5)
                
                # Error rate (usually low)
                error_rate = max(0, random.gauss(0.5, 0.5))
                
                metrics.extend([
                    {
                        'name': 'http.requests.rate',
                        'value': round(max(0, rate), 2),
                        'labels': {'host': host, 'endpoint': endpoint, 'unit': 'req/s'},
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    {
                        'name': 'http.response.time',
                        'value': round(max(0, response_time), 2),
                        'labels': {'host': host, 'endpoint': endpoint, 'unit': 'ms'},
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    {
                        'name': 'http.error.rate',
                        'value': round(min(100, error_rate), 2),
                        'labels': {'host': host, 'endpoint': endpoint, 'type': 'percentage'},
                        'timestamp': datetime.utcnow().isoformat()
                    }
                ])
        
        return metrics

    def generate_database_metrics(self) -> List[Dict[str, Any]]:
        """Generate database metrics"""
        metrics = []
        
        for host in ['db-master-01', 'db-replica-01']:
            is_master = 'master' in host
            
            # Connection pool
            connections = 50 if is_master else 30
            connections += random.gauss(10, 5)
            
            # Query rate
            query_rate = 200 if is_master else 500  # Replicas handle reads
            query_rate += random.gauss(50, 20)
            
            # Replication lag (replica only)
            if not is_master:
                lag = max(0, random.gauss(100, 50))
                metrics.append({
                    'name': 'db.replication.lag',
                    'value': round(lag, 2),
                    'labels': {'host': host, 'unit': 'ms'},
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            metrics.extend([
                {
                    'name': 'db.connections.active',
                    'value': round(max(0, connections)),
                    'labels': {'host': host},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'db.queries.rate',
                    'value': round(max(0, query_rate), 2),
                    'labels': {'host': host, 'unit': 'queries/s'},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'db.cache.hit.ratio',
                    'value': round(min(100, 85 + random.gauss(5, 3)), 2),
                    'labels': {'host': host, 'type': 'percentage'},
                    'timestamp': datetime.utcnow().isoformat()
                }
            ])
        
        return metrics

    def generate_cache_metrics(self) -> List[Dict[str, Any]]:
        """Generate cache metrics (Redis)"""
        metrics = []
        host = 'cache-server-01'
        
        metrics.extend([
            {
                'name': 'cache.hit.ratio',
                'value': round(min(100, 90 + random.gauss(3, 2)), 2),
                'labels': {'host': host, 'type': 'percentage'},
                'timestamp': datetime.utcnow().isoformat()
            },
            {
                'name': 'cache.memory.usage',
                'value': round(min(100, 40 + random.gauss(10, 5)), 2),
                'labels': {'host': host, 'type': 'percentage'},
                'timestamp': datetime.utcnow().isoformat()
            },
            {
                'name': 'cache.operations.rate',
                'value': round(max(0, 1000 + random.gauss(200, 100)), 2),
                'labels': {'host': host, 'unit': 'ops/s'},
                'timestamp': datetime.utcnow().isoformat()
            },
            {
                'name': 'cache.evictions',
                'value': round(max(0, random.gauss(5, 3))),
                'labels': {'host': host, 'unit': 'keys/s'},
                'timestamp': datetime.utcnow().isoformat()
            }
        ])
        
        return metrics

    def generate_queue_metrics(self) -> List[Dict[str, Any]]:
        """Generate message queue metrics (Kafka)"""
        metrics = []
        host = 'queue-server-01'
        topics = ['metrics', 'events', 'logs']
        
        for topic in topics:
            # Queue depth varies by topic
            base_depth = 100 if topic == 'metrics' else 50
            depth = base_depth + random.gauss(20, 10)
            
            # Message rate
            base_rate = 500 if topic == 'metrics' else 100
            rate = base_rate + random.gauss(50, 20)
            
            metrics.extend([
                {
                    'name': 'queue.depth',
                    'value': round(max(0, depth)),
                    'labels': {'host': host, 'topic': topic},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'queue.messages.rate',
                    'value': round(max(0, rate), 2),
                    'labels': {'host': host, 'topic': topic, 'unit': 'msg/s'},
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'name': 'queue.consumer.lag',
                    'value': round(max(0, random.gauss(10, 5))),
                    'labels': {'host': host, 'topic': topic, 'unit': 'messages'},
                    'timestamp': datetime.utcnow().isoformat()
                }
            ])
        
        return metrics

    def send_metrics(self, metrics: List[Dict[str, Any]]):
        """Send metrics to the collector"""
        try:
            response = requests.post(
                f"{self.collector_url}/api/metrics",
                json={'metrics': metrics},
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            if response.status_code == 200:
                print(f"✓ Sent {len(metrics)} metrics successfully")
            else:
                print(f"✗ Failed to send metrics: {response.status_code}")
        except Exception as e:
            print(f"✗ Error sending metrics: {e}")

    def generate_and_send(self, metric_type: str):
        """Generate and send specific metric type"""
        if metric_type in self.metric_patterns:
            metrics = self.metric_patterns[metric_type]()
            self.send_metrics(metrics)
        else:
            print(f"Unknown metric type: {metric_type}")

    def continuous_generation(self, metric_types: List[str], interval: int):
        """Continuously generate metrics"""
        print(f"Starting continuous generation for: {', '.join(metric_types)}")
        print(f"Interval: {interval} seconds")
        print("Press Ctrl+C to stop...")
        
        self.running = True
        try:
            while self.running:
                for metric_type in metric_types:
                    if metric_type in self.metric_patterns:
                        metrics = self.metric_patterns[metric_type]()
                        self.send_metrics(metrics)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopping generation...")
            self.running = False

    def simulate_scenarios(self):
        """Simulate various scenarios for demo purposes"""
        scenarios = [
            ('normal', self.simulate_normal_load),
            ('spike', self.simulate_traffic_spike),
            ('memory_leak', self.simulate_memory_leak),
            ('disk_full', self.simulate_disk_full),
            ('network_issues', self.simulate_network_issues),
            ('database_slow', self.simulate_database_slowdown)
        ]
        
        print("Available scenarios:")
        for i, (name, _) in enumerate(scenarios, 1):
            print(f"{i}. {name}")
        
        choice = input("Select scenario (1-6): ")
        try:
            scenario_name, scenario_func = scenarios[int(choice) - 1]
            print(f"\nRunning scenario: {scenario_name}")
            scenario_func()
        except (IndexError, ValueError):
            print("Invalid choice")

    def simulate_normal_load(self):
        """Simulate normal system load"""
        print("Simulating normal load for 60 seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 60:
            # Generate all metric types with normal patterns
            for metric_type in ['cpu', 'memory', 'disk', 'network', 'application']:
                metrics = self.metric_patterns[metric_type]()
                self.send_metrics(metrics)
            time.sleep(5)
        
        print("Normal load simulation completed")

    def simulate_traffic_spike(self):
        """Simulate sudden traffic spike"""
        print("Simulating traffic spike...")
        
        # Normal traffic for 20 seconds
        for _ in range(4):
            metrics = self.generate_application_metrics()
            self.send_metrics(metrics)
            time.sleep(5)
        
        print("SPIKE! Increasing traffic 5x...")
        # Spike for 30 seconds
        for _ in range(6):
            metrics = []
            for _ in range(5):  # 5x traffic
                metrics.extend(self.generate_application_metrics())
            self.send_metrics(metrics)
            time.sleep(5)
        
        print("Returning to normal...")
        # Return to normal
        for _ in range(4):
            metrics = self.generate_application_metrics()
            self.send_metrics(metrics)
            time.sleep(5)
        
        print("Traffic spike simulation completed")

    def simulate_memory_leak(self):
        """Simulate gradual memory leak"""
        print("Simulating memory leak on web-server-01...")
        
        base_memory = 50
        for i in range(20):
            # Gradually increase memory usage
            memory_usage = min(95, base_memory + (i * 2))
            
            metrics = [{
                'name': 'memory.usage',
                'value': memory_usage,
                'labels': {'host': 'web-server-01', 'type': 'percentage'},
                'timestamp': datetime.utcnow().isoformat()
            }]
            
            self.send_metrics(metrics)
            print(f"Memory usage: {memory_usage}%")
            time.sleep(3)
        
        print("Memory leak simulation completed")

    def simulate_disk_full(self):
        """Simulate disk filling up"""
        print("Simulating disk full on db-master-01...")
        
        base_usage = 70
        for i in range(15):
            disk_usage = min(99, base_usage + (i * 2))
            
            metrics = [{
                'name': 'disk.usage',
                'value': disk_usage,
                'labels': {'host': 'db-master-01', 'device': '/dev/sda1', 'type': 'percentage'},
                'timestamp': datetime.utcnow().isoformat()
            }]
            
            self.send_metrics(metrics)
            print(f"Disk usage: {disk_usage}%")
            time.sleep(4)
        
        print("Disk full simulation completed")

    def simulate_network_issues(self):
        """Simulate network problems"""
        print("Simulating network issues...")
        
        for i in range(20):
            # Intermittent packet loss
            packet_loss = random.choice([0, 0, 0, 50, 100, 200])
            
            metrics = [{
                'name': 'network.packets.dropped',
                'value': packet_loss,
                'labels': {'host': 'web-server-02', 'interface': 'eth0'},
                'timestamp': datetime.utcnow().isoformat()
            }]
            
            self.send_metrics(metrics)
            if packet_loss > 0:
                print(f"⚠️  Packet loss detected: {packet_loss} packets")
            else:
                print("Network normal")
            time.sleep(3)
        
        print("Network issues simulation completed")

    def simulate_database_slowdown(self):
        """Simulate database performance degradation"""
        print("Simulating database slowdown...")
        
        base_time = 20
        for i in range(15):
            # Gradually increase response time
            response_time = base_time * (1 + i * 0.5)
            
            metrics = [{
                'name': 'db.query.time',
                'value': response_time,
                'labels': {'host': 'db-master-01', 'unit': 'ms'},
                'timestamp': datetime.utcnow().isoformat()
            }]
            
            self.send_metrics(metrics)
            print(f"Query time: {response_time:.1f}ms")
            time.sleep(4)
        
        print("Database slowdown simulation completed")


def main():
    parser = argparse.ArgumentParser(description='Metrics Generator for Demo')
    parser.add_argument('--url', default='http://localhost:9847',
                        help='Metrics collector URL')
    parser.add_argument('--mode', choices=['continuous', 'scenario', 'single'],
                        default='continuous',
                        help='Generation mode')
    parser.add_argument('--types', nargs='+',
                        default=['cpu', 'memory', 'network'],
                        help='Metric types to generate')
    parser.add_argument('--interval', type=int, default=10,
                        help='Generation interval in seconds')
    
    args = parser.parse_args()
    
    generator = MetricsGenerator(args.url)
    
    if args.mode == 'continuous':
        generator.continuous_generation(args.types, args.interval)
    elif args.mode == 'scenario':
        generator.simulate_scenarios()
    elif args.mode == 'single':
        for metric_type in args.types:
            generator.generate_and_send(metric_type)
    
    print("Generation completed")


if __name__ == "__main__":
    main()