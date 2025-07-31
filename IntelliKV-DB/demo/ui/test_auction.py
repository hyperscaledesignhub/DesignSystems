#!/usr/bin/env python3
"""
Simple test server for auction demo
"""
from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def test():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Auction Test</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            .test { background: #f0f0f0; padding: 20px; margin: 10px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1>🏆 Auction Demo Test</h1>
        <div class="test">
            <p>If you can see this, the server is working!</p>
            <button onclick="testApi()">Test API</button>
            <div id="result"></div>
        </div>
        
        <script>
        function testApi() {
            fetch('/api/test')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('result').innerHTML = 
                        '<p style="color: green;">✅ API Response: ' + JSON.stringify(data) + '</p>';
                })
                .catch(error => {
                    document.getElementById('result').innerHTML = 
                        '<p style="color: red;">❌ Error: ' + error + '</p>';
                });
        }
        console.log('Test page loaded successfully');
        </script>
    </body>
    </html>
    """

@app.route('/api/test')
def api_test():
    return jsonify({"status": "working", "message": "API is functional"})

if __name__ == '__main__':
    print("🧪 Starting test server on http://localhost:8006")
    app.run(host='0.0.0.0', port=8006, debug=True)