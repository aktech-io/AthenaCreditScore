package main

import (
	"os"
	"strconv"

	"github.com/athena/pkg/config"
	"github.com/athena/pkg/database"
	"github.com/athena/pkg/health"
	"github.com/athena/pkg/jwt"
	"github.com/athena/pkg/middleware"
	"github.com/athena/pkg/rabbitmq"
	"github.com/athena/scoring-service/internal/cache"
	"github.com/athena/scoring-service/internal/client"
	"github.com/athena/scoring-service/internal/handler"
	"github.com/athena/scoring-service/internal/routing"
	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	cfg := config.Load()

	// Database
	db, err := database.Connect(cfg)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to database")
	}

	// JWT
	jwtUtil, err := jwt.New(cfg.JWTSecret, cfg.JWTExpMs)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to init JWT")
	}

	// RabbitMQ (non-fatal if unavailable)
	var rabbit *rabbitmq.Client
	rabbit, err = rabbitmq.NewClient(cfg.RabbitMQURL)
	if err != nil {
		log.Warn().Err(err).Msg("rabbitmq unavailable, events will be dropped")
	}

	// Clients
	scoringEngineURL := getEnv("SCORING_ENGINE_URL", "http://athena-python-service:8001")
	pythonClient := client.NewPythonClient(scoringEngineURL)

	transunionURL := getEnv("TRANSUNION_URL", "")
	transunionKey := getEnv("TRANSUNION_API_KEY", "")
	metropolURL := getEnv("METROPOL_URL", "")
	metropolKey := getEnv("METROPOL_API_KEY", "")
	crbClient := client.NewCrbClient(transunionURL, transunionKey, metropolURL, metropolKey)

	// Champion-Challenger Router
	challengerPct := 0.0
	if v := getEnv("CHALLENGER_TRAFFIC_PCT", ""); v != "" {
		if p, err := strconv.ParseFloat(v, 64); err == nil {
			challengerPct = p
		}
	}
	router := routing.NewRouter(challengerPct)

	// Credit Cache
	creditCache := cache.New()

	// Gin engine
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(middleware.Recovery())
	r.Use(middleware.CORS())
	r.Use(middleware.RequestLogger())

	// Health & Prometheus
	health.RegisterRoutes(r)
	r.GET("/actuator/prometheus", gin.WrapH(promhttp.Handler()))

	// Public auth routes (no JWT required)
	authGroup := r.Group("/api/auth")
	authHandler := handler.NewAuthHandler(db, jwtUtil)
	authHandler.RegisterRoutes(authGroup)

	// Protected routes (JWT required)
	protected := r.Group("")
	protected.Use(middleware.JWTAuth(jwtUtil))

	// Credit Query
	creditGroup := protected.Group("/api/v1/credit")
	creditQueryHandler := handler.NewCreditQueryHandler(db, pythonClient, creditCache)
	creditQueryHandler.RegisterRoutes(creditGroup)

	// Dashboard
	dashboardGroup := protected.Group("/api/v1/dashboard")
	dashboardHandler := handler.NewDashboardHandler(db)
	dashboardHandler.RegisterRoutes(dashboardGroup)

	// CRB
	crbGroup := protected.Group("/api/v1/crb")
	crbHandler := handler.NewCrbHandler(crbClient, router)
	crbHandler.RegisterRoutes(crbGroup)

	// Customer Profile
	customerGroup := protected.Group("/api/v1/customers")
	customerHandler := handler.NewCustomerProfileHandler(db, rabbit)
	customerHandler.RegisterRoutes(customerGroup)

	// Disputes
	disputeGroup := protected.Group("/api/v1/disputes")
	disputeHandler := handler.NewDisputeHandler(db)
	disputeHandler.RegisterRoutes(disputeGroup)

	// Models
	modelGroup := protected.Group("/api/v1/models")
	modelHandler := handler.NewModelHandler(db)
	modelHandler.RegisterRoutes(modelGroup)

	// Audit
	auditGroup := protected.Group("/api/v1/audit")
	auditHandler := handler.NewAuditHandler(db)
	auditHandler.RegisterRoutes(auditGroup)

	// Third Party (no JWT — uses API key via Kong)
	thirdPartyGroup := r.Group("/api/v3p")
	thirdPartyHandler := handler.NewThirdPartyHandler(pythonClient, rabbit)
	thirdPartyHandler.RegisterRoutes(thirdPartyGroup)

	port := cfg.Port
	log.Info().Str("port", port).Msg("scoring-service starting")
	if err := r.Run(":" + port); err != nil {
		log.Fatal().Err(err).Msg("server failed")
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
