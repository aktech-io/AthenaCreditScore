package handler

import (
	"net/http"

	apierrors "github.com/athena/pkg/errors"
	"github.com/athena/user-service/internal/model"
	"github.com/athena/user-service/internal/repository"
	"github.com/gin-gonic/gin"
)

type RoleHandler struct {
	roleRepo *repository.RoleRepository
}

func NewRoleHandler(roleRepo *repository.RoleRepository) *RoleHandler {
	return &RoleHandler{roleRepo: roleRepo}
}

func (h *RoleHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("", h.GetAll)
	rg.POST("", h.Create)
}

func (h *RoleHandler) GetAll(c *gin.Context) {
	roles, err := h.roleRepo.FindAll()
	if err != nil {
		apierrors.InternalError(c, "failed to list roles")
		return
	}
	c.JSON(http.StatusOK, roles)
}

func (h *RoleHandler) Create(c *gin.Context) {
	var role model.Role
	if err := c.ShouldBindJSON(&role); err != nil {
		apierrors.BadRequest(c, err.Error())
		return
	}
	if err := h.roleRepo.Create(&role); err != nil {
		apierrors.InternalError(c, "failed to create role")
		return
	}
	c.JSON(http.StatusOK, role)
}
