package handler

import (
	"errors"
	"net/http"
	"os"
	"strconv"

	apierrors "github.com/athena/pkg/errors"
	"github.com/athena/pkg/jwt"
	"github.com/athena/pkg/rabbitmq"
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
	otpService    *service.OTPService
	rabbitClient  *rabbitmq.Client
	db            *gorm.DB
}

func NewAuthHandler(
	adminUserRepo *repository.AdminUserRepository,
	jwtUtil *jwt.JWTUtil,
	authService *service.AuthService,
	otpService *service.OTPService,
	rabbitClient *rabbitmq.Client,
	db *gorm.DB,
) *AuthHandler {
	return &AuthHandler{
		adminUserRepo: adminUserRepo,
		jwtUtil:       jwtUtil,
		authService:   authService,
		otpService:    otpService,
		rabbitClient:  rabbitClient,
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

// RequestOTP issues a single-use sign-in code to a registered customer's mobile.
//
// The response is identical whether or not the number is registered — a
// distinguishable response would let anyone enumerate the customer base.
func (h *AuthHandler) RequestOTP(c *gin.Context) {
	phone := c.Query("phone")
	if phone == "" {
		phone = c.PostForm("phone")
	}
	if phone == "" {
		apierrors.BadRequest(c, "phone is required")
		return
	}

	const genericAck = "If that number is registered, a one-time code has been sent."

	var cidVal int64
	if err := h.db.Raw(
		"SELECT customer_id FROM customers WHERE mobile_number = ?", phone,
	).Scan(&cidVal).Error; err != nil || cidVal == 0 {
		log.Warn().Str("phone", phone).Msg("OTP requested for unknown number")
		c.JSON(http.StatusOK, genericAck)
		return
	}

	code, err := h.otpService.Issue(phone)
	if err != nil {
		if errors.Is(err, service.ErrOTPThrottled) {
			apierrors.Respond(c, http.StatusTooManyRequests, "too_many_requests",
				"Too many code requests. Try again shortly.")
			return
		}
		apierrors.InternalError(c, "failed to issue one-time code")
		return
	}

	if h.rabbitClient != nil {
		event := map[string]interface{}{
			"type":    "CUSTOMER_OTP",
			"channel": "SMS",
			"phone":   phone,
			"message": "Your NemoScore sign-in code is " + code + ". It expires in 5 minutes.",
		}
		if pubErr := h.rabbitClient.Publish(rabbitmq.NotificationKey, event); pubErr != nil {
			// Delivery is best-effort; the code is already stored and still valid.
			log.Error().Err(pubErr).Msg("failed to publish OTP notification")
		}
	}

	// Dev escape hatch: without SMS configured there is no other way to obtain the
	// code. Never enable outside local development — it puts codes in the logs.
	if os.Getenv("OTP_DEV_LOG") == "true" {
		log.Warn().Str("phone", phone).Str("otp", code).Msg("OTP_DEV_LOG enabled — code logged in clear")
	}

	log.Info().Int64("customerId", cidVal).Msg("OTP issued")
	c.JSON(http.StatusOK, genericAck)
}

// VerifyOTP exchanges a valid single-use code for a customer JWT.
func (h *AuthHandler) VerifyOTP(c *gin.Context) {
	phone := c.Query("phone")
	if phone == "" {
		phone = c.PostForm("phone")
	}
	otp := c.Query("otp")
	if otp == "" {
		otp = c.PostForm("otp")
	}
	if phone == "" || otp == "" {
		apierrors.BadRequest(c, "phone and otp are required")
		return
	}

	if err := h.otpService.Verify(phone, otp); err != nil {
		if errors.Is(err, service.ErrOTPInvalid) {
			log.Warn().Str("phone", phone).Msg("OTP verification failed")
			apierrors.Unauthorized(c, "Invalid or expired code")
			return
		}
		apierrors.InternalError(c, "failed to verify one-time code")
		return
	}

	// The code is only ever issued to a registered number, but re-check rather
	// than mint a token whose customerId claim we could not resolve.
	var cidVal int64
	if err := h.db.Raw(
		"SELECT customer_id FROM customers WHERE mobile_number = ?", phone,
	).Scan(&cidVal).Error; err != nil || cidVal == 0 {
		apierrors.Unauthorized(c, "Invalid or expired code")
		return
	}

	subject := strconv.FormatInt(cidVal, 10)
	token, err := h.jwtUtil.GenerateToken(subject, []string{"CUSTOMER"}, &cidVal)
	if err != nil {
		apierrors.InternalError(c, "failed to generate token")
		return
	}

	log.Info().Int64("customerId", cidVal).Msg("Customer OTP login")
	c.JSON(http.StatusOK, dto.AuthResponse{
		Token:      token,
		Username:   subject,
		Roles:      []string{"CUSTOMER"},
		CustomerID: &cidVal,
	})
}

// DemoToken mints a customer JWT from a customerId alone, with no authentication.
// It is a development affordance and is disabled unless ALLOW_DEMO_TOKENS=true;
// with it enabled, anyone who can reach this route can impersonate any customer.
func (h *AuthHandler) DemoToken(c *gin.Context) {
	if os.Getenv("ALLOW_DEMO_TOKENS") != "true" {
		apierrors.NotFound(c, "not found")
		return
	}

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

	// 2. Not an admin. This endpoint used to fall through to a customer lookup by
	// phone or email and issue a CUSTOMER token on a match alone — no credential
	// was ever checked, so any known mobile number was a full account login.
	// Customers hold no password (the customers table has no credential column);
	// they sign in with a one-time code via /api/auth/customer/request-otp.
	log.Warn().Str("username", req.Username).Msg("Portal login failed")
	apierrors.Unauthorized(c, "Invalid username or password")
}
