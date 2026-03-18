package main

import (
	"os"

	"github.com/athena/notification-service/internal/handler"
	"github.com/athena/notification-service/internal/listener"
	"github.com/athena/notification-service/internal/repository"
	"github.com/athena/notification-service/internal/seed"
	"github.com/athena/notification-service/internal/service"
	"github.com/athena/pkg/config"
	"github.com/athena/pkg/database"
	"github.com/athena/pkg/health"
	"github.com/athena/pkg/middleware"
	"github.com/athena/pkg/rabbitmq"
	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	// Structured logging
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = zerolog.New(os.Stdout).With().Timestamp().Caller().Logger()

	// Load shared config
	cfg := config.Load()
	if os.Getenv("PORT") == "" {
		cfg.Port = "8085"
	}

	// Connect to database
	db, err := database.Connect(cfg)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to database")
	}

	// Repositories
	configRepo := repository.NewConfigRepository(db)
	logRepo := repository.NewLogRepository(db)

	// Seed default configs
	seed.Run(configRepo)

	// Notification service
	notifSvc := service.NewNotificationService(configRepo, logRepo)

	// RabbitMQ client + event listener
	rmqClient, err := rabbitmq.NewClient(cfg.RabbitMQURL)
	if err != nil {
		log.Warn().Err(err).Msg("failed to connect to RabbitMQ — event consumption disabled")
	} else {
		eventListener := listener.NewEventListener(notifSvc, rmqClient)
		if err := eventListener.Start(); err != nil {
			log.Error().Err(err).Msg("failed to start event listener")
		}
		defer rmqClient.Close()
	}

	// Handler
	notifHandler := handler.NewNotificationHandler(notifSvc)

	// Gin engine
	r := gin.New()
	r.Use(middleware.Recovery())
	r.Use(middleware.CORS())
	r.Use(middleware.RequestLogger())

	// Health + Prometheus (public)
	health.RegisterRoutes(r)
	r.GET("/actuator/prometheus", gin.WrapH(promhttp.Handler()))

	// Notification API routes
	api := r.Group("/api/v1/notifications")
	notifHandler.RegisterRoutes(api)

	log.Info().Str("port", cfg.Port).Msg("notification-service starting")
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal().Err(err).Msg("server failed")
	}
}
