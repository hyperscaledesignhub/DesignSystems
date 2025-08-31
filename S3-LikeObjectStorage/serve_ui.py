#!/usr/bin/env python3
"""
Simple HTTP server to serve the S3 Demo UI
Usage: python serve_ui.py [port]
"""

import sys
import os
import http.server
import socketserver
from pathlib import Path

# Default port - using 3000 for familiar web development port
PORT = 3000 if len(sys.argv) < 2 else int(sys.argv[1])

# Change to the directory containing the HTML file
web_dir = Path(__file__).parent
os.chdir(web_dir)

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for all origins (for development)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-User-ID, Authorization')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

try:
    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        print(f"""
🚀 S3 Object Storage Demo UI Server Started!

📱 Open in your browser:
   http://localhost:{PORT}/demo-ui.html

🔧 Make sure your S3 services are running:
   - API Gateway: http://localhost:7841
   - Bucket Service: http://localhost:7861  
   - Object Service: http://localhost:7871
   - Storage Service: http://localhost:7881
   - Metadata Service: http://localhost:7891
   - Identity Service: http://localhost:7851

Press Ctrl+C to stop the server
        """)
        
        httpd.serve_forever()
        
except KeyboardInterrupt:
    print("\n🛑 Server stopped")
    sys.exit(0)
except Exception as e:
    print(f"❌ Error starting server: {e}")
    sys.exit(1)