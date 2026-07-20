package handler

import (
	"net/http"
	"time"

	apierrors "github.com/athena/pkg/errors"
	"github.com/athena/user-service/internal/model"
	"github.com/athena/user-service/internal/repository"
	"github.com/athena/user-service/internal/service"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
)

// TotpHandler manages admin TOTP enrollment (NemoScore Phase 5). Routes sit
// behind JWT auth; the acting admin is taken from the token's username claim,
// so an admin can only ever enroll/disable their own second factor. Recovery
// for a lost device is an operational action (clear totp_secret in the DB).
type TotpHandler struct {
	adminUserRepo *repository.AdminUserRepository
}

func NewTotpHandler(adminUserRepo *repository.AdminUserRepository) *TotpHandler {
	return &TotpHandler{adminUserRepo: adminUserRepo}
}

func (h *TotpHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("/status", h.Status)
	rg.POST("/setup", h.Setup)
	rg.POST("/enable", h.Enable)
	rg.POST("/disable", h.Disable)
}

// currentAdmin resolves the acting admin from the JWT username claim,
// writing the error response and returning nil when there isn't one.
func (h *TotpHandler) currentAdmin(c *gin.Context) *model.AdminUser {
	username, _ := c.Get("username")
	name, _ := username.(string)
	if name == "" {
		apierrors.Unauthorized(c, "unauthenticated")
		return nil
	}
	admin, err := h.adminUserRepo.FindByUsername(name)
	if err != nil {
		apierrors.Unauthorized(c, "not an admin account")
		return nil
	}
	return admin
}

// Status reports whether TOTP is enrolled for the acting admin.
func (h *TotpHandler) Status(c *gin.Context) {
	admin := h.currentAdmin(c)
	if admin == nil {
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"enabled":      admin.TotpSecret != "",
		"setupPending": admin.TotpPendingSecret != "",
	})
}

// Setup generates a fresh secret and returns the otpauth:// URI for the
// authenticator app. The secret stays pending until Enable proves possession.
func (h *TotpHandler) Setup(c *gin.Context) {
	admin := h.currentAdmin(c)
	if admin == nil {
		return
	}

	secret, err := service.GenerateTOTPSecret()
	if err != nil {
		apierrors.InternalError(c, "failed to generate TOTP secret")
		return
	}
	if err := h.adminUserRepo.UpdateTotpSecrets(admin.ID, admin.TotpSecret, secret); err != nil {
		apierrors.InternalError(c, "failed to store pending TOTP secret")
		return
	}

	log.Info().Str("username", admin.Username).Msg("TOTP enrollment started")
	c.JSON(http.StatusOK, gin.H{
		"secret":          secret,
		"provisioningUri": service.TOTPProvisioningURI(admin.Username, secret),
	})
}

type totpCodeRequest struct {
	Code string `json:"code" binding:"required"`
}

// Enable confirms the pending secret with a live code and turns enforcement on.
func (h *TotpHandler) Enable(c *gin.Context) {
	admin := h.currentAdmin(c)
	if admin == nil {
		return
	}

	var req totpCodeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierrors.BadRequest(c, "code is required")
		return
	}
	if admin.TotpPendingSecret == "" {
		apierrors.BadRequest(c, "no TOTP setup in progress — call /totp/setup first")
		return
	}
	if !service.ValidateTOTP(admin.TotpPendingSecret, req.Code, time.Now()) {
		apierrors.Unauthorized(c, "Invalid TOTP code")
		return
	}
	if err := h.adminUserRepo.UpdateTotpSecrets(admin.ID, admin.TotpPendingSecret, ""); err != nil {
		apierrors.InternalError(c, "failed to enable TOTP")
		return
	}

	log.Info().Str("username", admin.Username).Msg("TOTP enabled")
	c.JSON(http.StatusOK, gin.H{"enabled": true})
}

// Disable turns enforcement off; it requires a valid current code so a
// hijacked session cannot silently strip the second factor.
func (h *TotpHandler) Disable(c *gin.Context) {
	admin := h.currentAdmin(c)
	if admin == nil {
		return
	}

	var req totpCodeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierrors.BadRequest(c, "code is required")
		return
	}
	if admin.TotpSecret == "" {
		apierrors.BadRequest(c, "TOTP is not enabled")
		return
	}
	if !service.ValidateTOTP(admin.TotpSecret, req.Code, time.Now()) {
		apierrors.Unauthorized(c, "Invalid TOTP code")
		return
	}
	if err := h.adminUserRepo.UpdateTotpSecrets(admin.ID, "", ""); err != nil {
		apierrors.InternalError(c, "failed to disable TOTP")
		return
	}

	log.Info().Str("username", admin.Username).Msg("TOTP disabled")
	c.JSON(http.StatusOK, gin.H{"enabled": false})
}
