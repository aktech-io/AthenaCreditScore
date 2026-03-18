package handler

import (
	"math"
	"net/http"
	"strconv"
	"time"

	"github.com/athena/pkg/middleware"
	"github.com/athena/pkg/rabbitmq"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
	"gorm.io/gorm"
)

type CustomerProfileHandler struct {
	db     *gorm.DB
	rabbit *rabbitmq.Client
}

func NewCustomerProfileHandler(db *gorm.DB, rabbit *rabbitmq.Client) *CustomerProfileHandler {
	return &CustomerProfileHandler{db: db, rabbit: rabbit}
}

func (h *CustomerProfileHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("/search",
		middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER"),
		h.SearchCustomers)
	rg.GET("/:customerId",
		middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CUSTOMER"),
		h.GetProfile)
	rg.PUT("/:customerId",
		middleware.RequireRoles("ADMIN", "ANALYST", "CUSTOMER"),
		h.UpdateProfile)
	rg.POST("/:customerId/disputes",
		middleware.RequireRoles("ADMIN", "CUSTOMER"),
		h.FileDispute)
	rg.GET("/:customerId/disputes",
		middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CUSTOMER"),
		h.GetDisputes)
	rg.GET("/:customerId/consents",
		middleware.RequireRoles("ADMIN", "CUSTOMER"),
		h.GetConsents)
	rg.DELETE("/:customerId/consents/:consentId",
		middleware.RequireRoles("ADMIN", "CUSTOMER"),
		h.RevokeConsent)
	rg.PUT("/:customerId/consent",
		middleware.RequireRoles("ADMIN", "CUSTOMER"),
		h.GrantConsent)
}

func (h *CustomerProfileHandler) SearchCustomers(c *gin.Context) {
	query := c.DefaultQuery("q", "")
	likeQuery := "%" + query + "%"
	var idQuery int64 = -1
	if id, err := strconv.ParseInt(query, 10, 64); err == nil {
		idQuery = id
	}

	var results []map[string]interface{}
	sql := `SELECT c.customer_id as id, c.first_name || ' ' || c.last_name as name,
			c.mobile_number as phone, 'General' as sector,
			COALESCE(cse.final_score, 0) as score,
			COALESCE(cse.pd_probability, 0.0) as pd
			FROM customers c
			LEFT JOIN (SELECT DISTINCT ON (customer_id) customer_id, final_score, pd_probability
			           FROM credit_score_events ORDER BY customer_id, scored_at DESC) cse
			ON c.customer_id = cse.customer_id
			WHERE ? = '' OR c.first_name ILIKE ? OR c.last_name ILIKE ? OR c.mobile_number ILIKE ?
			OR c.customer_id = ?
			ORDER BY c.customer_id ASC
			LIMIT 50`

	h.db.Raw(sql, query, likeQuery, likeQuery, likeQuery, idQuery).Scan(&results)
	if results == nil {
		results = []map[string]interface{}{}
	}
	c.JSON(http.StatusOK, results)
}

func (h *CustomerProfileHandler) GetProfile(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	var profile map[string]interface{}
	sql := `SELECT c.customer_id AS id,
			c.first_name || ' ' || c.last_name AS name,
			c.first_name, c.last_name, c.mobile_number AS phone,
			c.email, c.national_id, c.date_of_birth, c.gender,
			c.county, c.region, c.bank_name, c.account_number,
			c.verification_status, c.crb_consent, c.registration_channel, c.created_at,
			COALESCE(cse.final_score, 0) AS score,
			COALESCE(cse.score_band, 'N/A') AS score_band,
			COALESCE(cse.pd_probability, 0.0) AS pd_probability,
			cse.scored_at
			FROM customers c
			LEFT JOIN (
			    SELECT DISTINCT ON (customer_id)
			           customer_id, final_score, score_band, pd_probability, scored_at
			    FROM credit_score_events ORDER BY customer_id, scored_at DESC
			) cse ON c.customer_id = cse.customer_id
			WHERE c.customer_id = ?`

	result := h.db.Raw(sql, customerID).Scan(&profile)
	if result.Error != nil || profile == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error":       "Customer not found",
			"customer_id": customerID,
		})
		return
	}

	c.JSON(http.StatusOK, profile)
}

func (h *CustomerProfileHandler) UpdateProfile(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	var updates map[string]interface{}
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	actor := middleware.GetUsername(c)
	log.Info().Int64("customer", customerID).Str("by", actor).Msg("profile update")

	h.publishEvent("PROFILE_UPDATED", customerID, updates, actor)

	keys := make([]string, 0, len(updates))
	for k := range updates {
		keys = append(keys, k)
	}

	c.JSON(http.StatusOK, gin.H{
		"customer_id":    customerID,
		"updated_fields": keys,
		"updated_at":     time.Now().Format(time.RFC3339),
	})
}

func (h *CustomerProfileHandler) FileDispute(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	var body map[string]string
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	disputeID := "DSP-" + uuid.New().String()[:8]
	description := body["description"]
	field := body["disputed_field"]

	log.Info().Int64("customer", customerID).Str("disputeId", disputeID).Str("field", field).Msg("dispute filed")

	reason := description
	if reason == "" {
		reason = field
	}
	h.db.Exec("INSERT INTO disputes (customer_id, reason, status) VALUES (?, ?, 'OPEN')", customerID, reason)

	// Publish notification
	if h.rabbit != nil {
		_ = h.rabbit.Publish(rabbitmq.NotificationKey, map[string]interface{}{
			"type":        "DISPUTE_FILED",
			"disputeId":   disputeID,
			"customerId":  customerID,
			"field":       field,
			"description": description,
			"filedAt":     time.Now().Format(time.RFC3339),
		})
	}

	now := time.Now().Format(time.RFC3339)
	c.JSON(http.StatusOK, gin.H{
		"dispute_id":     disputeID,
		"customer_id":    customerID,
		"status":         "OPEN",
		"disputed_field": field,
		"filed_at":       now,
		"message":        "Dispute filed. Our team will review within 5 business days.",
	})
}

func (h *CustomerProfileHandler) GetDisputes(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	var disputes []map[string]interface{}
	h.db.Raw(`SELECT dispute_id as id, COALESCE(disputed_field, reason) as field,
			reason as desc, status, CAST(created_at AS DATE) as filed
			FROM disputes WHERE customer_id = ? ORDER BY created_at DESC`, customerID).Scan(&disputes)

	if disputes == nil {
		disputes = []map[string]interface{}{}
	}
	c.JSON(http.StatusOK, disputes)
}

func (h *CustomerProfileHandler) GetConsents(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	var consents []map[string]interface{}
	h.db.Raw(`SELECT consent_id as id,
			CASE partner_id
			  WHEN 1178866990 THEN 'KCB Bank'
			  WHEN 492889783  THEN 'Equity Bank'
			  WHEN 1069688314 THEN 'Co-operative Bank'
			  WHEN 723158978  THEN 'Safaricom M-Pesa'
			  WHEN 327945913  THEN 'Standard Chartered'
			  WHEN 1894859336 THEN 'NCBA Bank'
			  WHEN 1188602069 THEN 'Absa Kenya'
			  WHEN 1709023242 THEN 'DTB Bank'
			  WHEN 1558763374 THEN 'Stanbic Bank'
			  WHEN 609826168  THEN 'Family Bank'
			  ELSE CAST(partner_id AS VARCHAR) END as name,
			scope, CAST(created_at AS DATE) as granted
			FROM consents WHERE customer_id = ? AND revoked = false
			ORDER BY created_at DESC`, customerID).Scan(&consents)

	if consents == nil {
		consents = []map[string]interface{}{}
	}
	c.JSON(http.StatusOK, consents)
}

func (h *CustomerProfileHandler) RevokeConsent(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}
	consentID, err := strconv.ParseInt(c.Param("consentId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid consentId"})
		return
	}

	result := h.db.Exec("UPDATE consents SET revoked = true WHERE customer_id = ? AND consent_id = ?",
		customerID, consentID)
	log.Info().Int64("customer", customerID).Int64("consentId", consentID).
		Int64("rows", result.RowsAffected).Msg("consent revoked")

	c.JSON(http.StatusOK, gin.H{
		"customer_id": customerID,
		"consent_id":  consentID,
		"revoked":     result.RowsAffected > 0,
	})
}

func (h *CustomerProfileHandler) GrantConsent(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	var body map[string]string
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	partnerID := body["partner_id"]
	if partnerID == "" {
		partnerID = "unknown"
	}
	scope := body["scope"]
	if scope == "" {
		scope = "CREDIT_SCORE"
	}
	consentToken := uuid.New().String()

	log.Info().Int64("customer", customerID).Str("partner", partnerID).Str("scope", scope).Msg("consent granted")

	// Java's String.hashCode() implementation
	partnerIDLong := int64(math.Abs(float64(javaStringHashCode(partnerID))))
	h.db.Exec(`INSERT INTO consents (customer_id, partner_id, scope, token_jti, expires_at)
			VALUES (?, ?, ?, ?, NOW() + INTERVAL '1 year')
			ON CONFLICT (token_jti) DO NOTHING`,
		customerID, partnerIDLong, scope, consentToken)

	actor := middleware.GetUsername(c)
	h.publishEvent("CONSENT_GRANTED", customerID, map[string]interface{}{
		"partner_id": partnerID,
		"scope":      scope,
	}, actor)

	c.JSON(http.StatusOK, gin.H{
		"consent_token": consentToken,
		"customer_id":   customerID,
		"partner_id":    partnerID,
		"scope":         scope,
		"expires_at":    time.Now().AddDate(1, 0, 0).Format(time.RFC3339),
	})
}

func (h *CustomerProfileHandler) publishEvent(eventType string, customerID int64, payload interface{}, actor string) {
	if h.rabbit == nil {
		return
	}
	err := h.rabbit.Publish(rabbitmq.ScoringKey, map[string]interface{}{
		"type":       eventType,
		"customerId": customerID,
		"payload":    payload,
		"actor":      actor,
		"ts":         time.Now().Format(time.RFC3339),
	})
	if err != nil {
		log.Error().Err(err).Msg("event publish failed")
	}
}

// javaStringHashCode replicates Java's String.hashCode() algorithm.
func javaStringHashCode(s string) int32 {
	var h int32
	for _, c := range s {
		h = 31*h + int32(c)
	}
	return h
}
