package handler

import (
	"crypto/rand"
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/athena/customer-service/internal/client"
	"github.com/athena/customer-service/internal/dto"
	"github.com/athena/pkg/errors"
	"github.com/athena/pkg/middleware"
	"github.com/athena/pkg/rabbitmq"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
	"gorm.io/gorm"
)

// CustomerHandler contains all customer-related endpoint handlers.
type CustomerHandler struct {
	db          *gorm.DB
	rabbit      *rabbitmq.Client
	mediaClient *client.MediaClient
}

func NewCustomerHandler(db *gorm.DB, rabbit *rabbitmq.Client, mediaClient *client.MediaClient) *CustomerHandler {
	return &CustomerHandler{db: db, rabbit: rabbit, mediaClient: mediaClient}
}

// RegisterRoutes registers all /api/v1/customers routes.
func (h *CustomerHandler) RegisterRoutes(rg *gin.RouterGroup) {
	customers := rg.Group("/customers")
	{
		customers.GET("", middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER"), h.GetAllCustomers)
		customers.GET("/search", middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER"), h.SearchCustomers)
		customers.POST("", middleware.RequireRoles("ADMIN", "ANALYST"), h.CreateCustomer)
		customers.POST("/whitelist", middleware.RequireRoles("ADMIN"), h.UploadWhitelist)
		customers.GET("/:customerId", middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CUSTOMER"), h.GetProfile)
		customers.PUT("/:customerId", middleware.RequireRoles("ADMIN", "ANALYST"), h.UpdateProfile)
		customers.PUT("/:customerId/approve", middleware.RequireRoles("ADMIN", "ANALYST"), h.ApproveCustomer)
		customers.PUT("/:customerId/reject", middleware.RequireRoles("ADMIN", "ANALYST"), h.RejectCustomer)
		customers.GET("/:customerId/disputes", middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CUSTOMER"), h.GetDisputes)
		customers.POST("/:customerId/disputes", middleware.RequireRoles("ADMIN", "CUSTOMER"), h.FileDispute)
		customers.GET("/:customerId/consents", middleware.RequireRoles("ADMIN", "ANALYST", "CUSTOMER"), h.GetConsents)
		customers.PUT("/:customerId/consent", middleware.RequireRoles("ADMIN", "CUSTOMER"), h.GrantConsent)
		customers.DELETE("/:customerId/consents/:consentId", middleware.RequireRoles("ADMIN", "CUSTOMER"), h.RevokeConsent)
		customers.PUT("/:customerId/identity-document", middleware.RequireRoles("ADMIN", "ANALYST"), h.UpdateIdentityDocument)
	}
}

// ──────────────────────────────────────────────────────────────
// LIST / SEARCH
// ──────────────────────────────────────────────────────────────

func (h *CustomerHandler) GetAllCustomers(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "0"))
	size, _ := strconv.Atoi(c.DefaultQuery("size", "20"))
	if size <= 0 {
		size = 20
	}
	offset := page * size

	var customers []map[string]interface{}
	h.db.Raw(
		"SELECT customer_id, first_name, last_name, mobile_number, email, "+
			"national_id, verification_status, registration_channel, created_at "+
			"FROM customers ORDER BY customer_id ASC LIMIT ? OFFSET ?",
		size, offset,
	).Scan(&customers)

	var total int64
	h.db.Raw("SELECT COUNT(*) FROM customers").Scan(&total)

	totalPages := int(math.Ceil(float64(total) / float64(size)))

	c.JSON(http.StatusOK, gin.H{
		"content":       customers,
		"pageNumber":    page,
		"pageSize":      size,
		"totalElements": total,
		"totalPages":    totalPages,
		"last":          (page + 1) >= totalPages,
	})
}

func (h *CustomerHandler) SearchCustomers(c *gin.Context) {
	query := c.DefaultQuery("q", "")
	likeQuery := "%" + query + "%"

	var idQuery int64 = -1
	if v, err := strconv.ParseInt(query, 10, 64); err == nil {
		idQuery = v
	}

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
		ORDER BY c.customer_id ASC LIMIT 50`

	var results []map[string]interface{}
	h.db.Raw(sql, query, likeQuery, likeQuery, likeQuery, idQuery).Scan(&results)

	c.JSON(http.StatusOK, results)
}

// ──────────────────────────────────────────────────────────────
// CREATE
// ──────────────────────────────────────────────────────────────

func (h *CustomerHandler) CreateCustomer(c *gin.Context) {
	var req dto.CustomerRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		errors.BadRequest(c, "Invalid request body")
		return
	}

	if strings.TrimSpace(req.FirstName) == "" {
		errors.BadRequest(c, "firstName is required")
		return
	}
	if strings.TrimSpace(req.LastName) == "" {
		errors.BadRequest(c, "lastName is required")
		return
	}
	if strings.TrimSpace(req.MobileNumber) == "" {
		errors.BadRequest(c, "mobileNumber is required")
		return
	}
	if strings.TrimSpace(req.NationalID) == "" {
		errors.BadRequest(c, "nationalId is required")
		return
	}

	createdBy := middleware.GetUsername(c)
	regChannel := req.RegistrationChannel
	if regChannel == "" {
		regChannel = "ADMIN_PORTAL"
	}

	// Handle dateOfBirth
	var dob interface{}
	if req.DateOfBirth != nil && *req.DateOfBirth != "" {
		dob = *req.DateOfBirth
	}

	result := h.db.Exec(
		"INSERT INTO customers (first_name, last_name, mobile_number, email, national_id, "+
			"date_of_birth, gender, county, region, bank_name, account_number, "+
			"verification_status, crb_consent, registration_channel, created_by) "+
			"VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
		req.FirstName, req.LastName, req.MobileNumber,
		req.Email, req.NationalID,
		dob,
		req.Gender,
		req.County, req.Region,
		req.BankName, req.AccountNumber,
		"PENDING", false,
		regChannel, createdBy,
	)

	if result.Error != nil {
		// Check for duplicate constraint violations
		if strings.Contains(result.Error.Error(), "duplicate") || strings.Contains(result.Error.Error(), "unique") {
			errors.Conflict(c, "A customer with the same mobile number or national ID already exists.")
			return
		}
		errors.InternalError(c, "Failed to create customer: "+result.Error.Error())
		return
	}

	var saved map[string]interface{}
	h.db.Raw(
		"SELECT * FROM customers WHERE mobile_number = ? ORDER BY created_at DESC LIMIT 1",
		req.MobileNumber,
	).Scan(&saved)

	log.Info().Interface("customer_id", saved["customer_id"]).Str("by", createdBy).Msg("[CUSTOMER] Created customer")
	c.JSON(http.StatusOK, saved)
}

// ──────────────────────────────────────────────────────────────
// READ / UPDATE PROFILE
// ──────────────────────────────────────────────────────────────

func (h *CustomerHandler) GetProfile(c *gin.Context) {
	customerID := c.Param("customerId")

	sql := `SELECT c.customer_id AS id,
		c.first_name || ' ' || c.last_name AS name,
		c.first_name, c.last_name, c.mobile_number AS phone,
		c.email, c.national_id, c.date_of_birth, c.gender,
		c.county, c.region, c.bank_name, c.account_number,
		c.verification_status, c.crb_consent, c.registration_channel, c.created_at,
		c.created_by, c.approved_by, c.approved_at, c.rejection_reason,
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

	var profile map[string]interface{}
	result := h.db.Raw(sql, customerID).Scan(&profile)
	if result.Error != nil || profile == nil {
		errors.NotFound(c, "Customer not found")
		return
	}

	c.JSON(http.StatusOK, profile)
}

func (h *CustomerHandler) UpdateProfile(c *gin.Context) {
	customerID := c.Param("customerId")
	username := middleware.GetUsername(c)

	var updates map[string]interface{}
	if err := c.ShouldBindJSON(&updates); err != nil {
		errors.BadRequest(c, "Invalid request body")
		return
	}

	log.Info().Str("customer", customerID).Str("by", username).Msg("Profile update")
	h.publishEvent("PROFILE_UPDATED", customerID, updates, username)

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

// ──────────────────────────────────────────────────────────────
// MAKER-CHECKER: APPROVE / REJECT
// ──────────────────────────────────────────────────────────────

func (h *CustomerHandler) ApproveCustomer(c *gin.Context) {
	customerID := c.Param("customerId")
	checkerUsername := middleware.GetUsername(c)

	var rows []map[string]interface{}
	h.db.Raw("SELECT created_by FROM customers WHERE customer_id = ?", customerID).Scan(&rows)
	if len(rows) == 0 {
		errors.NotFound(c, "Customer not found: "+customerID)
		return
	}

	createdBy, _ := rows[0]["created_by"].(string)
	if createdBy != "" && createdBy == checkerUsername {
		errors.Forbidden(c, "Maker-checker segregation required: cannot approve a customer you created.")
		return
	}

	h.db.Exec(
		"UPDATE customers SET verification_status = 'APPROVED', approved_by = ?, approved_at = NOW() "+
			"WHERE customer_id = ?",
		checkerUsername, customerID,
	)

	log.Info().Str("customer", customerID).Str("by", checkerUsername).Msg("[MAKER-CHECKER] Customer approved")
	h.publishEvent("CUSTOMER_APPROVED", customerID, map[string]string{"approvedBy": checkerUsername}, checkerUsername)

	c.JSON(http.StatusOK, gin.H{
		"customer_id": customerID,
		"status":      "APPROVED",
		"approved_by": checkerUsername,
		"approved_at": time.Now().Format(time.RFC3339),
	})
}

func (h *CustomerHandler) RejectCustomer(c *gin.Context) {
	customerID := c.Param("customerId")
	checkerUsername := middleware.GetUsername(c)

	var body map[string]string
	if err := c.ShouldBindJSON(&body); err != nil {
		body = map[string]string{}
	}
	reason := body["reason"]

	var rows []map[string]interface{}
	h.db.Raw("SELECT created_by FROM customers WHERE customer_id = ?", customerID).Scan(&rows)
	if len(rows) == 0 {
		errors.NotFound(c, "Customer not found: "+customerID)
		return
	}

	createdBy, _ := rows[0]["created_by"].(string)
	if createdBy != "" && createdBy == checkerUsername {
		errors.Forbidden(c, "Maker-checker segregation required: cannot reject a customer you created.")
		return
	}

	h.db.Exec(
		"UPDATE customers SET verification_status = 'REJECTED', approved_by = ?, "+
			"approved_at = NOW(), rejection_reason = ? WHERE customer_id = ?",
		checkerUsername, reason, customerID,
	)

	log.Info().Str("customer", customerID).Str("by", checkerUsername).Str("reason", reason).Msg("[MAKER-CHECKER] Customer rejected")

	c.JSON(http.StatusOK, gin.H{
		"customer_id":      customerID,
		"status":           "REJECTED",
		"rejection_reason": reason,
		"rejected_by":      checkerUsername,
	})
}

// ──────────────────────────────────────────────────────────────
// DISPUTES
// ──────────────────────────────────────────────────────────────

func (h *CustomerHandler) GetDisputes(c *gin.Context) {
	customerID := c.Param("customerId")

	var disputes []map[string]interface{}
	h.db.Raw(
		"SELECT dispute_id as id, COALESCE(disputed_field, reason) as field, "+
			"reason as desc, status, CAST(created_at AS DATE) as filed "+
			"FROM disputes WHERE customer_id = ? ORDER BY created_at DESC",
		customerID,
	).Scan(&disputes)

	c.JSON(http.StatusOK, gin.H{
		"customer_id": customerID,
		"disputes":    disputes,
	})
}

func (h *CustomerHandler) FileDispute(c *gin.Context) {
	customerID := c.Param("customerId")

	var body map[string]string
	if err := c.ShouldBindJSON(&body); err != nil {
		errors.BadRequest(c, "Invalid request body")
		return
	}

	description := body["description"]
	field := body["disputed_field"]

	log.Info().Str("customer", customerID).Str("field", field).Msg("Dispute filed")

	var disputedField interface{}
	if field != "" {
		disputedField = field
	}

	h.db.Exec(
		"INSERT INTO disputes (customer_id, reason, disputed_field, status) VALUES (?, ?, ?, 'OPEN')",
		customerID, description, disputedField,
	)

	// Fetch newly created dispute_id
	var disputeDBID int64
	h.db.Raw(
		"SELECT dispute_id FROM disputes WHERE customer_id = ? ORDER BY created_at DESC LIMIT 1",
		customerID,
	).Scan(&disputeDBID)

	disputeID := fmt.Sprintf("DSP-%d", disputeDBID)

	now := time.Now().Format(time.RFC3339)
	if h.rabbit != nil {
		_ = h.rabbit.Publish(rabbitmq.NotificationKey, map[string]interface{}{
			"type":        "DISPUTE_FILED",
			"disputeId":   disputeID,
			"customerId":  customerID,
			"field":       field,
			"description": description,
			"filedAt":     now,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"dispute_id":     disputeID,
		"customer_id":    customerID,
		"status":         "OPEN",
		"disputed_field": field,
		"filed_at":       now,
		"message":        "Dispute filed. Our team will review within 5 business days.",
	})
}

// ──────────────────────────────────────────────────────────────
// CONSENT
// ──────────────────────────────────────────────────────────────

// javaStringHashCode replicates Java's String.hashCode() algorithm.
func javaStringHashCode(s string) int64 {
	var h int32
	for _, ch := range s {
		h = 31*h + int32(ch)
	}
	if h < 0 {
		h = -h
	}
	return int64(h)
}

func (h *CustomerHandler) GrantConsent(c *gin.Context) {
	customerID := c.Param("customerId")
	username := middleware.GetUsername(c)

	var body map[string]string
	if err := c.ShouldBindJSON(&body); err != nil {
		errors.BadRequest(c, "Invalid request body")
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

	consentToken := generateUUID()
	partnerIDLong := javaStringHashCode(partnerID)

	h.db.Exec(
		"INSERT INTO consents (customer_id, partner_id, scope, token_jti, expires_at) "+
			"VALUES (?, ?, ?, ?, NOW() + INTERVAL '1 year') ON CONFLICT (token_jti) DO NOTHING",
		customerID, partnerIDLong, scope, consentToken,
	)

	h.publishEvent("CONSENT_GRANTED", customerID, map[string]string{"partner_id": partnerID, "scope": scope}, username)

	c.JSON(http.StatusOK, gin.H{
		"consent_token": consentToken,
		"customer_id":   customerID,
		"partner_id":    partnerID,
		"scope":         scope,
		"expires_at":    time.Now().AddDate(1, 0, 0).Format(time.RFC3339),
	})
}

func (h *CustomerHandler) GetConsents(c *gin.Context) {
	customerID := c.Param("customerId")

	sql := `SELECT consent_id as id,
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
		ORDER BY created_at DESC`

	var consents []map[string]interface{}
	h.db.Raw(sql, customerID).Scan(&consents)

	c.JSON(http.StatusOK, consents)
}

func (h *CustomerHandler) RevokeConsent(c *gin.Context) {
	customerID := c.Param("customerId")
	consentID := c.Param("consentId")

	result := h.db.Exec(
		"UPDATE consents SET revoked = true WHERE customer_id = ? AND consent_id = ?",
		customerID, consentID,
	)

	log.Info().Str("customer", customerID).Str("consentId", consentID).Int64("rows", result.RowsAffected).Msg("[CONSENT] Revoked")

	c.JSON(http.StatusOK, gin.H{
		"customer_id": customerID,
		"consent_id":  consentID,
		"revoked":     result.RowsAffected > 0,
	})
}

// ──────────────────────────────────────────────────────────────
// IDENTITY DOCUMENT
// ──────────────────────────────────────────────────────────────

func (h *CustomerHandler) UpdateIdentityDocument(c *gin.Context) {
	customerID := c.Param("customerId")
	documentID := c.Query("documentId")
	username := middleware.GetUsername(c)

	if documentID == "" {
		errors.BadRequest(c, "documentId query parameter is required")
		return
	}

	media, err := h.mediaClient.GetMediaMetadata(documentID)
	if err != nil {
		log.Error().Str("documentId", documentID).Err(err).Msg("[CUSTOMER] Failed to validate media")
		errors.NotFound(c, "Invalid document ID. Media not found in media-service.")
		return
	}
	log.Info().Str("documentId", documentID).Str("file", media.OriginalFilename).Msg("[CUSTOMER] Media validated")

	h.db.Exec(
		"UPDATE customers SET identity_document_id = ? WHERE customer_id = ?",
		documentID, customerID,
	)

	log.Info().Str("document", documentID).Str("customer", customerID).Msg("[CUSTOMER] Identity document linked")

	c.JSON(http.StatusOK, gin.H{
		"customer_id": customerID,
		"document_id": documentID,
		"linked_by":   username,
		"linked_at":   time.Now().Format(time.RFC3339),
	})
}

// ──────────────────────────────────────────────────────────────
// CSV WHITELIST UPLOAD
// ──────────────────────────────────────────────────────────────

func (h *CustomerHandler) UploadWhitelist(c *gin.Context) {
	file, err := c.FormFile("file")
	if err != nil || file.Size == 0 {
		errors.BadRequest(c, "Please upload a valid CSV file.")
		return
	}

	f, err := file.Open()
	if err != nil {
		errors.InternalError(c, "Failed to open uploaded file")
		return
	}
	defer f.Close()

	reader := csv.NewReader(f)

	// Read header
	header, err := reader.Read()
	if err != nil {
		errors.BadRequest(c, "Failed to parse CSV header: "+err.Error())
		return
	}

	// Build column index map (case-insensitive)
	colIndex := make(map[string]int)
	for i, col := range header {
		colIndex[strings.ToLower(strings.TrimSpace(col))] = i
	}

	username := middleware.GetUsername(c)
	var processed []string
	var skipped []string

	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}

		phone := getCSVField(record, colIndex, "phonenumber")

		// Check if customer already exists
		var count int64
		h.db.Raw("SELECT COUNT(*) FROM customers WHERE mobile_number = ?", phone).Scan(&count)
		if count > 0 {
			skipped = append(skipped, phone)
			continue
		}

		name := getCSVField(record, colIndex, "name")
		parts := strings.SplitN(name, " ", 2)
		firstName := parts[0]
		lastName := ""
		if len(parts) > 1 {
			lastName = parts[1]
		}

		dobStr := getCSVField(record, colIndex, "dateofbirth")
		var dob interface{}
		if dobStr != "" {
			// Validate date format
			if _, parseErr := time.Parse("2006-01-02", dobStr); parseErr == nil {
				dob = dobStr
			}
		}

		gender := strings.ToUpper(getCSVField(record, colIndex, "gender"))
		if gender == "" {
			gender = "MALE"
		}
		nationalID := getCSVField(record, colIndex, "nationalid")
		email := getCSVField(record, colIndex, "email")

		h.db.Exec(
			"INSERT INTO customers (first_name, last_name, mobile_number, email, national_id, "+
				"date_of_birth, gender, verification_status, crb_consent, registration_channel, created_by) "+
				"VALUES (?,?,?,?,?,?,?,'APPROVED',true,'PARTNER_API',?)",
			firstName, lastName, phone, email, nationalID,
			dob, gender, username,
		)
		processed = append(processed, phone)
	}

	log.Info().Int("processed", len(processed)).Int("skipped", len(skipped)).Msg("[CUSTOMER] Whitelist CSV")

	c.JSON(http.StatusOK, gin.H{
		"processed":      len(processed),
		"skipped":        len(skipped),
		"skipped_phones": skipped,
		"message":        "Whitelist upload completed successfully.",
	})
}

// ──────────────────────────────────────────────────────────────
// INTERNAL HELPERS
// ──────────────────────────────────────────────────────────────

func (h *CustomerHandler) publishEvent(eventType, customerID string, payload interface{}, actor string) {
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
		log.Error().Err(err).Msg("Event publish failed")
	}
}

func getCSVField(record []string, colIndex map[string]int, field string) string {
	if idx, ok := colIndex[field]; ok && idx < len(record) {
		return strings.TrimSpace(record[idx])
	}
	return ""
}

func generateUUID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40 // version 4
	b[8] = (b[8] & 0x3f) | 0x80 // variant
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
