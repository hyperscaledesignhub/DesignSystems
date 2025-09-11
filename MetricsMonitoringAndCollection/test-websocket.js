#!/usr/bin/env node

const WebSocket = require('ws');

console.log('🔄 Testing Dashboard WebSocket Connection...');

const ws = new WebSocket('ws://localhost:5317');

ws.on('open', function() {
    console.log('✅ WebSocket connection established');
    console.log('🔄 Waiting for real-time metrics updates...');
});

ws.on('message', function(data) {
    try {
        const message = JSON.parse(data.toString());
        console.log('📊 Received metrics update:', JSON.stringify(message, null, 2));
    } catch (e) {
        console.log('📨 Received message:', data.toString());
    }
});

ws.on('error', function(error) {
    console.log('❌ WebSocket error:', error.message);
});

ws.on('close', function() {
    console.log('🔌 WebSocket connection closed');
    process.exit(0);
});

// Close after 30 seconds
setTimeout(() => {
    console.log('⏰ Test timeout - closing connection');
    ws.close();
}, 30000);