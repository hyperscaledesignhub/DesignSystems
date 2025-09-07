#!/bin/bash

echo "🔧 Fixing Service Issues"
echo "======================="

# Add health endpoint to auth service
echo "Adding health endpoint to auth service..."
cat >> auth-service/src/main.py << 'EOF'

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth-service"}
EOF

# Add health endpoint to file service  
echo "Adding health endpoint to file service..."
cat >> file-service/src/main.py << 'EOF'

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "file-service"}
EOF

echo "✅ Health endpoints added!"
echo "🔄 Rebuilding and restarting services..."

# Rebuild and restart affected services
cd auth-service && docker build -t auth-service . && cd ..
cd file-service && docker build -t file-service . && cd ..

# Restart the services
docker stop auth-service file-service
docker rm auth-service file-service

# Start auth service
docker run -d --name auth-service \
    --network bridge \
    -p 9011:9001 \
    -e DB_HOST=172.17.0.1 \
    -e DB_USER=postgres \
    -e DB_PASSWORD=postgres \
    -e DB_NAME=gdrive \
    -e JWT_SECRET_KEY=your-secret-key-change-this-in-production \
    auth-service

# Start file service
docker run -d --name file-service \
    --network bridge \
    -p 9012:9002 \
    -e DB_HOST=172.17.0.1 \
    -e DB_USER=postgres \
    -e DB_PASSWORD=postgres \
    -e DB_NAME=gdrive \
    -e JWT_SECRET_KEY=your-secret-key-change-this-in-production \
    -e STORAGE_ENDPOINT=172.17.0.1:9000 \
    -e STORAGE_ACCESS_KEY=minioadmin \
    -e STORAGE_SECRET_KEY=minioadmin123 \
    -e STORAGE_BUCKET=gdrive-files \
    -e AUTH_SERVICE_URL=http://172.17.0.1:9011 \
    file-service

echo "✅ Services restarted!"
sleep 5

echo "🧪 Testing health endpoints..."
curl -s http://localhost:9011/health
echo ""
curl -s http://localhost:9012/health
echo ""
echo "🎉 Fix complete!"