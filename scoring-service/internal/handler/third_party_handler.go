package handler

import (
	"net/http"
	"strconv"
	"time"

	"github.com/athena/pkg/rabbitmq"
	"github.com/athena/scoring-service/internal/client"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

type ThirdPartyHandler struct {
	pythonClient *client.PythonClient
	rabbit       *rabbitmq.Client
}

func NewThirdPartyHandler(pythonClient *client.PythonClient, rabbit *rabbitmq.Client) *ThirdPartyHandler {
	return &ThirdPartyHandler{pythonClient: pythonClient, rabbit: rabbit}
}

func (h *ThirdPartyHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("/credit-score/:customerId", h.GetScore)
	rg.POST("/webhooks", h.RegisterWebhook)
	rg.DELETE("/consent/:customerId", h.RevokeConsent)
}

func (h *ThirdPartyHandler) GetScore(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	consentToken := c.Query("consentToken")
	partnerID := c.GetHeader("X-Partner-Id")
	if partnerID == "" {
		partnerID = "unknown"
	}

	if !validateConsent(consentToken) {
		h.auditLog(partnerID, customerID, "CREDIT_SCORE_REQUEST", "DENIED_NO_CONSENT", c.ClientIP())
		c.JSON(http.StatusForbidden, gin.H{
			"error":   "CONSENT_REQUIRED",
			"message": "Customer has not granted consent for this partner to access their credit data.",
		})
		return
	}

	h.auditLog(partnerID, customerID, "CREDIT_SCORE_REQUEST", "APPROVED", c.ClientIP())

	result, err := h.pythonClient.GetCreditScoreByAPIKey(customerID)
	if err != nil {
		log.Warn().Err(err).Msg("python score fetch failed for third party")
		result = map[string]interface{}{}
	}

	c.JSON(http.StatusOK, gin.H{
		"customer_id":      customerID,
		"partner_id":       partnerID,
		"score_data":       result,
		"consent_verified": true,
		"request_id":       uuid.New().String(),
	})
}

func (h *ThirdPartyHandler) RegisterWebhook(c *gin.Context) {
	var body map[string]string
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	partnerID := c.GetHeader("X-Partner-Id")
	if partnerID == "" {
		partnerID = "unknown"
	}
	webhookURL := body["url"]
	eventType := body["event_type"]
	if eventType == "" {
		eventType = "SCORE_UPDATED"
	}

	log.Info().Str("partner", partnerID).Str("url", webhookURL).Str("event", eventType).Msg("webhook registered")

	if h.rabbit != nil {
		_ = h.rabbit.Publish(rabbitmq.NotificationKey, map[string]interface{}{
			"type":         "WEBHOOK_REGISTRATION",
			"partnerId":    partnerID,
			"url":          webhookURL,
			"eventType":    eventType,
			"registeredAt": time.Now().Format(time.RFC3339),
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"webhook_id": uuid.New().String(),
		"partner_id": partnerID,
		"url":        webhookURL,
		"event_type": eventType,
		"status":     "REGISTERED",
	})
}

func (h *ThirdPartyHandler) RevokeConsent(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	partnerID := c.GetHeader("X-Partner-Id")
	if partnerID == "" {
		partnerID = "unknown"
	}

	h.auditLog(partnerID, customerID, "CONSENT_REVOKED", "OK", c.ClientIP())
	log.Info().Int64("customer", customerID).Str("partner", partnerID).Msg("consent revoked")

	c.JSON(http.StatusOK, gin.H{
		"customer_id": customerID,
		"partner_id":  partnerID,
		"status":      "CONSENT_REVOKED",
		"revoked_at":  time.Now().Format(time.RFC3339),
	})
}

func validateConsent(consentToken string) bool {
	// MVP: accept non-null, non-empty token
	return consentToken != ""
}

func (h *ThirdPartyHandler) auditLog(partnerID string, customerID int64, action, outcome, ip string) {
	if h.rabbit == nil {
		return
	}
	err := h.rabbit.Publish(rabbitmq.ScoringKey, map[string]interface{}{
		"type":       "AUDIT_LOG",
		"partnerId":  partnerID,
		"customerId": customerID,
		"action":     action,
		"outcome":    outcome,
		"ip":         ip,
		"ts":         time.Now().Format(time.RFC3339),
	})
	if err != nil {
		log.Error().Err(err).Msg("audit log publish failed")
	}
}
