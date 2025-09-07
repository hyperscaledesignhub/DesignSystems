#!/usr/bin/env python3
"""
Simple HTTP server to serve the demo UI
Serves the demo on http://localhost:8080
"""

import http.server
import socketserver
import os

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        # Add CORS headers to allow API calls
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

def run_server():
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║            🎉 NEARBY FRIENDS DEMO UI READY! 🎉                ║
║                                                                ║
║  ➤ Open your browser and navigate to:                         ║
║    http://localhost:{PORT}/demo_ui.html                           ║
║                                                                ║
║  ➤ Make sure all services are running:                        ║
║    ./startup.sh                                               ║
║                                                                ║
║  ➤ Demo Features:                                             ║
║    • Real-time location tracking on interactive map           ║
║    • Live WebSocket updates                                   ║
║    • Multiple demo users with friendships                     ║
║    • System metrics dashboard                                 ║
║    • Activity feed                                            ║
║    • Demo scenarios (Rush Hour, Meetup, Moving)               ║
║                                                                ║
║  Press Ctrl+C to stop the server                              ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """)
        
        httpd.serve_forever()

if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n✨ Demo server stopped")
    except OSError as e:
        if e.errno == 48:  # Port already in use
            print(f"❌ Port {PORT} is already in use. Please stop any other servers running on this port.")
        else:
            raise