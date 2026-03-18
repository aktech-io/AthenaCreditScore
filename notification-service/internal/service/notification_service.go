package service

import (
	"crypto/tls"
	"fmt"
	"time"

	"github.com/athena/notification-service/internal/model"
	"github.com/athena/notification-service/internal/repository"
	"github.com/rs/zerolog/log"
	"gopkg.in/gomail.v2"
)

type NotificationService struct {
	configRepo *repository.ConfigRepository
	logRepo    *repository.LogRepository
}

func NewNotificationService(configRepo *repository.ConfigRepository, logRepo *repository.LogRepository) *NotificationService {
	return &NotificationService{
		configRepo: configRepo,
		logRepo:    logRepo,
	}
}

// --------------------------------------------------------------------------
// Core email dispatcher — used by all event-driven and REST-triggered sends
// --------------------------------------------------------------------------

func (s *NotificationService) SendEmail(serviceName, to, subject, body string) error {
	log.Info().Str("service", serviceName).Str("to", to).Str("subject", subject).Msg("Sending email")

	status := "FAILED"
	var errorMsg string

	defer func() {
		entry := &model.NotificationLog{
			ServiceName:  serviceName,
			Type:         "EMAIL",
			Recipient:    to,
			Subject:      subject,
			Body:         body,
			Status:       status,
			ErrorMessage: errorMsg,
			SentAt:       time.Now(),
		}
		if err := s.logRepo.Save(entry); err != nil {
			log.Error().Err(err).Msg("failed to save notification log")
		}
	}()

	cfg, err := s.configRepo.FindByType("EMAIL")
	if err != nil {
		errorMsg = err.Error()
		return fmt.Errorf("email configuration error: %w", err)
	}
	if cfg == nil {
		errorMsg = "Email configuration not found"
		return fmt.Errorf("email configuration not found")
	}

	if !cfg.Enabled {
		log.Warn().Str("to", to).Msg("Email notifications are DISABLED. Skipping send")
		status = "SKIPPED"
		return nil
	}

	m := gomail.NewMessage()
	m.SetHeader("From", cfg.FromAddress)
	m.SetHeader("To", to)
	m.SetHeader("Subject", subject)
	m.SetBody("text/plain", body)

	d := gomail.NewDialer(cfg.Host, cfg.Port, cfg.Username, cfg.Password)

	if cfg.Port == 465 {
		d.SSL = true
	}
	// Trust all certs (matches Java mail.smtp.ssl.trust = "*")
	d.TLSConfig = &tls.Config{InsecureSkipVerify: true}

	if sendErr := d.DialAndSend(m); sendErr != nil {
		errorMsg = sendErr.Error()
		log.Error().Err(sendErr).Str("to", to).Msg("Failed to send email")
		return fmt.Errorf("failed to send email: %w", sendErr)
	}

	log.Info().Str("to", to).Msg("Email sent successfully")
	status = "SENT"
	return nil
}

// --------------------------------------------------------------------------
// Athena Credit Score — event-driven email templates
// --------------------------------------------------------------------------

func (s *NotificationService) SendDisputeAcknowledgement(to, disputeID string, customerID int64) {
	subject := "Dispute Received — Athena Credit Score"
	body := fmt.Sprintf(
		"Dear Valued Customer,\n\n"+
			"We have received your credit report dispute (Ref: %s).\n\n"+
			"Our team will review your dispute and respond within 5 working days in accordance "+
			"with the Credit Reference Bureau Regulations, 2013.\n\n"+
			"You can track the status of your dispute by logging into the Athena Customer Portal.\n\n"+
			"Regards,\n"+
			"Athena Credit Score Team\n"+
			"support@athena.co.ke",
		disputeID)
	if err := s.SendEmail("customer-service", to, subject, body); err != nil {
		log.Error().Err(err).Str("to", to).Msg("failed to send dispute acknowledgement")
	}
}

func (s *NotificationService) SendScoreUpdateNotification(to string, score interface{}, customerID int64) {
	subject := "Your Credit Score Has Been Updated — Athena"
	body := fmt.Sprintf(
		"Dear Valued Customer,\n\n"+
			"Your Athena Credit Score has been updated.\n\n"+
			"New Score: %v / 850\n\n"+
			"Log in to the Athena Customer Portal to view your full credit report "+
			"and understand what factors influenced your score.\n\n"+
			"Regards,\n"+
			"Athena Credit Score Team\n"+
			"support@athena.co.ke",
		score)
	if err := s.SendEmail("scoring-service", to, subject, body); err != nil {
		log.Error().Err(err).Str("to", to).Msg("failed to send score update notification")
	}
}

func (s *NotificationService) SendConsentGrantedNotification(to string, partnerID interface{}, customerID int64) {
	subject := "Data Access Consent Confirmed — Athena"
	body := fmt.Sprintf(
		"Dear Valued Customer,\n\n"+
			"You have successfully granted data access consent to partner: %v.\n\n"+
			"If you did not authorise this, please contact us immediately at support@athena.co.ke "+
			"or call +254 700 000 000.\n\n"+
			"You can revoke consent at any time from the Athena Customer Portal.\n\n"+
			"Regards,\n"+
			"Athena Credit Score Team",
		partnerID)
	if err := s.SendEmail("customer-service", to, subject, body); err != nil {
		log.Error().Err(err).Str("to", to).Msg("failed to send consent granted notification")
	}
}

// --------------------------------------------------------------------------
// Config management
// --------------------------------------------------------------------------

func (s *NotificationService) GetConfig(configType string) (*model.NotificationConfig, error) {
	return s.configRepo.FindByType(configType)
}

func (s *NotificationService) UpdateConfig(cfg *model.NotificationConfig) (*model.NotificationConfig, error) {
	existing, err := s.configRepo.FindByType(cfg.Type)
	if err != nil {
		return nil, err
	}

	if existing != nil {
		existing.Provider = cfg.Provider
		existing.Host = cfg.Host
		existing.Port = cfg.Port
		existing.Username = cfg.Username
		existing.Password = cfg.Password
		existing.FromAddress = cfg.FromAddress
		existing.ApiKey = cfg.ApiKey
		existing.ApiSecret = cfg.ApiSecret
		existing.SenderID = cfg.SenderID
		existing.Enabled = cfg.Enabled
		existing.Type = cfg.Type
		if err := s.configRepo.Save(existing); err != nil {
			return nil, err
		}
		return existing, nil
	}

	if err := s.configRepo.Save(cfg); err != nil {
		return nil, err
	}
	return cfg, nil
}
