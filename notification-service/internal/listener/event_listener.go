package listener

import (
	"encoding/json"
	"fmt"

	"github.com/athena/notification-service/internal/service"
	"github.com/athena/pkg/rabbitmq"
	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/rs/zerolog/log"
)

type EventListener struct {
	svc    *service.NotificationService
	client *rabbitmq.Client
}

func NewEventListener(svc *service.NotificationService, client *rabbitmq.Client) *EventListener {
	return &EventListener{
		svc:    svc,
		client: client,
	}
}

// Start launches goroutines to consume from notification and dispute queues.
func (l *EventListener) Start() error {
	notifMsgs, err := l.client.Consume(rabbitmq.NotificationQueue)
	if err != nil {
		return fmt.Errorf("failed to consume notification queue: %w", err)
	}

	disputeMsgs, err := l.client.Consume(rabbitmq.DisputeQueue)
	if err != nil {
		return fmt.Errorf("failed to consume dispute queue: %w", err)
	}

	go l.consumeNotifications(notifMsgs)
	go l.consumeDisputes(disputeMsgs)

	log.Info().Msg("event listener started: consuming athena.notification.queue + athena.dispute.queue")
	return nil
}

func (l *EventListener) consumeNotifications(msgs <-chan amqp.Delivery) {
	for msg := range msgs {
		var event map[string]interface{}
		if err := json.Unmarshal(msg.Body, &event); err != nil {
			log.Error().Err(err).Msg("[NOTIFICATION] failed to unmarshal event")
			_ = msg.Nack(false, false)
			continue
		}

		eventType, _ := event["type"].(string)
		if eventType == "" {
			eventType = "UNKNOWN"
		}
		customerID := extractInt64(event, "customerId")
		email, _ := event["email"].(string)

		log.Info().Str("type", eventType).Int64("customerId", customerID).Msg("[NOTIFICATION] received event")

		switch eventType {
		case "DISPUTE_FILED":
			disputeID, _ := event["disputeId"].(string)
			log.Info().Str("disputeId", disputeID).Int64("customerId", customerID).Msg("[NOTIFICATION] Dispute filed")
			if email != "" {
				l.svc.SendDisputeAcknowledgement(email, disputeID, customerID)
			} else {
				log.Warn().Int64("customerId", customerID).Msg("[NOTIFICATION] No email in event payload for DISPUTE_FILED")
			}

		case "SCORE_UPDATED":
			score := event["score"]
			log.Info().Int64("customerId", customerID).Interface("score", score).Msg("[NOTIFICATION] Score updated")
			if email != "" {
				l.svc.SendScoreUpdateNotification(email, score, customerID)
			} else {
				log.Warn().Int64("customerId", customerID).Msg("[NOTIFICATION] No email in event payload for SCORE_UPDATED")
			}

		case "CONSENT_GRANTED":
			partnerID := event["partnerId"]
			log.Info().Int64("customerId", customerID).Interface("partnerId", partnerID).Msg("[NOTIFICATION] Consent granted")
			if email != "" {
				l.svc.SendConsentGrantedNotification(email, partnerID, customerID)
			} else {
				log.Warn().Int64("customerId", customerID).Msg("[NOTIFICATION] No email in event payload for CONSENT_GRANTED")
			}

		case "USER_INVITATION":
			token, _ := event["token"].(string)
			log.Info().Str("email", email).Msg("[NOTIFICATION] User invitation")
			if email != "" && token != "" {
				subject := "You've been invited to Athena Credit Score Platform"
				body := fmt.Sprintf(
					"Hello,\n\n"+
						"You have been invited to join the Athena Credit Score Platform.\n\n"+
						"Complete your registration here:\n"+
						"http://localhost:5173/complete-registration?token=%s\n\n"+
						"This link expires in 24 hours.\n\n"+
						"Regards,\nAthena Team", token)
				if err := l.svc.SendEmail("user-service", email, subject, body); err != nil {
					log.Error().Err(err).Msg("[NOTIFICATION] failed to send user invitation email")
				}
			} else {
				log.Warn().Msg("[NOTIFICATION] Missing email or token in USER_INVITATION event")
			}

		default:
			log.Warn().Str("type", eventType).Msg("[NOTIFICATION] Unknown event type")
		}

		_ = msg.Ack(false)
	}
}

func (l *EventListener) consumeDisputes(msgs <-chan amqp.Delivery) {
	for msg := range msgs {
		var event map[string]interface{}
		if err := json.Unmarshal(msg.Body, &event); err != nil {
			log.Error().Err(err).Msg("[DISPUTE-EVENT] failed to unmarshal event")
			_ = msg.Nack(false, false)
			continue
		}

		eventType, _ := event["type"].(string)
		if eventType == "" {
			eventType = "UNKNOWN"
		}
		log.Info().Str("type", eventType).Interface("payload", event).Msg("[DISPUTE-EVENT] received")
		// Routes to compliance team mailbox — configure via /api/v1/notifications/config

		_ = msg.Ack(false)
	}
}

// extractInt64 safely extracts an int64 from a JSON-decoded map value
// which may be a float64 (JSON numbers) or nil.
func extractInt64(m map[string]interface{}, key string) int64 {
	v, ok := m[key]
	if !ok || v == nil {
		return 0
	}
	switch n := v.(type) {
	case float64:
		return int64(n)
	case int64:
		return n
	case json.Number:
		i, _ := n.Int64()
		return i
	default:
		return 0
	}
}
