// Minimal Go HTTP server with Gin — health endpoint, structured logging, graceful shutdown.
// Designed for k8s: graceful shutdown, health/ready endpoints, env config.
package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
)

// Structured logging
type logEntry struct {
	Timestamp string                 `json:"timestamp"`
	Level     string                 `json:"level"`
	Msg       string                 `json:"msg"`
	Extra     map[string]interface{} `json:"extra,omitempty"`
}

func logInfo(msg string, extra map[string]interface{}) {
	entry := logEntry{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Level:     "info",
		Msg:       msg,
		Extra:     extra,
	}
	b, _ := json.Marshal(entry)
	log.Println(string(b))
}

func logError(msg string, extra map[string]interface{}) {
	entry := logEntry{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Level:     "error",
		Msg:       msg,
		Extra:     extra,
	}
	b, _ := json.Marshal(entry)
	log.Println(string(b))
}

// Config from environment
type Config struct {
	AppName  string
	Version  string
	Port     string
	AppEnv   string
}

func loadConfig() Config {
	return Config{
		AppName: getEnv("APP_NAME", "go-http"),
		Version: getEnv("VERSION", "1.0.0"),
		Port:    getEnv("PORT", "8080"),
		AppEnv:  getEnv("APP_ENV", "lab"),
	}
}

func getEnv(key, defaultValue string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultValue
}

// Health response
type HealthResponse struct {
	Status   string `json:"status"`
	App      string `json:"app"`
	Version  string `json:"version"`
	Hostname string `json:"hostname"`
}

func main() {
	cfg := loadConfig()

	// Gin mode
	if cfg.AppEnv == "prod" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.New()
	r.Use(gin.Recovery())

	// Structured logging middleware
	r.Use(func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		method := c.Request.Method

		c.Next()

		duration := time.Since(start)
		logInfo("http_request", map[string]interface{}{
			"method":   method,
			"path":     path,
			"status":   c.Writer.Status(),
			"duration": duration.String(),
			"client":   c.ClientIP(),
		})
	})

	// Health endpoint
	r.GET("/healthz", func(c *gin.Context) {
		hostname, _ := os.Hostname()
		c.JSON(http.StatusOK, HealthResponse{
			Status:   "ok",
			App:      cfg.AppName,
			Version:  cfg.Version,
			Hostname: hostname,
		})
	})

	// Readiness
	r.GET("/ready", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ready", "app": cfg.AppName})
	})

	// Example API
	r.GET("/api/hello", func(c *gin.Context) {
		hostname, _ := os.Hostname()
		c.JSON(http.StatusOK, gin.H{
			"message":  "Hello from " + cfg.AppName,
			"version":  cfg.Version,
			"env":      cfg.AppEnv,
			"hostname": hostname,
		})
	})

	// HTTP server
	srv := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: r,
	}

	// Graceful shutdown
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logError("server error", map[string]interface{}{"error": err.Error()})
		}
	}()

	logInfo("server starting", map[string]interface{}{
		"app":     cfg.AppName,
		"version": cfg.Version,
		"port":    cfg.Port,
		"env":     cfg.AppEnv,
	})

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logInfo("shutdown signal received", nil)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		logError("server forced to shutdown", map[string]interface{}{"error": err.Error()})
	}

	logInfo("server exited", nil)
}