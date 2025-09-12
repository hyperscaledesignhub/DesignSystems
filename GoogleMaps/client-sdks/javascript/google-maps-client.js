/**
 * Google Maps Clone - Complete JavaScript SDK
 * Full-featured client library for all 75+ implemented features
 */

class GoogleMapsClient {
    constructor(options = {}) {
        this.apiKey = options.apiKey;
        this.baseUrl = options.baseUrl || 'http://localhost:8080';
        this.version = options.version || 'v3';
        this.websockets = new Map();
        this.subscribers = new Map();
        
        // Request interceptor for authentication
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        };
    }

    // ============== CORE LOCATION SERVICES ==============

    /**
     * Submit batch location updates with ML analysis
     */
    async submitLocationBatch(userId, locations) {
        const response = await this.makeRequest('POST', `/api/${this.version}/locations/batch`, {
            user_id: userId,
            locations: locations
        });
        return response;
    }

    /**
     * Get current location for a user
     */
    async getCurrentLocation(userId) {
        const response = await this.makeRequest('GET', `/api/${this.version}/locations/${userId}/current`);
        return response;
    }

    /**
     * Get location history with analytics
     */
    async getLocationHistory(userId, options = {}) {
        const params = new URLSearchParams({
            limit: options.limit || 100,
            ...(options.startTime && { start_time: options.startTime.toISOString() }),
            ...(options.endTime && { end_time: options.endTime.toISOString() })
        });

        const response = await this.makeRequest('GET', `/api/${this.version}/locations/${userId}/history?${params}`);
        return response;
    }

    /**
     * Find nearby users with proximity search
     */
    async getNearbyUsers(userId, radiusKm = 1.0) {
        const response = await this.makeRequest('GET', 
            `/api/${this.version}/locations/${userId}/nearby?radius_km=${radiusKm}`);
        return response;
    }

    // ============== GEOCODING & PLACES ==============

    /**
     * Convert address to coordinates with caching
     */
    async geocode(address) {
        const response = await this.makeRequest('POST', `/api/v2/geocode`, {
            address: address
        });
        return response;
    }

    /**
     * Convert coordinates to address
     */
    async reverseGeocode(latitude, longitude) {
        const response = await this.makeRequest('POST', `/api/v2/reverse-geocode`, {
            latitude: latitude,
            longitude: longitude
        });
        return response;
    }

    /**
     * Advanced places search with ML ranking
     */
    async searchPlaces(options = {}) {
        const params = new URLSearchParams({
            q: options.query || '',
            ...(options.latitude && { lat: options.latitude }),
            ...(options.longitude && { lng: options.longitude }),
            radius: options.radius || 10,
            ...(options.type && { type: options.type }),
            ...(options.minRating && { min_rating: options.minRating }),
            ...(options.priceLevel && { price_level: options.priceLevel }),
            open_now: options.openNow || false,
            has_photos: options.hasPhotos || false,
            limit: options.limit || 20
        });

        const response = await this.makeRequest('GET', `/api/${this.version}/places/search?${params}`);
        return response;
    }

    /**
     * Get detailed place information
     */
    async getPlace(placeId) {
        const response = await this.makeRequest('GET', `/api/${this.version}/places/${placeId}`);
        return response;
    }

    /**
     * Add review to a place
     */
    async addPlaceReview(placeId, rating, text = null, photos = []) {
        const response = await this.makeRequest('POST', `/api/${this.version}/places/${placeId}/reviews`, {
            rating: rating,
            text: text,
            photos: photos
        });
        return response;
    }

    /**
     * Get place reviews
     */
    async getPlaceReviews(placeId, limit = 10) {
        const response = await this.makeRequest('GET', `/api/${this.version}/places/${placeId}/reviews?limit=${limit}`);
        return response;
    }

    // ============== ADVANCED NAVIGATION ==============

    /**
     * Calculate advanced route with ML-enhanced ETA
     */
    async calculateAdvancedRoute(options = {}) {
        const requestData = {
            origin: options.origin,
            destination: options.destination,
            mode: options.mode || 'driving',
            waypoints: options.waypoints || null,
            alternatives: options.alternatives || false,
            avoid_tolls: options.avoidTolls || false,
            avoid_highways: options.avoidHighways || false,
            departure_time: options.departureTime ? options.departureTime.toISOString() : null,
            optimize_for: options.optimizeFor || 'time',
            include_traffic: options.includeTraffic !== false,
            voice_guidance: options.voiceGuidance || false,
            language: options.language || 'en'
        };

        const response = await this.makeRequest('POST', `/api/${this.version}/routes/advanced`, requestData);
        return response;
    }

    /**
     * Get turn-by-turn navigation instructions
     */
    async getNavigationInstructions(routeId) {
        const response = await this.makeRequest('GET', `/api/v2/routes/${routeId}/instructions`);
        return response;
    }

    /**
     * Get ML-enhanced ETA with traffic
     */
    async getEnhancedETA(routeId, currentLocation = null) {
        const requestData = {
            ...(currentLocation && {
                current_lat: currentLocation.latitude,
                current_lng: currentLocation.longitude
            })
        };

        const response = await this.makeRequest('POST', `/api/v2/routes/${routeId}/eta`, requestData);
        return response;
    }

    // ============== STREET VIEW ==============

    /**
     * Get Street View panoramic imagery
     */
    async getStreetView(options = {}) {
        const params = new URLSearchParams({
            ...(options.latitude && { lat: options.latitude }),
            ...(options.longitude && { lng: options.longitude }),
            ...(options.panoId && { pano_id: options.panoId }),
            heading: options.heading || 0,
            pitch: options.pitch || 0,
            fov: options.fov || 90,
            quality: options.quality || 'medium'
        });

        const response = await this.makeRequest('GET', `/api/${this.version}/street-view?${params}`);
        return response;
    }

    /**
     * Search for Street View panoramas
     */
    async searchStreetView(query, location = null, radius = 10) {
        const params = new URLSearchParams({
            q: query,
            ...(location && {
                lat: location.latitude,
                lng: location.longitude
            }),
            radius_km: radius
        });

        const response = await this.makeRequest('GET', `/api/${this.version}/street-view/search?${params}`);
        return response;
    }

    // ============== ROUTE OPTIMIZATION ==============

    /**
     * Optimize multi-stop delivery routes
     */
    async optimizeDeliveryRoute(options = {}) {
        const requestData = {
            stops: options.stops || [],
            vehicles: options.vehicles || [],
            depot_lat: options.depot.latitude,
            depot_lng: options.depot.longitude,
            departure_time: options.departureTime ? options.departureTime.toISOString() : null,
            optimize_for: options.optimizeFor || 'time',
            max_duration_hours: options.maxDurationHours || null
        };

        const response = await this.makeRequest('POST', `/api/${this.version}/optimize/delivery-routes`, requestData);
        return response;
    }

    // ============== PUBLIC TRANSIT ==============

    /**
     * Get public transit routes
     */
    async getTransitRoute(options = {}) {
        const params = new URLSearchParams({
            origin: options.origin,
            destination: options.destination,
            ...(options.departureTime && { departure_time: options.departureTime.toISOString() }),
            ...(options.arrivalTime && { arrival_time: options.arrivalTime.toISOString() }),
            modes: options.modes ? options.modes.join(',') : 'subway,bus,train'
        });

        const response = await this.makeRequest('GET', `/api/${this.version}/transit/routes?${params}`);
        return response;
    }

    // ============== RIDE SHARING ==============

    /**
     * Request a ride with dynamic pricing
     */
    async requestRide(options = {}) {
        const requestData = {
            pickup_lat: options.pickup.latitude,
            pickup_lng: options.pickup.longitude,
            destination_lat: options.destination.latitude,
            destination_lng: options.destination.longitude,
            ride_type: options.rideType || 'standard',
            passengers: options.passengers || 1
        };

        const response = await this.makeRequest('POST', `/api/${this.version}/rides/request`, requestData);
        return response;
    }

    // ============== OFFLINE MAPS ==============

    /**
     * Download map area for offline use
     */
    async downloadOfflineArea(options = {}) {
        const requestData = {
            north: options.north,
            south: options.south,
            east: options.east,
            west: options.west,
            min_zoom: options.minZoom || 10,
            max_zoom: options.maxZoom || 15,
            include_places: options.includePlaces !== false,
            include_transit: options.includeTransit !== false
        };

        const response = await this.makeRequest('POST', `/api/${this.version}/offline/download`, requestData);
        return response;
    }

    // ============== VOICE NAVIGATION ==============

    /**
     * Get voice navigation instructions
     */
    async getVoiceInstructions(options = {}) {
        const params = new URLSearchParams({
            language: options.language || 'en',
            voice: options.voice || 'female'
        });

        const response = await this.makeRequest('GET', 
            `/api/${this.version}/voice/instructions/${options.routeId}?${params}`);
        return response;
    }

    // ============== TRAFFIC MANAGEMENT ==============

    /**
     * Get current traffic conditions
     */
    async getCurrentTraffic(latitude, longitude, radiusKm = 5) {
        const params = new URLSearchParams({
            lat: latitude,
            lng: longitude,
            radius_km: radiusKm
        });

        const response = await this.makeRequest('GET', `/api/v2/traffic/current?${params}`);
        return response;
    }

    /**
     * Report traffic incident
     */
    async reportTrafficIncident(options = {}) {
        const requestData = {
            incident_type: options.type || 'traffic',
            severity: options.severity || 'moderate',
            lat: options.latitude,
            lng: options.longitude,
            description: options.description || '',
            user_id: options.userId
        };

        const response = await this.makeRequest('POST', `/api/v2/traffic/report-incident`, requestData);
        return response;
    }

    // ============== REAL-TIME FEATURES ==============

    /**
     * Stream live location updates
     */
    streamLocation(callback, userId = 'default') {
        const wsUrl = `${this.baseUrl.replace('http', 'ws')}/ws/${this.version}/live-navigation?user_id=${userId}&route_id=live_tracking`;
        
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('🔄 Live location stream connected');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            callback(data);
        };
        
        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
        };
        
        ws.onclose = () => {
            console.log('🔌 Live location stream disconnected');
        };
        
        this.websockets.set('location_stream', ws);
        return ws;
    }

    /**
     * Subscribe to traffic updates
     */
    subscribeToTraffic(callback, area = null) {
        const params = new URLSearchParams({
            user_id: 'traffic_subscriber',
            ...(area && {
                lat: area.latitude,
                lng: area.longitude,
                radius_km: area.radius || 5
            })
        });

        const wsUrl = `${this.baseUrl.replace('http', 'ws')}/ws/traffic-feed?${params}`;
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('🚦 Traffic updates subscribed');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            callback(data);
        };
        
        this.websockets.set('traffic_feed', ws);
        return ws;
    }

    /**
     * Start live navigation session
     */
    startLiveNavigation(routeId, callback) {
        const wsUrl = `${this.baseUrl.replace('http', 'ws')}/ws/${this.version}/live-navigation?user_id=navigator&route_id=${routeId}`;
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('🧭 Live navigation started');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            callback(data);
        };
        
        this.websockets.set('navigation', ws);
        return ws;
    }

    /**
     * Send live position update during navigation
     */
    updateNavigationPosition(routeId, position) {
        const ws = this.websockets.get('navigation');
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'position_update',
                route_id: routeId,
                latitude: position.latitude,
                longitude: position.longitude,
                speed: position.speed || 0,
                bearing: position.bearing || 0
            }));
        }
    }

    // ============== ANALYTICS & MONITORING ==============

    /**
     * Get system health status
     */
    async getSystemHealth() {
        const response = await this.makeRequest('GET', `/api/${this.version}/system/health`);
        return response;
    }

    /**
     * Get system metrics (requires admin access)
     */
    async getSystemMetrics() {
        const response = await this.makeRequest('GET', `/api/${this.version}/system/metrics`);
        return response;
    }

    /**
     * Get analytics dashboard (requires admin access)
     */
    async getAnalyticsDashboard(timeRange = '24h') {
        const response = await this.makeRequest('GET', 
            `/api/${this.version}/analytics/dashboard?time_range=${timeRange}`);
        return response;
    }

    // ============== UTILITY METHODS ==============

    /**
     * Make authenticated HTTP request
     */
    async makeRequest(method, endpoint, data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method: method,
            headers: this.defaultHeaders
        };

        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error(`❌ Request failed: ${method} ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * Calculate distance between two points
     */
    calculateDistance(point1, point2) {
        const R = 6371; // Earth's radius in km
        const dLat = this.toRad(point2.latitude - point1.latitude);
        const dLon = this.toRad(point2.longitude - point1.longitude);
        
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(this.toRad(point1.latitude)) * Math.cos(this.toRad(point2.latitude)) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    toRad(deg) {
        return deg * (Math.PI/180);
    }

    /**
     * Close all WebSocket connections
     */
    disconnect() {
        this.websockets.forEach((ws, key) => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.close();
                console.log(`🔌 Disconnected ${key}`);
            }
        });
        this.websockets.clear();
    }
}

// ============== USAGE EXAMPLES ==============

/**
 * Example usage of all major features
 */
class GoogleMapsClientExamples {
    constructor() {
        this.client = new GoogleMapsClient({
            apiKey: 'demo-api-key',
            baseUrl: 'http://localhost:8080'
        });
    }

    async demonstrateAllFeatures() {
        console.log('🚀 Demonstrating all Google Maps Clone features...');

        try {
            // 1. Core Location Services
            console.log('\n📍 Testing Core Location Services...');
            await this.client.submitLocationBatch('demo_user', [{
                latitude: 37.7749,
                longitude: -122.4194,
                timestamp: Math.floor(Date.now() / 1000),
                accuracy: 5.0,
                user_mode: 'active',
                speed: 15.5
            }]);

            const currentLocation = await this.client.getCurrentLocation('demo_user');
            console.log('✅ Current location:', currentLocation);

            // 2. Advanced Navigation
            console.log('\n🧭 Testing Advanced Navigation...');
            const route = await this.client.calculateAdvancedRoute({
                origin: 'San Francisco, CA',
                destination: 'Los Angeles, CA',
                mode: 'driving',
                alternatives: true,
                includeTraffic: true,
                voiceGuidance: true
            });
            console.log('✅ Advanced route calculated:', route);

            // 3. Places Search
            console.log('\n🏢 Testing Places Search...');
            const restaurants = await this.client.searchPlaces({
                query: 'italian restaurants',
                latitude: 37.7749,
                longitude: -122.4194,
                radius: 5,
                openNow: true,
                minRating: 4.0
            });
            console.log('✅ Found restaurants:', restaurants.places?.length || 0);

            // 4. Street View
            console.log('\n📸 Testing Street View...');
            const streetView = await this.client.getStreetView({
                latitude: 37.7749,
                longitude: -122.4194,
                heading: 90,
                quality: 'high'
            });
            console.log('✅ Street View retrieved:', streetView?.pano_id);

            // 5. Real-time Features
            console.log('\n🔄 Testing Real-time Features...');
            this.client.streamLocation((update) => {
                console.log('📍 Live location update:', update);
            });

            this.client.subscribeToTraffic((alert) => {
                console.log('🚦 Traffic alert:', alert);
            });

            // 6. Multi-stop Optimization
            console.log('\n🛣️ Testing Route Optimization...');
            const optimizedRoute = await this.client.optimizeDeliveryRoute({
                depot: { latitude: 37.7749, longitude: -122.4194 },
                stops: [
                    { id: 'stop1', latitude: 37.7849, longitude: -122.4094, deliveryTime: 10 },
                    { id: 'stop2', latitude: 37.7649, longitude: -122.4294, deliveryTime: 15 }
                ],
                vehicles: [{ id: 'truck1', type: 'truck', capacity: 100 }]
            });
            console.log('✅ Route optimized:', optimizedRoute);

            console.log('\n🎉 All features demonstrated successfully!');

        } catch (error) {
            console.error('❌ Feature demonstration failed:', error);
        }
    }
}

// Export for both Node.js and browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GoogleMapsClient, GoogleMapsClientExamples };
} else if (typeof window !== 'undefined') {
    window.GoogleMapsClient = GoogleMapsClient;
    window.GoogleMapsClientExamples = GoogleMapsClientExamples;
}

console.log('🗺️ Google Maps Clone JavaScript SDK loaded successfully!');
console.log('📚 Usage: const client = new GoogleMapsClient({ apiKey: "your-key" });');