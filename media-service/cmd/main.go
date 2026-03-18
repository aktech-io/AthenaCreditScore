package main

import (
	"github.com/athena/media-service/internal/config"
	"github.com/athena/media-service/internal/handler"
	"github.com/athena/media-service/internal/repository"
	"github.com/athena/media-service/internal/service"
	pkgcfg "github.com/athena/pkg/config"
	"github.com/athena/pkg/database"
	"github.com/athena/pkg/health"
	"github.com/athena/pkg/jwt"
	"github.com/athena/pkg/middleware"
	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"os"
)

func main() {
	// Structured logging
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = zerolog.New(os.Stdout).With().Timestamp().Caller().Logger()

	// Load shared config
	cfg := pkgcfg.Load()
	// Override default port for media-service
	if os.Getenv("PORT") == "" {
		cfg.Port = "8083"
	}

	// Load media-specific config
	mediaCfg := config.LoadMediaConfig()

	// Connect to database
	db, err := database.Connect(cfg)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to database")
	}

	// JWT util (for optional auth on uploads)
	jwtUtil, err := jwt.New(cfg.JWTSecret, cfg.JWTExpMs)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to initialise JWT")
	}

	// Repository, service, handlers
	repo := repository.NewMediaRepository(db)
	svc := service.NewMediaService(repo, mediaCfg.StorageLocation)
	mediaHandler := handler.NewMediaHandler(svc)
	statsHandler := handler.NewStatsHandler(svc)

	// Gin engine
	r := gin.New()
	r.Use(middleware.Recovery())
	r.Use(middleware.CORS())
	r.Use(middleware.RequestLogger())

	// Health + Prometheus (public)
	health.RegisterRoutes(r)
	r.GET("/actuator/prometheus", gin.WrapH(promhttp.Handler()))

	// Media API routes (JWT auth with optional fallback for upload username)
	api := r.Group("/api/v1/media")
	api.Use(middleware.OptionalJWTAuth(jwtUtil))
	mediaHandler.RegisterRoutes(api)

	// Stats sub-group
	statsGroup := r.Group("/api/v1/media/stats")
	statsGroup.Use(middleware.OptionalJWTAuth(jwtUtil))
	statsHandler.RegisterRoutes(statsGroup)

	log.Info().Str("port", cfg.Port).Msg("media-service starting")
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal().Err(err).Msg("server failed")
	}
}
