package handler

import (
	"net/http"

	apierrors "github.com/athena/pkg/errors"
	"github.com/athena/user-service/internal/model"
	"github.com/athena/user-service/internal/service"
	"github.com/gin-gonic/gin"
)

type PasswordPolicyHandler struct {
	policyService *service.PasswordPolicyService
}

func NewPasswordPolicyHandler(policyService *service.PasswordPolicyService) *PasswordPolicyHandler {
	return &PasswordPolicyHandler{policyService: policyService}
}

func (h *PasswordPolicyHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("", h.GetPolicy)
	rg.PUT("", h.UpdatePolicy)
}

func (h *PasswordPolicyHandler) GetPolicy(c *gin.Context) {
	policy, err := h.policyService.GetCurrentPolicy()
	if err != nil {
		apierrors.NotFound(c, err.Error())
		return
	}
	c.JSON(http.StatusOK, policy)
}

func (h *PasswordPolicyHandler) UpdatePolicy(c *gin.Context) {
	var policy model.PasswordPolicy
	if err := c.ShouldBindJSON(&policy); err != nil {
		apierrors.BadRequest(c, err.Error())
		return
	}
	updated, err := h.policyService.UpdatePolicy(&policy)
	if err != nil {
		apierrors.InternalError(c, "failed to update policy")
		return
	}
	c.JSON(http.StatusOK, updated)
}
