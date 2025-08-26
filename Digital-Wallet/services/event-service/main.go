package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/segmentio/kafka-go"
)

type Event struct {
	ID            string                 `json:"id"`
	EventType     string                 `json:"event_type"`
	WalletID      string                 `json:"wallet_id"`
	Amount        string                 `json:"amount"`
	Currency      string                 `json:"currency"`
	TransactionID string                 `json:"transaction_id"`
	Timestamp     time.Time              `json:"timestamp"`
	Metadata      map[string]interface{} `json:"metadata"`
}

type EventService struct {
	kafkaWriter *kafka.Writer
	kafkaReader *kafka.Reader
}

func NewEventService() *EventService {
	kafkaBroker := getEnv("KAFKA_BROKER", "localhost:9092")
	kafkaTopic := getEnv("KAFKA_TOPIC", "wallet-events")

	writer := &kafka.Writer{
		Addr:     kafka.TCP(kafkaBroker),
		Topic:    kafkaTopic,
		Balancer: &kafka.LeastBytes{},
	}

	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: []string{kafkaBroker},
		Topic:   kafkaTopic,
		GroupID: "event-service-group",
	})

	return &EventService{
		kafkaWriter: writer,
		kafkaReader: reader,
	}
}

func (es *EventService) Close() {
	if es.kafkaWriter != nil {
		es.kafkaWriter.Close()
	}
	if es.kafkaReader != nil {
		es.kafkaReader.Close()
	}
}

func (es *EventService) AppendEvent(c *gin.Context) {
	var event Event
	if err := c.ShouldBindJSON(&event); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Set event ID and timestamp if not provided
	if event.ID == "" {
		event.ID = uuid.New().String()
	}
	if event.Timestamp.IsZero() {
		event.Timestamp = time.Now().UTC()
	}

	// Serialize event to JSON
	eventBytes, err := json.Marshal(event)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to serialize event"})
		return
	}

	// Write to Kafka
	msg := kafka.Message{
		Key:   []byte(event.WalletID),
		Value: eventBytes,
		Time:  event.Timestamp,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := es.kafkaWriter.WriteMessages(ctx, msg); err != nil {
		log.Printf("Failed to write event to Kafka: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to append event"})
		return
	}

	log.Printf("Event appended: %s - %s", event.ID, event.EventType)
	c.JSON(http.StatusOK, gin.H{
		"message":  "Event appended successfully",
		"event_id": event.ID,
	})
}

func (es *EventService) GetEventStream(c *gin.Context) {
	startOffsetStr := c.Param("start_offset")
	startOffset, err := strconv.ParseInt(startOffsetStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid start_offset"})
		return
	}

	limitStr := c.DefaultQuery("limit", "100")
	limit, err := strconv.Atoi(limitStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid limit"})
		return
	}

	// Create a new reader for this request with specific offset
	kafkaBroker := getEnv("KAFKA_BROKER", "localhost:9092")
	kafkaTopic := getEnv("KAFKA_TOPIC", "wallet-events")

	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: []string{kafkaBroker},
		Topic:   kafkaTopic,
		GroupID: fmt.Sprintf("stream-reader-%s", uuid.New().String()),
	})
	defer reader.Close()

	// Set offset
	reader.SetOffset(startOffset)

	var events []Event
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	for i := 0; i < limit; i++ {
		msg, err := reader.FetchMessage(ctx)
		if err != nil {
			break
		}

		var event Event
		if err := json.Unmarshal(msg.Value, &event); err != nil {
			log.Printf("Failed to unmarshal event: %v", err)
			continue
		}

		events = append(events, event)

		// Commit the message
		if err := reader.CommitMessages(ctx, msg); err != nil {
			log.Printf("Failed to commit message: %v", err)
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"start_offset": startOffset,
		"count":        len(events),
		"events":       events,
	})
}

func (es *EventService) GetWalletEvents(c *gin.Context) {
	walletID := c.Param("wallet_id")
	limitStr := c.DefaultQuery("limit", "50")
	limit, err := strconv.Atoi(limitStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid limit"})
		return
	}

	// Create a new reader for this wallet
	kafkaBroker := getEnv("KAFKA_BROKER", "localhost:9092")
	kafkaTopic := getEnv("KAFKA_TOPIC", "wallet-events")

	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: []string{kafkaBroker},
		Topic:   kafkaTopic,
		GroupID: fmt.Sprintf("wallet-reader-%s", uuid.New().String()),
	})
	defer reader.Close()

	var events []Event
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Read messages and filter by wallet ID
	count := 0
	for count < limit {
		msg, err := reader.FetchMessage(ctx)
		if err != nil {
			break
		}

		var event Event
		if err := json.Unmarshal(msg.Value, &event); err != nil {
			log.Printf("Failed to unmarshal event: %v", err)
			continue
		}

		// Filter by wallet ID
		if event.WalletID == walletID {
			events = append(events, event)
			count++
		}

		// Commit the message
		if err := reader.CommitMessages(ctx, msg); err != nil {
			log.Printf("Failed to commit message: %v", err)
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"wallet_id": walletID,
		"count":     len(events),
		"events":    events,
	})
}

func (es *EventService) ReplayEvents(c *gin.Context) {
	var replayRequest struct {
		FromTimestamp string `json:"from_timestamp"`
		ToTimestamp   string `json:"to_timestamp"`
		WalletID      string `json:"wallet_id,omitempty"`
	}

	if err := c.ShouldBindJSON(&replayRequest); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	fromTime, err := time.Parse(time.RFC3339, replayRequest.FromTimestamp)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid from_timestamp format"})
		return
	}

	toTime, err := time.Parse(time.RFC3339, replayRequest.ToTimestamp)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid to_timestamp format"})
		return
	}

	// Create a new reader for replay
	kafkaBroker := getEnv("KAFKA_BROKER", "localhost:9092")
	kafkaTopic := getEnv("KAFKA_TOPIC", "wallet-events")

	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: []string{kafkaBroker},
		Topic:   kafkaTopic,
		GroupID: fmt.Sprintf("replay-reader-%s", uuid.New().String()),
	})
	defer reader.Close()

	var events []Event
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	// Set offset to beginning
	reader.SetOffset(0)

	for {
		msg, err := reader.FetchMessage(ctx)
		if err != nil {
			break
		}

		var event Event
		if err := json.Unmarshal(msg.Value, &event); err != nil {
			log.Printf("Failed to unmarshal event: %v", err)
			continue
		}

		// Filter by time range
		if event.Timestamp.After(fromTime) && event.Timestamp.Before(toTime) {
			// Filter by wallet ID if specified
			if replayRequest.WalletID == "" || event.WalletID == replayRequest.WalletID {
				events = append(events, event)
			}
		}

		// Commit the message
		if err := reader.CommitMessages(ctx, msg); err != nil {
			log.Printf("Failed to commit message: %v", err)
		}
	}

	log.Printf("Replayed %d events from %s to %s", len(events), replayRequest.FromTimestamp, replayRequest.ToTimestamp)

	c.JSON(http.StatusOK, gin.H{
		"message":        "Events replayed successfully",
		"from_timestamp": replayRequest.FromTimestamp,
		"to_timestamp":   replayRequest.ToTimestamp,
		"wallet_id":      replayRequest.WalletID,
		"count":          len(events),
		"events":         events,
	})
}

func (es *EventService) HealthCheck(c *gin.Context) {
	// Test Kafka connectivity
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	testEvent := Event{
		ID:        uuid.New().String(),
		EventType: "health_check",
		WalletID:  "test",
		Amount:    "0",
		Currency:  "USD",
		Timestamp: time.Now().UTC(),
	}

	eventBytes, _ := json.Marshal(testEvent)
	msg := kafka.Message{
		Key:   []byte("health"),
		Value: eventBytes,
	}

	if err := es.kafkaWriter.WriteMessages(ctx, msg); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status":  "unhealthy",
			"service": "event-service",
			"kafka":   "disconnected",
			"error":   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"service": "event-service",
		"kafka":   "connected",
	})
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
	// Initialize event service
	eventService := NewEventService()
	defer eventService.Close()

	// Setup Gin router
	r := gin.Default()

	// Routes
	v1 := r.Group("/v1/events")
	{
		v1.POST("/append", eventService.AppendEvent)
		v1.GET("/stream/:start_offset", eventService.GetEventStream)
		v1.GET("/wallet/:wallet_id", eventService.GetWalletEvents)
		v1.POST("/replay", eventService.ReplayEvents)
	}

	r.GET("/health", eventService.HealthCheck)

	// Start server
	port := getEnv("PORT", "9085")
	log.Printf("Event Service starting on port %s", port)
	log.Fatal(r.Run(":" + port))
}