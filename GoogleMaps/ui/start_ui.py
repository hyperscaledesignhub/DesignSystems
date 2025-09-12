#!/usr/bin/env python3

import sys
import os
import subprocess
import webbrowser
import time
from pathlib import Path

def main():
    print("🚀 Starting Google Maps Clone - Web UI")
    print("======================================")
    
    # Check if backend is running
    try:
        import requests
        response = requests.get("http://localhost:8086/api/locations/stats", timeout=5)
        if response.status_code == 200:
            print("✅ Backend API is running")
        else:
            print("⚠️  Backend API might not be fully ready")
    except Exception as e:
        print("❌ Backend API not accessible. Please start backend services first.")
        print("   Run: ./scripts/start-all-services.sh")
        return
    
    # Start UI server
    print(f"\n🌐 Starting Web UI on http://0.0.0.0:3002")
    print("📱 Features available:")
    print("   - Interactive location testing")  
    print("   - Real-time updates via WebSocket")
    print("   - Performance monitoring")
    print("   - API documentation access")
    
    # Start the UI server
    try:
        import uvicorn
        uvicorn.run(
            "maps_ui:app",
            host="0.0.0.0",
            port=3002,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 UI Server stopped")
    except Exception as e:
        print(f"❌ Error starting UI: {e}")

if __name__ == "__main__":
    main()
