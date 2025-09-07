import random
import hashlib
from typing import List, Dict
import os

class LoadBalancer:
    def __init__(self):
        # Service URLs configuration
        self.services = {
            "auth": [
                os.getenv("AUTH_SERVICE_URL", "http://172.17.0.1:9011")
            ],
            "file": [
                os.getenv("FILE_SERVICE_URL", "http://172.17.0.1:9012")
            ],
            "metadata": [
                os.getenv("METADATA_SERVICE_URL", "http://172.17.0.1:9003")
            ],
            "block": [
                os.getenv("BLOCK_SERVICE_URL", "http://172.17.0.1:9004")
            ],
            "notification": [
                os.getenv("NOTIFICATION_SERVICE_URL", "http://172.17.0.1:9005")
            ]
        }
        
        # For demonstration, we can add multiple instances of same service
        # In production, these would be different instance URLs
        if os.getenv("ENABLE_LOAD_BALANCING", "false").lower() == "true":
            self.services["file"].extend([
                "http://172.17.0.1:9022",
                "http://172.17.0.1:9032"
            ])
    
    def get_service_url(self, service_name: str, strategy: str = "round_robin", user_id: str = None) -> str:
        """Get service URL using specified load balancing strategy"""
        
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")
        
        instances = self.services[service_name]
        
        if len(instances) == 1:
            return instances[0]
        
        if strategy == "random":
            return random.choice(instances)
        
        elif strategy == "hash":
            if user_id:
                # Consistent hashing based on user_id
                hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
                return instances[hash_value % len(instances)]
            else:
                return instances[0]
        
        elif strategy == "round_robin":
            # Simple round-robin (in production, would use shared state)
            return instances[random.randint(0, len(instances) - 1)]
        
        return instances[0]
    
    def health_check(self, service_name: str) -> Dict[str, bool]:
        """Check health of all service instances"""
        if service_name not in self.services:
            return {}
        
        # In a real implementation, this would ping each service
        # For demo, we'll assume all are healthy
        return {url: True for url in self.services[service_name]}
    
    def get_service_stats(self) -> Dict[str, int]:
        """Get statistics about services"""
        return {
            service: len(urls) for service, urls in self.services.items()
        }

load_balancer = LoadBalancer()