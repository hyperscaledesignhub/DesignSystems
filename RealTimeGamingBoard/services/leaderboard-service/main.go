package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	_ "github.com/lib/pq"
)

type LeaderboardService struct {
	redisClient *redis.Client
	db          *sql.DB
	userServiceURL string
}

type LeaderboardEntry struct {
	Rank        int    `json:"rank"`
	UserID      string `json:"user_id"`
	DisplayName string `json:"display_name"`
	Score       int64  `json:"score"`
}

type LeaderboardResponse struct {
	Leaderboard []LeaderboardEntry `json:"leaderboard"`
	Month       string             `json:"month"`
}

type UserRankResponse struct {
	UserID      string `json:"user_id"`
	DisplayName string `json:"display_name"`
	Rank        int64  `json:"rank"`
	Score       int64  `json:"score"`
	Month       string `json:"month"`
}

type ScoreUpdateRequest struct {
	UserID string `json:"user_id"`
	Points int    `json:"points"`
}

type UserProfile struct {
	UserID      string `json:"user_id"`
	Username    string `json:"username"`
	DisplayName string `json:"display_name"`
	CreatedAt   string `json:"created_at"`
}

func NewLeaderboardService() *LeaderboardService {
	redisURL := getEnv("REDIS_URL", "redis://localhost:6379")
	databaseURL := getEnv("DATABASE_URL", "postgresql://user:password@localhost/gaming?sslmode=disable")
	userServiceURL := getEnv("USER_SERVICE_URL", "http://localhost:23451")

	// Redis client
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatal("Failed to parse Redis URL:", err)
	}
	redisClient := redis.NewClient(opt)

	// Database connection
	db, err := sql.Open("postgres", databaseURL)
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}

	// Initialize database schema
	initDB(db)

	return &LeaderboardService{
		redisClient:    redisClient,
		db:             db,
		userServiceURL: userServiceURL,
	}
}

func initDB(db *sql.DB) {
	query := `
	CREATE TABLE IF NOT EXISTS leaderboard_history (
		id SERIAL PRIMARY KEY,
		user_id UUID NOT NULL,
		score INT NOT NULL,
		month VARCHAR(7) NOT NULL,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		UNIQUE(user_id, month)
	);

	CREATE INDEX IF NOT EXISTS idx_leaderboard_month ON leaderboard_history(month, score DESC);
	`
	
	_, err := db.Exec(query)
	if err != nil {
		log.Fatal("Failed to initialize database:", err)
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getCurrentMonth() string {
	return time.Now().Format("2006-01")
}

func (ls *LeaderboardService) getLeaderboardKey(month string) string {
	return fmt.Sprintf("leaderboard:%s", month)
}

func (ls *LeaderboardService) fetchUserProfile(userID string) (*UserProfile, error) {
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get(fmt.Sprintf("%s/api/v1/users/%s", ls.userServiceURL, userID))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("user not found")
	}

	var profile UserProfile
	if err := json.NewDecoder(resp.Body).Decode(&profile); err != nil {
		return nil, err
	}

	return &profile, nil
}

func (ls *LeaderboardService) getTopLeaderboard(c *gin.Context) {
	month := getCurrentMonth()
	key := ls.getLeaderboardKey(month)
	
	// Get top 10 from Redis sorted set
	result, err := ls.redisClient.ZRevRangeWithScores(context.Background(), key, 0, 9).Result()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch leaderboard"})
		return
	}

	leaderboard := make([]LeaderboardEntry, 0, len(result))
	
	for i, member := range result {
		userID := member.Member.(string)
		score := int64(member.Score)
		
		// Fetch user profile
		profile, err := ls.fetchUserProfile(userID)
		displayName := userID // fallback
		if err == nil && profile != nil {
			displayName = profile.DisplayName
		}

		leaderboard = append(leaderboard, LeaderboardEntry{
			Rank:        i + 1,
			UserID:      userID,
			DisplayName: displayName,
			Score:       score,
		})
	}

	c.JSON(http.StatusOK, LeaderboardResponse{
		Leaderboard: leaderboard,
		Month:       month,
	})
}

func (ls *LeaderboardService) getUserRank(c *gin.Context) {
	userID := c.Param("user_id")
	month := getCurrentMonth()
	key := ls.getLeaderboardKey(month)

	// Get user rank (0-based, so add 1)
	rank, err := ls.redisClient.ZRevRank(context.Background(), key, userID).Result()
	if err != nil {
		if err == redis.Nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "User not found in leaderboard"})
		} else {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch user rank"})
		}
		return
	}

	// Get user score
	score, err := ls.redisClient.ZScore(context.Background(), key, userID).Result()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch user score"})
		return
	}

	// Fetch user profile
	profile, err := ls.fetchUserProfile(userID)
	displayName := userID // fallback
	if err == nil && profile != nil {
		displayName = profile.DisplayName
	}

	c.JSON(http.StatusOK, UserRankResponse{
		UserID:      userID,
		DisplayName: displayName,
		Rank:        rank + 1, // Convert to 1-based
		Score:       int64(score),
		Month:       month,
	})
}

func (ls *LeaderboardService) getRelativeLeaderboard(c *gin.Context) {
	userID := c.Param("user_id")
	month := getCurrentMonth()
	key := ls.getLeaderboardKey(month)

	// Get user rank
	rank, err := ls.redisClient.ZRevRank(context.Background(), key, userID).Result()
	if err != nil {
		if err == redis.Nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "User not found in leaderboard"})
		} else {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch user rank"})
		}
		return
	}

	// Get 4 above and 4 below (total 9 including user)
	start := rank - 4
	end := rank + 4

	if start < 0 {
		start = 0
	}

	result, err := ls.redisClient.ZRevRangeWithScores(context.Background(), key, start, end).Result()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch relative leaderboard"})
		return
	}

	leaderboard := make([]LeaderboardEntry, 0, len(result))
	
	for i, member := range result {
		memberUserID := member.Member.(string)
		score := int64(member.Score)
		
		// Fetch user profile
		profile, err := ls.fetchUserProfile(memberUserID)
		displayName := memberUserID // fallback
		if err == nil && profile != nil {
			displayName = profile.DisplayName
		}

		leaderboard = append(leaderboard, LeaderboardEntry{
			Rank:        int(start) + i + 1,
			UserID:      memberUserID,
			DisplayName: displayName,
			Score:       score,
		})
	}

	c.JSON(http.StatusOK, LeaderboardResponse{
		Leaderboard: leaderboard,
		Month:       month,
	})
}

func (ls *LeaderboardService) updateScore(c *gin.Context) {
	var req ScoreUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	month := getCurrentMonth()
	key := ls.getLeaderboardKey(month)

	// Update Redis sorted set
	_, err := ls.redisClient.ZIncrBy(context.Background(), key, float64(req.Points), req.UserID).Result()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update score"})
		return
	}

	// Get new score for backup
	newScore, err := ls.redisClient.ZScore(context.Background(), key, req.UserID).Result()
	if err != nil {
		log.Printf("Failed to get new score for backup: %v", err)
	} else {
		// Backup to PostgreSQL
		_, err = ls.db.Exec(`
			INSERT INTO leaderboard_history (user_id, score, month)
			VALUES ($1, $2, $3)
			ON CONFLICT (user_id, month)
			DO UPDATE SET score = $2, updated_at = CURRENT_TIMESTAMP
		`, req.UserID, int64(newScore), month)
		if err != nil {
			log.Printf("Failed to backup score to database: %v", err)
		}
	}

	c.JSON(http.StatusOK, gin.H{"message": "Score updated successfully"})
}

func (ls *LeaderboardService) healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"service": "leaderboard-service",
	})
}

func main() {
	service := NewLeaderboardService()
	defer service.redisClient.Close()
	defer service.db.Close()

	router := gin.Default()

	// Routes
	router.GET("/api/v1/leaderboard/top", service.getTopLeaderboard)
	router.GET("/api/v1/leaderboard/rank/:user_id", service.getUserRank)
	router.GET("/api/v1/leaderboard/around/:user_id", service.getRelativeLeaderboard)
	router.POST("/api/v1/leaderboard/score", service.updateScore)
	router.GET("/health", service.healthCheck)

	port := getEnv("SERVICE_PORT", "23453")
	log.Printf("Leaderboard service starting on port %s", port)
	
	if err := router.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}