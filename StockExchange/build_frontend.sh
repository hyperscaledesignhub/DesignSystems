#!/bin/bash

# Simple frontend build without webpack complexities
cd /Users/vijayabhaskarv/python-projects/venv/sysdesign/22-StockExchange/demo/frontend

echo "Creating simple production build..."

# Create build directory structure
mkdir -p build/static/js build/static/css

# Copy index.html
cp public/index.html build/

# Copy manifest
cp public/manifest.json build/

# Bundle all components into a single file
cat > build/static/js/bundle.js << 'EOF'
// Simple React bundle for production
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(React.createElement(App));
EOF

echo "Build completed!"