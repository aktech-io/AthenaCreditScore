package seed

import (
	"github.com/athena/notification-service/internal/model"
	"github.com/athena/notification-service/internal/repository"
	"github.com/rs/zerolog/log"
)

// Run seeds default EMAIL and SMS notification configs if they don't exist.
func Run(configRepo *repository.ConfigRepository) {
	// Seed EMAIL config
	existing, err := configRepo.FindByType("EMAIL")
	if err != nil {
		log.Error().Err(err).Msg("failed to check for existing EMAIL config")
	}
	if existing == nil {
		log.Info().Msg("Seeding default EMAIL notification config (disabled — configure via API)")
		emailCfg := &model.NotificationConfig{
			Type:        "EMAIL",
			Provider:    "SMTP",
			Host:        "smtp.gmail.com",
			Port:        587,
			Username:    "",
			Password:    "",
			FromAddress: "noreply@athena.co.ke",
			Enabled:     false,
		}
		if err := configRepo.Create(emailCfg); err != nil {
			log.Error().Err(err).Msg("failed to seed EMAIL config")
		}
	}

	// Seed SMS config
	existing, err = configRepo.FindByType("SMS")
	if err != nil {
		log.Error().Err(err).Msg("failed to check for existing SMS config")
	}
	if existing == nil {
		log.Info().Msg("Seeding default SMS notification config (disabled — configure via API)")
		smsCfg := &model.NotificationConfig{
			Type:     "SMS",
			Provider: "AFRICAS_TALKING",
			SenderID: "ATHENA",
			ApiKey:   "",
			ApiSecret: "",
			Enabled:  false,
		}
		if err := configRepo.Create(smsCfg); err != nil {
			log.Error().Err(err).Msg("failed to seed SMS config")
		}
	}
}
