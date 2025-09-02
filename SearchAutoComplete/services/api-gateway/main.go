package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	"golang.org/x/time/rate"
)

// Configuration
const (
	DefaultQueryServiceHost     = "query-service"
	DefaultQueryServicePort     = "17893"
	DefaultDataCollectionHost   = "data-collection-service"
	DefaultDataCollectionPort   = "18761"
	DefaultRedisHost           = "redis-rate-limit"
	DefaultRedisPort           = "6379"
	AutocompleteRateLimit      = 100  // requests per minute
	AutocompleteBurst          = 10   // burst capacity
	LogSearchRateLimit         = 1000 // requests per minute  
	LogSearchBurst             = 50   // burst capacity
	RequestTimeout             = 10 * time.Second
	MaxRequestSize             = 1024 // 1KB
)

// Rate limiter store
type RateLimiterStore struct {
	redis    *redis.Client
	limiters map[string]*rate.Limiter
}

func NewRateLimiterStore(redisClient *redis.Client) *RateLimiterStore {
	return &RateLimiterStore{
		redis:    redisClient,
		limiters: make(map[string]*rate.Limiter),
	}
}

func (store *RateLimiterStore) GetLimiter(clientIP string, rps rate.Limit, burst int) *rate.Limiter {
	key := fmt.Sprintf("%s:%f:%d", clientIP, float64(rps), burst)
	
	if limiter, exists := store.limiters[key]; exists {
		return limiter
	}
	
	limiter := rate.NewLimiter(rps, burst)
	store.limiters[key] = limiter
	return limiter
}

// Global variables
var (
	rateLimiterStore *RateLimiterStore
	queryServiceURL  string
	dataCollectionURL string
)

// Response structures
type ErrorResponse struct {
	Error string `json:"error"`
}

type ServiceStatus struct {
	Status    string            `json:"status"`
	Timestamp int64             `json:"timestamp"`
	Services  map[string]string `json:"services"`
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func initializeRateLimiter() error {
	host := getEnv("REDIS_HOST", DefaultRedisHost)
	port := getEnv("REDIS_PORT", DefaultRedisPort)
	
	redisClient := redis.NewClient(&redis.Options{
		Addr:         fmt.Sprintf("%s:%s", host, port),
		Password:     "",
		DB:           1, // Use DB 1 for rate limiting
		DialTimeout:  5 * time.Second,
		ReadTimeout:  3 * time.Second,
		WriteTimeout: 3 * time.Second,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err := redisClient.Ping(ctx).Result()
	if err != nil {
		return fmt.Errorf("failed to connect to Redis: %w", err)
	}

	rateLimiterStore = NewRateLimiterStore(redisClient)
	log.Printf("✅ Rate limiter connected to Redis at %s:%s", host, port)
	return nil
}

func initializeServiceURLs() {
	queryServiceHost := getEnv("QUERY_SERVICE_HOST", DefaultQueryServiceHost)
	queryServicePort := getEnv("QUERY_SERVICE_PORT", DefaultQueryServicePort)
	queryServiceURL = fmt.Sprintf("http://%s:%s", queryServiceHost, queryServicePort)

	dataCollectionHost := getEnv("DATA_COLLECTION_HOST", DefaultDataCollectionHost)
	dataCollectionPort := getEnv("DATA_COLLECTION_PORT", DefaultDataCollectionPort)
	dataCollectionURL = fmt.Sprintf("http://%s:%s", dataCollectionHost, dataCollectionPort)

	log.Printf("✅ Query Service URL: %s", queryServiceURL)
	log.Printf("✅ Data Collection URL: %s", dataCollectionURL)
}

// Middleware for rate limiting
func rateLimitMiddleware(rps rate.Limit, burst int) gin.HandlerFunc {
	return func(c *gin.Context) {
		clientIP := c.ClientIP()
		limiter := rateLimiterStore.GetLimiter(clientIP, rps, burst)

		if !limiter.Allow() {
			remaining := 0
			c.Header("X-RateLimit-Remaining", strconv.Itoa(remaining))
			c.Header("Retry-After", "60")
			
			c.JSON(http.StatusTooManyRequests, ErrorResponse{
				Error: "Rate limit exceeded. Please try again later.",
			})
			c.Abort()
			return
		}

		// Add rate limit headers
		// Note: This is a simplified implementation
		c.Header("X-RateLimit-Remaining", "95") // Approximate
		c.Next()
	}
}

// Middleware for request size limiting
func requestSizeLimitMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		if c.Request.ContentLength > MaxRequestSize {
			c.JSON(http.StatusRequestEntityTooLarge, ErrorResponse{
				Error: fmt.Sprintf("Request too large. Maximum size is %d bytes", MaxRequestSize),
			})
			c.Abort()
			return
		}
		c.Next()
	}
}

// Middleware for response time tracking
func responseTimeMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		startTime := time.Now()
		c.Next()
		duration := time.Since(startTime)
		c.Header("X-Response-Time", fmt.Sprintf("%.2fms", float64(duration.Nanoseconds())/1e6))
	}
}

// Proxy function to forward requests
func proxyRequest(c *gin.Context, targetURL string, method string) {
	client := &http.Client{
		Timeout: RequestTimeout,
	}

	// Build target URL
	fullURL := targetURL + c.Request.URL.Path
	if c.Request.URL.RawQuery != "" {
		fullURL += "?" + c.Request.URL.RawQuery
	}

	// Create request
	var body io.Reader
	if method == "POST" {
		if c.Request.Body != nil {
			body = c.Request.Body
		}
	}

	req, err := http.NewRequest(method, fullURL, body)
	if err != nil {
		log.Printf("Error creating request: %v", err)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error: "Failed to create upstream request",
		})
		return
	}

	// Copy headers
	for key, values := range c.Request.Header {
		for _, value := range values {
			req.Header.Add(key, value)
		}
	}

	// Make request
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Upstream request failed: %v", err)
		c.JSON(http.StatusBadGateway, ErrorResponse{
			Error: "Upstream service unavailable",
		})
		return
	}
	defer resp.Body.Close()

	// Copy response headers
	for key, values := range resp.Header {
		for _, value := range values {
			c.Header(key, value)
		}
	}

	// Read response body
	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Error reading response body: %v", err)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error: "Failed to read upstream response",
		})
		return
	}

	// Return response
	c.Data(resp.StatusCode, resp.Header.Get("Content-Type"), responseBody)
}

// HTTP Handlers

func healthHandler(c *gin.Context) {
	services := make(map[string]string)
	
	// Check query service
	client := &http.Client{Timeout: 3 * time.Second}
	if resp, err := client.Get(queryServiceURL + "/health"); err == nil && resp.StatusCode == 200 {
		services["query-service"] = "healthy"
		resp.Body.Close()
	} else {
		services["query-service"] = "unhealthy"
	}

	// Check data collection service  
	if resp, err := client.Get(dataCollectionURL + "/health"); err == nil && resp.StatusCode == 200 {
		services["data-collection"] = "healthy"
		resp.Body.Close()
	} else {
		services["data-collection"] = "unhealthy"
	}

	// Check rate limiter redis
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if _, err := rateLimiterStore.redis.Ping(ctx).Result(); err == nil {
		services["rate-limiter"] = "healthy"
	} else {
		services["rate-limiter"] = "unhealthy"
	}

	status := "healthy"
	for _, serviceStatus := range services {
		if serviceStatus != "healthy" {
			status = "degraded"
			break
		}
	}

	statusCode := http.StatusOK
	if status != "healthy" {
		statusCode = http.StatusServiceUnavailable
	}

	c.JSON(statusCode, ServiceStatus{
		Status:    status,
		Timestamp: time.Now().Unix(),
		Services:  services,
	})
}

func autocompleteHandler(c *gin.Context) {
	// Validate query parameter
	query := strings.TrimSpace(c.Query("q"))
	if query == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error: "Query parameter 'q' is required",
		})
		return
	}

	// Forward to query service with correct path
	client := &http.Client{
		Timeout: RequestTimeout,
	}

	// Build target URL with correct path mapping
	fullURL := queryServiceURL + "/autocomplete"
	if c.Request.URL.RawQuery != "" {
		fullURL += "?" + c.Request.URL.RawQuery
	}

	req, err := http.NewRequest("GET", fullURL, nil)
	if err != nil {
		log.Printf("Error creating request: %v", err)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error: "Failed to create upstream request",
		})
		return
	}

	// Copy headers
	for key, values := range c.Request.Header {
		for _, value := range values {
			req.Header.Add(key, value)
		}
	}

	// Make request
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Upstream request failed: %v", err)
		c.JSON(http.StatusBadGateway, ErrorResponse{
			Error: "Upstream service unavailable",
		})
		return
	}
	defer resp.Body.Close()

	// Copy response headers
	for key, values := range resp.Header {
		for _, value := range values {
			c.Header(key, value)
		}
	}

	// Read response body
	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Error reading response body: %v", err)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error: "Failed to read upstream response",
		})
		return
	}

	// Return response
	c.Data(resp.StatusCode, resp.Header.Get("Content-Type"), responseBody)
}

func logSearchHandler(c *gin.Context) {
	// Basic validation - detailed validation happens in the service
	var requestData map[string]interface{}
	if err := c.ShouldBindJSON(&requestData); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error: "Invalid JSON format",
		})
		return
	}

	// Check if query field exists
	if _, exists := requestData["query"]; !exists {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error: "Missing required field 'query'",
		})
		return
	}

	// Forward to data collection service with correct path
	client := &http.Client{
		Timeout: RequestTimeout,
	}

	// Build target URL with correct path mapping
	fullURL := dataCollectionURL + "/log-query"

	// Re-encode the JSON body
	jsonData, err := json.Marshal(requestData)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error: "Failed to marshal request data",
		})
		return
	}

	req, err := http.NewRequest("POST", fullURL, strings.NewReader(string(jsonData)))
	if err != nil {
		log.Printf("Error creating request: %v", err)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error: "Failed to create upstream request",
		})
		return
	}

	// Copy headers
	for key, values := range c.Request.Header {
		for _, value := range values {
			req.Header.Add(key, value)
		}
	}
	req.Header.Set("Content-Type", "application/json")

	// Make request
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Upstream request failed: %v", err)
		c.JSON(http.StatusBadGateway, ErrorResponse{
			Error: "Upstream service unavailable",
		})
		return
	}
	defer resp.Body.Close()

	// Copy response headers
	for key, values := range resp.Header {
		for _, value := range values {
			c.Header(key, value)
		}
	}

	// Read response body
	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Error reading response body: %v", err)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error: "Failed to read upstream response",
		})
		return
	}

	// Return response
	c.Data(resp.StatusCode, resp.Header.Get("Content-Type"), responseBody)
}

func metricsHandler(c *gin.Context) {
	// Aggregate metrics from all services
	client := &http.Client{Timeout: 5 * time.Second}
	
	metrics := []string{
		"# API Gateway Metrics",
		fmt.Sprintf("api_gateway_timestamp %d", time.Now().Unix()),
	}

	// Try to get metrics from query service
	if resp, err := client.Get(queryServiceURL + "/metrics"); err == nil {
		defer resp.Body.Close()
		if body, err := io.ReadAll(resp.Body); err == nil {
			metrics = append(metrics, "# Query Service Metrics")
			metrics = append(metrics, string(body))
		}
	}

	// Try to get metrics from data collection service
	if resp, err := client.Get(dataCollectionURL + "/metrics"); err == nil {
		defer resp.Body.Close()
		if body, err := io.ReadAll(resp.Body); err == nil {
			metrics = append(metrics, "# Data Collection Service Metrics")
			metrics = append(metrics, string(body))
		}
	}

	c.Data(http.StatusOK, "text/plain", []byte(strings.Join(metrics, "\n")))
}

func configHandler(c *gin.Context) {
	config := map[string]interface{}{
		"services": map[string]string{
			"query_service":     queryServiceURL,
			"data_collection":   dataCollectionURL,
		},
		"rate_limits": map[string]int{
			"autocomplete_per_minute": AutocompleteRateLimit,
			"log_search_per_minute":   LogSearchRateLimit,
		},
		"limits": map[string]int{
			"max_request_size": MaxRequestSize,
		},
		"timeout_ms": int(RequestTimeout / time.Millisecond),
	}

	c.JSON(http.StatusOK, config)
}

func main() {
	// Initialize services
	if err := initializeRateLimiter(); err != nil {
		log.Fatalf("Failed to initialize rate limiter: %v", err)
	}

	initializeServiceURLs()

	// Setup Gin router
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()
	router.Use(gin.Logger(), gin.Recovery())

	// CORS configuration
	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowMethods = []string{"GET", "POST", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Length", "Content-Type", "Authorization"}
	router.Use(cors.New(config))

	// Global middlewares
	router.Use(responseTimeMiddleware())
	router.Use(requestSizeLimitMiddleware())

	// Health and admin endpoints
	router.GET("/health", healthHandler)
	router.GET("/metrics", metricsHandler)
	router.GET("/config", configHandler)

	// API routes with rate limiting
	v1 := router.Group("/v1")
	{
		// Autocomplete endpoint with stricter rate limiting
		v1.GET("/autocomplete", 
			rateLimitMiddleware(rate.Limit(AutocompleteRateLimit)/60, AutocompleteBurst), // per second
			autocompleteHandler)

		// Log search endpoint with higher rate limit
		v1.POST("/log-search",
			rateLimitMiddleware(rate.Limit(LogSearchRateLimit)/60, LogSearchBurst), // per second
			logSearchHandler)
	}

	// Handle 404
	router.NoRoute(func(c *gin.Context) {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Error: "Endpoint not found",
		})
	})

	// Handle 405 Method Not Allowed
	router.NoMethod(func(c *gin.Context) {
		c.JSON(http.StatusMethodNotAllowed, ErrorResponse{
			Error: "Method not allowed",
		})
	})

	// Start server
	port := getEnv("PORT", "19845")
	log.Printf("🚀 API Gateway starting on port %s", port)
	log.Printf("📊 Rate limits: Autocomplete=%d/min, LogSearch=%d/min", AutocompleteRateLimit, LogSearchRateLimit)
	
	if err := router.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}