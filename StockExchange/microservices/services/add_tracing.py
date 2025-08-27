#!/usr/bin/env python3
"""
Script to add tracing to all microservices
"""
import os
import sys

# Template for adding tracing imports
IMPORT_TEMPLATE = """from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from shared.tracing import setup_tracing, instrument_fastapi, TracingMiddleware
"""

# Template for setting up tracing
SETUP_TEMPLATE = """
# Setup tracing
tracer = setup_tracing("{service_name}")

# Add after app initialization
instrument_fastapi(app)
app.add_middleware(TracingMiddleware, service_name="{service_name}")
"""

# Services to instrument
SERVICES = [
    ("user-service", "user-service"),
    ("wallet-service", "wallet-service"),
    ("order-manager", "order-manager"),
    ("matching-engine", "matching-engine"),
    ("market-data-service", "market-data-service"),
    ("risk-manager", "risk-manager"),
    ("reporting-service", "reporting-service"),
    ("notification-service", "notification-service")
]

def add_tracing_to_service(service_dir, service_name):
    """Add tracing to a service's main.py file"""
    main_file = os.path.join(service_dir, "main.py")
    
    if not os.path.exists(main_file):
        print(f"Warning: {main_file} not found")
        return False
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Check if already instrumented
    if "setup_tracing" in content:
        print(f"Service {service_name} already instrumented")
        return True
    
    # Find where to add imports (after other imports)
    import_line = content.find("from fastapi import")
    if import_line == -1:
        print(f"Error: Could not find FastAPI import in {service_name}")
        return False
    
    # Find end of imports section
    lines = content.split('\n')
    import_end_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            import_end_idx = i
    
    # Add tracing imports after other imports
    lines.insert(import_end_idx + 1, IMPORT_TEMPLATE)
    
    # Find app initialization
    app_line_idx = -1
    for i, line in enumerate(lines):
        if "app = FastAPI(" in line:
            app_line_idx = i
            break
    
    if app_line_idx == -1:
        print(f"Error: Could not find FastAPI app initialization in {service_name}")
        return False
    
    # Add tracing setup after app initialization
    setup_code = SETUP_TEMPLATE.format(service_name=service_name)
    lines.insert(app_line_idx + 1, setup_code)
    
    # Write back
    modified_content = '\n'.join(lines)
    with open(main_file, 'w') as f:
        f.write(modified_content)
    
    print(f"Successfully added tracing to {service_name}")
    return True

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for service_dir, service_name in SERVICES:
        full_path = os.path.join(base_dir, service_dir)
        if os.path.exists(full_path):
            add_tracing_to_service(full_path, service_name)
        else:
            print(f"Service directory not found: {full_path}")

if __name__ == "__main__":
    print("Adding OpenTelemetry tracing to all microservices...")
    main()
    print("\nDone! Remember to rebuild Docker images for changes to take effect.")