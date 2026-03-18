package main

import (
	"os"

	pkgcfg "github.com/athena/pkg/config"
	"github.com/athena/pkg/database"
	"github.com/athena/pkg/health"
	"github.com/athena/pkg/jwt"
	"github.com/athena/pkg/middleware"
	"github.com/athena/pkg/rabbitmq"
	"github.com/athena/user-service/internal/handler"
	"github.com/athena/user-service/internal/repository"
	"github.com/athena/user-service/internal/seed"
	"github.com/athena/user-service/internal/service"
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
	cfg := pkgcfg.Load()
	// Override default port for user-service
	if os.Getenv("PORT") == "" {
		cfg.Port = "8081"
	}

	// Connect to database
	db, err := database.Connect(cfg)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to database")
	}

	// JWT util
	jwtUtil, err := jwt.New(cfg.JWTSecret, cfg.JWTExpMs)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to initialise JWT")
	}

	// RabbitMQ client (optional — log warning if unavailable)
	var rabbitClient *rabbitmq.Client
	rabbitClient, err = rabbitmq.NewClient(cfg.RabbitMQURL)
	if err != nil {
		log.Warn().Err(err).Msg("RabbitMQ unavailable — invitation events will not be published")
	}

	// Repositories
	adminUserRepo := repository.NewAdminUserRepository(db)
	userRepo := repository.NewUserRepository(db)
	roleRepo := repository.NewRoleRepository(db)
	groupRepo := repository.NewGroupRepository(db)
	invitationRepo := repository.NewInvitationRepository(db)
	policyRepo := repository.NewPasswordPolicyRepository(db)

	// Services
	policyService := service.NewPasswordPolicyService(policyRepo)
	authService := service.NewAuthService(userRepo, roleRepo, jwtUtil, policyService)

	// Seed data
	seed.Initialize(roleRepo, groupRepo, policyRepo)

	// Handlers
	authHandler := handler.NewAuthHandler(adminUserRepo, jwtUtil, authService, db)
	userMgmtHandler := handler.NewUserManagementHandler(userRepo, groupRepo, roleRepo, invitationRepo, rabbitClient)
	groupHandler := handler.NewGroupHandler(groupRepo, roleRepo)
	roleHandler := handler.NewRoleHandler(roleRepo)
	policyHandler := handler.NewPasswordPolicyHandler(policyService)
	invitationHandler := handler.NewInvitationHandler(invitationRepo, userRepo)

	// Gin engine
	r := gin.New()
	r.Use(middleware.Recovery())
	r.Use(middleware.CORS())
	r.Use(middleware.RequestLogger())

	// Health + Prometheus (public)
	health.RegisterRoutes(r)
	r.GET("/actuator/prometheus", gin.WrapH(promhttp.Handler()))

	// Auth routes (public)
	authGroup := r.Group("/api/auth")
	authHandler.RegisterRoutes(authGroup)
	invitationHandler.RegisterRoutes(authGroup)

	// Protected admin routes
	adminGroup := r.Group("/api/v1/admin")
	adminGroup.Use(middleware.JWTAuth(jwtUtil))

	userMgmtHandler.RegisterRoutes(adminGroup.Group("/users"))
	groupHandler.RegisterRoutes(adminGroup.Group("/groups"))
	roleHandler.RegisterRoutes(adminGroup.Group("/roles"))
	policyHandler.RegisterRoutes(adminGroup.Group("/password-policy"))

	log.Info().Str("port", cfg.Port).Msg("user-service starting")
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal().Err(err).Msg("server failed")
	}
}
