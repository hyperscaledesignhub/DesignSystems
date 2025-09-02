#!/usr/bin/env python3
"""
Simple HTTP server to serve the Search Autocomplete UI
"""

import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 12847
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler with CORS support"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def main():
    """Start the HTTP server"""
    
    try:
        with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
            print(f"🚀 Search Autocomplete UI Server starting on port {PORT}")
            print(f"📁 Serving directory: {DIRECTORY}")
            print(f"🌐 Open your browser and go to: http://localhost:{PORT}")
            print(f"❌ Press Ctrl+C to stop the server")
            print()
            
            # Auto-open browser
            try:
                webbrowser.open(f'http://localhost:{PORT}')
            except:
                pass
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        sys.exit(0)
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use. Please stop other services on this port or change the PORT variable.")
        else:
            print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()