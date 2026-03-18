package main

import (
	"net/http"

	"github.com/athena/customer-service/internal/client"
	"github.com/athena/customer-service/internal/handler"
	"github.com/athena/pkg/config"
	"github.com/athena/pkg/database"
	"github.com/athena/pkg/health"
	"github.com/athena/pkg/jwt"
	"github.com/athena/pkg/middleware"
	"github.com/athena/pkg/rabbitmq"
	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Info().Msg("customer-service starting")

	cfg := config.Load()

	// Override default port to 8082 for customer-service
	if cfg.Port == "8080" {
		cfg.Port = "8082"
	}

	// Database
	db, err := database.Connect(cfg)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to database")
	}

	// JWT
	jwtUtil, err := jwt.New(cfg.JWTSecret, cfg.JWTExpMs)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to initialize JWT")
	}

	// RabbitMQ (optional — service works without it)
	var rabbit *rabbitmq.Client
	rabbit, err = rabbitmq.NewClient(cfg.RabbitMQURL)
	if err != nil {
		log.Warn().Err(err).Msg("rabbitmq: connection failed, events will be skipped")
	}

	// Media client
	mediaClient := client.NewMediaClient()

	// Gin router
	r := gin.New()
	r.Use(middleware.Recovery())
	r.Use(middleware.CORS())
	r.Use(middleware.RequestLogger())

	// Health & metrics (public)
	health.RegisterRoutes(r)
	r.GET("/actuator/prometheus", gin.WrapH(promhttp.Handler()))

	// Protected routes
	api := r.Group("/api/v1")
	api.Use(middleware.JWTAuth(jwtUtil))

	// Register handlers
	customerHandler := handler.NewCustomerHandler(db, rabbit, mediaClient)
	customerHandler.RegisterRoutes(api)

	disputeHandler := handler.NewAdminDisputeHandler(db)
	disputeHandler.RegisterRoutes(api)

	// Start server
	addr := ":" + cfg.Port
	log.Info().Str("addr", addr).Msg("customer-service listening")
	if err := http.ListenAndServe(addr, r); err != nil {
		log.Fatal().Err(err).Msg("server failed")
	}
}
