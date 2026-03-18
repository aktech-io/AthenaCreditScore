package handler

import (
	"net/http"
	"strconv"

	"github.com/athena/pkg/jwt"
	"github.com/athena/scoring-service/internal/dto"
	"github.com/athena/scoring-service/internal/model"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

type AuthHandler struct {
	db      *gorm.DB
	jwtUtil *jwt.JWTUtil
}

func NewAuthHandler(db *gorm.DB, jwtUtil *jwt.JWTUtil) *AuthHandler {
	return &AuthHandler{db: db, jwtUtil: jwtUtil}
}

func (h *AuthHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.POST("/admin/login", h.AdminLogin)
	rg.POST("/customer/request-otp", h.RequestOTP)
	rg.POST("/customer/verify-otp", h.VerifyOTP)
	rg.POST("/customer/demo-token", h.DemoToken)
}

// AdminLogin authenticates admin user via bcrypt and returns JWT.
func (h *AuthHandler) AdminLogin(c *gin.Context) {
	var req dto.AuthRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request", "message": err.Error()})
		return
	}

	var admin model.AdminUser
	if err := h.db.Where("username = ?", req.Username).First(&admin).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized", "message": "Invalid credentials"})
		return
	}
	if !admin.Active {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized", "message": "Account disabled"})
		return
	}

	if err := bcrypt.CompareHashAndPassword([]byte(admin.PasswordHash), []byte(req.Password)); err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized", "message": "Invalid credentials"})
		return
	}

	roles := []string{admin.Role}
	token, err := h.jwtUtil.GenerateToken(admin.Username, roles, nil)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Token generation failed"})
		return
	}

	log.Info().Str("username", admin.Username).Msg("admin login successful")
	c.JSON(http.StatusOK, dto.AuthResponse{
		Token:    token,
		Username: admin.Username,
		Roles:    roles,
	})
}

// RequestOTP sends an OTP to the customer's phone (stub).
func (h *AuthHandler) RequestOTP(c *gin.Context) {
	phone := c.Query("phone")
	if phone == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "phone parameter required"})
		return
	}
	log.Info().Str("phone", phone).Msg("OTP requested")
	c.JSON(http.StatusOK, "OTP sent to "+phone)
}

// VerifyOTP verifies OTP (hardcoded "123456") and returns JWT.
func (h *AuthHandler) VerifyOTP(c *gin.Context) {
	phone := c.Query("phone")
	otp := c.Query("otp")

	if otp != "123456" {
		c.Status(http.StatusUnauthorized)
		return
	}

	// Look up customerId by phone
	var customerID *int64
	var cid int64
	err := h.db.Raw("SELECT customer_id FROM customers WHERE mobile_number = ?", phone).Scan(&cid).Error
	if err == nil && cid > 0 {
		customerID = &cid
	}

	subject := phone
	if customerID != nil {
		subject = strconv.FormatInt(*customerID, 10)
	}

	roles := []string{"CUSTOMER"}
	token, err := h.jwtUtil.GenerateToken(subject, roles, customerID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Token generation failed"})
		return
	}

	c.JSON(http.StatusOK, dto.AuthResponse{
		Token:      token,
		Username:   subject,
		Roles:      roles,
		CustomerID: customerID,
	})
}

// DemoToken generates a signed demo JWT for a customer (dev/testing only).
func (h *AuthHandler) DemoToken(c *gin.Context) {
	cidStr := c.Query("customerId")
	cid, err := strconv.ParseInt(cidStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	subject := strconv.FormatInt(cid, 10)
	roles := []string{"CUSTOMER"}
	token, err := h.jwtUtil.GenerateToken(subject, roles, &cid)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Token generation failed"})
		return
	}

	log.Info().Int64("customerId", cid).Msg("demo token issued")
	c.JSON(http.StatusOK, dto.AuthResponse{
		Token:      token,
		Username:   subject,
		Roles:      roles,
		CustomerID: &cid,
	})
}
