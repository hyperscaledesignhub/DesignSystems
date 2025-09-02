package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	_ "github.com/lib/pq"
)

// Configuration
const (
	DefaultRedisHost    = "redis-cache"
	DefaultRedisPort    = "6379"
	DefaultDBHost       = "postgres"
	DefaultDBPort       = "5432"
	DefaultDBName       = "autocomplete_test"
	DefaultDBUser       = "testuser"
	DefaultDBPassword   = "testpass"
	CacheKeyPrefix      = "trie:prefix:"
	CacheTTL           = 7 * 24 * time.Hour // 7 days
	MaxPrefixLength    = 50
	SuggestionsCount   = 5
)

// Data structures
type Suggestion struct {
	Query     string `json:"query"`
	Frequency int    `json:"frequency"`
	Score     int    `json:"score,omitempty"`
}

type CacheEntry struct {
	Prefix      string       `json:"prefix"`
	Suggestions []Suggestion `json:"suggestions"`
	UpdatedAt   string       `json:"updated_at"`
}

type TrieResponse struct {
	Prefix      string       `json:"prefix"`
	Suggestions []Suggestion `json:"suggestions"`
	CacheHit    bool         `json:"cache_hit"`
	LatencyMs   float64      `json:"latency_ms"`
}

type HealthResponse struct {
	Status    string            `json:"status"`
	Timestamp int64             `json:"timestamp"`
	Services  map[string]string `json:"services"`
}

// Global clients
var (
	redisClient *redis.Client
	dbConn      *sql.DB
)

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func initializeRedis() error {
	host := getEnv("REDIS_HOST", DefaultRedisHost)
	port := getEnv("REDIS_PORT", DefaultRedisPort)
	
	redisClient = redis.NewClient(&redis.Options{
		Addr:         fmt.Sprintf("%s:%s", host, port),
		Password:     "",
		DB:           0,
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

	log.Printf("✅ Connected to Redis at %s:%s", host, port)
	return nil
}

func initializeDatabase() error {
	host := getEnv("DB_HOST", DefaultDBHost)
	port := getEnv("DB_PORT", DefaultDBPort)
	dbname := getEnv("DB_NAME", DefaultDBName)
	user := getEnv("DB_USER", DefaultDBUser)
	password := getEnv("DB_PASSWORD", DefaultDBPassword)

	dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		host, port, user, password, dbname)

	var err error
	dbConn, err = sql.Open("postgres", dsn)
	if err != nil {
		return fmt.Errorf("failed to open database connection: %w", err)
	}

	dbConn.SetMaxOpenConns(10)
	dbConn.SetMaxIdleConns(2)
	dbConn.SetConnMaxLifetime(time.Hour)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := dbConn.PingContext(ctx); err != nil {
		return fmt.Errorf("failed to connect to database: %w", err)
	}

	log.Printf("✅ Connected to Database at %s:%s", host, port)
	return nil
}

func getSuggestionsFromCache(ctx context.Context, prefix string) ([]Suggestion, bool, error) {
	cacheKey := CacheKeyPrefix + prefix
	
	result, err := redisClient.Get(ctx, cacheKey).Result()
	if err == redis.Nil {
		return nil, false, nil // Cache miss
	}
	if err != nil {
		return nil, false, fmt.Errorf("cache lookup error: %w", err)
	}

	var cacheEntry CacheEntry
	if err := json.Unmarshal([]byte(result), &cacheEntry); err != nil {
		return nil, false, fmt.Errorf("cache data unmarshal error: %w", err)
	}

	return cacheEntry.Suggestions, true, nil
}

func getSuggestionsFromDB(ctx context.Context, prefix string) ([]Suggestion, error) {
	// Try trie_data table first
	query := `
		SELECT suggestions 
		FROM trie_data 
		WHERE prefix = $1 
		ORDER BY version DESC 
		LIMIT 1
	`
	
	var suggestionsJSON []byte
	err := dbConn.QueryRowContext(ctx, query, prefix).Scan(&suggestionsJSON)
	
	if err == nil {
		var suggestions []Suggestion
		if err := json.Unmarshal(suggestionsJSON, &suggestions); err == nil {
			return suggestions, nil
		}
	}

	// Fallback: query frequency table
	fallbackQuery := `
		SELECT query, frequency
		FROM query_frequencies 
		WHERE query LIKE $1
		ORDER BY frequency DESC 
		LIMIT $2
	`

	rows, err := dbConn.QueryContext(ctx, fallbackQuery, prefix+"%", SuggestionsCount)
	if err != nil {
		return nil, fmt.Errorf("database query error: %w", err)
	}
	defer rows.Close()

	var suggestions []Suggestion
	for rows.Next() {
		var suggestion Suggestion
		if err := rows.Scan(&suggestion.Query, &suggestion.Frequency); err != nil {
			log.Printf("Row scan error: %v", err)
			continue
		}
		suggestion.Score = suggestion.Frequency
		suggestions = append(suggestions, suggestion)
	}

	return suggestions, nil
}

func cacheSuggestions(ctx context.Context, prefix string, suggestions []Suggestion) error {
	cacheKey := CacheKeyPrefix + prefix
	
	cacheEntry := CacheEntry{
		Prefix:      prefix,
		Suggestions: suggestions,
		UpdatedAt:   time.Now().UTC().Format(time.RFC3339),
	}

	data, err := json.Marshal(cacheEntry)
	if err != nil {
		return fmt.Errorf("cache data marshal error: %w", err)
	}

	return redisClient.SetEX(ctx, cacheKey, string(data), CacheTTL).Err()
}

func validatePrefix(prefix string) error {
	if prefix == "" {
		return fmt.Errorf("prefix cannot be empty")
	}
	
	if len(prefix) > MaxPrefixLength {
		return fmt.Errorf("prefix too long (max %d characters)", MaxPrefixLength)
	}
	
	// Check for lowercase alphabetic characters and spaces only
	for _, char := range prefix {
		if !((char >= 'a' && char <= 'z') || char == ' ') {
			return fmt.Errorf("only lowercase alphabetic characters and spaces allowed")
		}
	}
	
	return nil
}

// HTTP Handlers

func healthHandler(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	services := make(map[string]string)
	
	// Check Redis
	if _, err := redisClient.Ping(ctx).Result(); err != nil {
		services["redis"] = "error: " + err.Error()
		c.JSON(http.StatusServiceUnavailable, HealthResponse{
			Status:    "unhealthy",
			Timestamp: time.Now().Unix(),
			Services:  services,
		})
		return
	}
	services["redis"] = "connected"

	// Check Database
	if err := dbConn.PingContext(ctx); err != nil {
		services["database"] = "error: " + err.Error()
		c.JSON(http.StatusServiceUnavailable, HealthResponse{
			Status:    "unhealthy",
			Timestamp: time.Now().Unix(),
			Services:  services,
		})
		return
	}
	services["database"] = "connected"

	c.JSON(http.StatusOK, HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now().Unix(),
		Services:  services,
	})
}

func trieHandler(c *gin.Context) {
	startTime := time.Now()
	prefix := strings.TrimSpace(c.Param("prefix"))

	// Validate input
	if err := validatePrefix(prefix); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": err.Error(),
		})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Try cache first
	suggestions, cacheHit, err := getSuggestionsFromCache(ctx, prefix)
	if err != nil {
		log.Printf("Cache error for prefix '%s': %v", prefix, err)
	}

	// Fallback to database
	if !cacheHit {
		suggestions, err = getSuggestionsFromDB(ctx, prefix)
		if err != nil {
			log.Printf("Database error for prefix '%s': %v", prefix, err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "failed to retrieve suggestions",
			})
			return
		}

		// Cache the results asynchronously
		if len(suggestions) > 0 {
			go func() {
				ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
				defer cancel()
				if err := cacheSuggestions(ctx, prefix, suggestions); err != nil {
					log.Printf("Cache write error for prefix '%s': %v", prefix, err)
				}
			}()
		}
	}

	// Limit to max suggestions
	if len(suggestions) > SuggestionsCount {
		suggestions = suggestions[:SuggestionsCount]
	}

	latencyMs := float64(time.Since(startTime).Nanoseconds()) / 1e6

	response := TrieResponse{
		Prefix:      prefix,
		Suggestions: suggestions,
		CacheHit:    cacheHit,
		LatencyMs:   latencyMs,
	}

	// Set cache headers
	c.Header("Cache-Control", "public, max-age=3600")
	c.Header("X-Cache", map[bool]string{true: "HIT", false: "MISS"}[cacheHit])
	c.Header("X-Response-Time", fmt.Sprintf("%.2fms", latencyMs))

	c.JSON(http.StatusOK, response)
}

func reloadHandler(c *gin.Context) {
	// This would typically reload trie from database
	// For now, just clear cache to force database lookup
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pattern := CacheKeyPrefix + "*"
	keys, err := redisClient.Keys(ctx, pattern).Result()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "failed to get cache keys",
		})
		return
	}

	if len(keys) > 0 {
		if err := redisClient.Del(ctx, keys...).Err(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "failed to clear cache",
			})
			return
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"status":       "reloaded",
		"keys_cleared": len(keys),
		"timestamp":    time.Now().Unix(),
	})
}

func metricsHandler(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	// Get cache stats
	cacheInfo, _ := redisClient.Info(ctx, "memory").Result()
	
	// Get database stats
	var totalQueries int
	dbConn.QueryRowContext(ctx, "SELECT COUNT(*) FROM query_frequencies").Scan(&totalQueries)

	// Count cache keys
	keys, _ := redisClient.Keys(ctx, CacheKeyPrefix+"*").Result()
	cacheKeys := len(keys)

	metrics := fmt.Sprintf(`# HELP trie_cache_db_total_queries Total queries in database
# TYPE trie_cache_db_total_queries counter
trie_cache_db_total_queries %d

# HELP trie_cache_keys_total Total trie cache keys
# TYPE trie_cache_keys_total gauge
trie_cache_keys_total %d

# HELP trie_cache_memory_info Cache memory information
# TYPE trie_cache_memory_info gauge
# %s
`, totalQueries, cacheKeys, strings.ReplaceAll(cacheInfo, "\r\n", "\n# "))

	c.Data(http.StatusOK, "text/plain", []byte(metrics))
}

func main() {
	// Initialize connections
	if err := initializeRedis(); err != nil {
		log.Fatalf("Failed to initialize Redis: %v", err)
	}

	if err := initializeDatabase(); err != nil {
		log.Fatalf("Failed to initialize Database: %v", err)
	}

	// Setup Gin router
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()
	router.Use(gin.Logger(), gin.Recovery())

	// CORS configuration
	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowHeaders = []string{"Origin", "Content-Length", "Content-Type", "Authorization"}
	router.Use(cors.New(config))

	// Routes
	router.GET("/health", healthHandler)
	router.GET("/trie/:prefix", trieHandler)
	router.PUT("/trie/reload", reloadHandler)
	router.GET("/metrics", metricsHandler)

	// Start server
	port := getEnv("PORT", "18294")
	log.Printf("🚀 Trie Cache Service starting on port %s", port)
	
	if err := router.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}