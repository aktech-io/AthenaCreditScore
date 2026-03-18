package handler

import (
	"fmt"
	"net/http"
	"strconv"

	"github.com/athena/pkg/jwt"
	apierrors "github.com/athena/pkg/errors"
	"github.com/athena/user-service/internal/dto"
	"github.com/athena/user-service/internal/repository"
	"github.com/athena/user-service/internal/service"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

type AuthHandler struct {
	adminUserRepo *repository.AdminUserRepository
	jwtUtil       *jwt.JWTUtil
	authService   *service.AuthService
	db            *gorm.DB
}

func NewAuthHandler(
	adminUserRepo *repository.AdminUserRepository,
	jwtUtil *jwt.JWTUtil,
	authService *service.AuthService,
	db *gorm.DB,
) *AuthHandler {
	return &AuthHandler{
		adminUserRepo: adminUserRepo,
		jwtUtil:       jwtUtil,
		authService:   authService,
		db:            db,
	}
}

func (h *AuthHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.POST("/admin/login", h.AdminLogin)
	rg.POST("/customer/request-otp", h.RequestOTP)
	rg.POST("/customer/verify-otp", h.VerifyOTP)
	rg.POST("/customer/demo-token", h.DemoToken)
	rg.POST("/user/login", h.UserLogin)
	rg.POST("/login", h.PortalLogin)
}

// AdminLogin authenticates an admin user via the admin_users table.
func (h *AuthHandler) AdminLogin(c *gin.Context) {
	var req dto.AuthRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierrors.BadRequest(c, "username and password are required")
		return
	}

	admin, err := h.adminUserRepo.FindByUsername(req.Username)
	if err != nil {
		apierrors.Unauthorized(c, "Invalid username or password")
		return
	}

	if err := bcrypt.CompareHashAndPassword([]byte(admin.PasswordHash), []byte(req.Password)); err != nil {
		apierrors.Unauthorized(c, "Invalid username or password")
		return
	}

	roles := []string{admin.Role}
	token, err := h.jwtUtil.GenerateToken(req.Username, roles, nil)
	if err != nil {
		apierrors.InternalError(c, "failed to generate token")
		return
	}

	log.Info().Str("username", req.Username).Msg("Admin login successful")
	c.JSON(http.StatusOK, dto.AuthResponse{
		Token:    token,
		Username: req.Username,
		Roles:    roles,
	})
}

// RequestOTP is a stub that returns "OTP sent".
func (h *AuthHandler) RequestOTP(c *gin.Context) {
	phone := c.Query("phone")
	if phone == "" {
		phone = c.PostForm("phone")
	}
	log.Info().Str("phone", phone).Msg("OTP requested")
	c.JSON(http.StatusOK, "OTP sent to "+phone)
}

// VerifyOTP checks hardcoded OTP "123456" and looks up customer by mobile_number.
func (h *AuthHandler) VerifyOTP(c *gin.Context) {
	phone := c.Query("phone")
	if phone == "" {
		phone = c.PostForm("phone")
	}
	otp := c.Query("otp")
	if otp == "" {
		otp = c.PostForm("otp")
	}

	if otp != "123456" {
		c.Status(http.StatusUnauthorized)
		return
	}

	// Look up customerId by phone
	var customerID *int64
	var cidVal int64
	err := h.db.Raw("SELECT customer_id FROM customers WHERE mobile_number = ?", phone).Scan(&cidVal).Error
	if err == nil && cidVal != 0 {
		customerID = &cidVal
	}

	subject := phone
	if customerID != nil {
		subject = strconv.FormatInt(*customerID, 10)
	}

	token, err := h.jwtUtil.GenerateToken(subject, []string{"CUSTOMER"}, customerID)
	if err != nil {
		apierrors.InternalError(c, "failed to generate token")
		return
	}

	c.JSON(http.StatusOK, dto.AuthResponse{
		Token:      token,
		Username:   subject,
		Roles:      []string{"CUSTOMER"},
		CustomerID: customerID,
	})
}

// DemoToken generates a signed demo JWT for a customer (dev/testing only).
func (h *AuthHandler) DemoToken(c *gin.Context) {
	cidStr := c.Query("customerId")
	if cidStr == "" {
		cidStr = c.PostForm("customerId")
	}
	customerID, err := strconv.ParseInt(cidStr, 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "customerId is required")
		return
	}

	subject := strconv.FormatInt(customerID, 10)
	token, tokenErr := h.jwtUtil.GenerateToken(subject, []string{"CUSTOMER"}, &customerID)
	if tokenErr != nil {
		apierrors.InternalError(c, "failed to generate token")
		return
	}

	log.Info().Int64("customerId", customerID).Msg("Demo token issued")
	c.JSON(http.StatusOK, dto.AuthResponse{
		Token:      token,
		Username:   subject,
		Roles:      []string{"CUSTOMER"},
		CustomerID: &customerID,
	})
}

// UserLogin authenticates an internal user via the users table (AuthService).
func (h *AuthHandler) UserLogin(c *gin.Context) {
	var req dto.AuthRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierrors.BadRequest(c, "username and password are required")
		return
	}

	resp, err := h.authService.Authenticate(req)
	if err != nil {
		apierrors.Unauthorized(c, "Invalid username or password")
		return
	}

	log.Info().Str("username", req.Username).Msg("Internal user login")
	c.JSON(http.StatusOK, resp)
}

// PortalLogin is the unified login for the portal.
// Tries admin auth first, then customer lookup by mobile_number or email.
func (h *AuthHandler) PortalLogin(c *gin.Context) {
	var req dto.AuthRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierrors.BadRequest(c, "username and password are required")
		return
	}

	// 1. Try admin/internal-user authentication
	admin, err := h.adminUserRepo.FindByUsername(req.Username)
	if err == nil {
		if bcryptErr := bcrypt.CompareHashAndPassword([]byte(admin.PasswordHash), []byte(req.Password)); bcryptErr == nil {
			roles := []string{admin.Role}
			primaryRole := admin.Role
			if primaryRole == "" {
				primaryRole = "ADMIN"
			}
			token, tokenErr := h.jwtUtil.GenerateToken(req.Username, roles, nil)
			if tokenErr != nil {
				apierrors.InternalError(c, "failed to generate token")
				return
			}
			log.Info().Str("username", req.Username).Msg("Portal admin login")
			c.JSON(http.StatusOK, dto.PortalLoginResponse{
				Token: token,
				User: dto.UserInfo{
					ID:        req.Username,
					Email:     req.Username,
					FirstName: req.Username,
					LastName:  "",
					Role:      primaryRole,
				},
			})
			return
		}
	}

	// 2. Customer lookup by phone or email
	lookup := req.Username
	var result struct {
		CustomerID int64  `gorm:"column:customer_id"`
		FirstName  string `gorm:"column:first_name"`
		LastName   string `gorm:"column:last_name"`
		Email      string `gorm:"column:email"`
	}

	sql := "SELECT customer_id, first_name, last_name, email FROM customers WHERE mobile_number = ? OR email = ? LIMIT 1"
	if err := h.db.Raw(sql, lookup, lookup).Scan(&result).Error; err != nil || result.CustomerID == 0 {
		log.Warn().Str("username", lookup).Msg("Portal login failed")
		c.Status(http.StatusUnauthorized)
		return
	}

	cidStr := fmt.Sprintf("%d", result.CustomerID)
	token, tokenErr := h.jwtUtil.GenerateTokenWithTenant(cidStr, []string{"CUSTOMER"}, &result.CustomerID, "admin")
	if tokenErr != nil {
		apierrors.InternalError(c, "failed to generate token")
		return
	}

	log.Info().Int64("customerId", result.CustomerID).Msg("Portal customer login")
	c.JSON(http.StatusOK, dto.PortalLoginResponse{
		Token: token,
		User: dto.UserInfo{
			ID:         cidStr,
			Email:      result.Email,
			FirstName:  result.FirstName,
			LastName:   result.LastName,
			Role:       "CUSTOMER",
			CustomerID: cidStr,
		},
	})
}
