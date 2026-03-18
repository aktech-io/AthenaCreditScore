package handler

import (
	"net/http"
	"time"

	apierrors "github.com/athena/pkg/errors"
	"github.com/athena/user-service/internal/dto"
	"github.com/athena/user-service/internal/model"
	"github.com/athena/user-service/internal/repository"
	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
)

type InvitationHandler struct {
	invitationRepo *repository.InvitationRepository
	userRepo       *repository.UserRepository
}

func NewInvitationHandler(
	invitationRepo *repository.InvitationRepository,
	userRepo *repository.UserRepository,
) *InvitationHandler {
	return &InvitationHandler{
		invitationRepo: invitationRepo,
		userRepo:       userRepo,
	}
}

func (h *InvitationHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("/validate-token", h.ValidateToken)
	rg.POST("/complete-registration", h.CompleteRegistration)
}

func (h *InvitationHandler) ValidateToken(c *gin.Context) {
	token := c.Query("token")
	if token == "" {
		apierrors.BadRequest(c, "token is required")
		return
	}

	invitation, err := h.invitationRepo.FindByToken(token)
	if err != nil {
		apierrors.NotFound(c, "Invalid token")
		return
	}

	if invitation.Used {
		apierrors.BadRequest(c, "Token already used")
		return
	}
	if invitation.ExpiryDate.Before(time.Now()) {
		apierrors.BadRequest(c, "Token expired")
		return
	}

	c.JSON(http.StatusOK, gin.H{"email": invitation.Email})
}

func (h *InvitationHandler) CompleteRegistration(c *gin.Context) {
	var req dto.CompleteRegistrationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierrors.BadRequest(c, err.Error())
		return
	}

	invitation, err := h.invitationRepo.FindByToken(req.Token)
	if err != nil {
		apierrors.NotFound(c, "Invalid token")
		return
	}

	if invitation.Used || invitation.ExpiryDate.Before(time.Now()) {
		apierrors.BadRequest(c, "Token invalid or expired")
		return
	}

	hashed, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		apierrors.InternalError(c, "failed to hash password")
		return
	}

	// Copy roles and groups from invitation
	roles := make([]model.Role, len(invitation.Roles))
	copy(roles, invitation.Roles)
	groups := make([]model.Group, len(invitation.Groups))
	copy(groups, invitation.Groups)

	user := model.User{
		Username:  invitation.Email,
		Email:     invitation.Email,
		FirstName: req.FirstName,
		LastName:  req.LastName,
		Password:  string(hashed),
		Status:    "ACTIVE",
		Roles:     roles,
		Groups:    groups,
	}

	if err := h.userRepo.Create(&user); err != nil {
		apierrors.InternalError(c, "failed to create user")
		return
	}

	invitation.Used = true
	if err := h.invitationRepo.Save(invitation); err != nil {
		apierrors.InternalError(c, "failed to update invitation")
		return
	}

	c.JSON(http.StatusOK, "Registration completed successfully")
}
