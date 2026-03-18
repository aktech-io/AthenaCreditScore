package handler

import (
	"net/http"
	"strconv"

	apierrors "github.com/athena/pkg/errors"
	"github.com/athena/user-service/internal/model"
	"github.com/athena/user-service/internal/repository"
	"github.com/gin-gonic/gin"
)

type GroupHandler struct {
	groupRepo *repository.GroupRepository
	roleRepo  *repository.RoleRepository
}

func NewGroupHandler(groupRepo *repository.GroupRepository, roleRepo *repository.RoleRepository) *GroupHandler {
	return &GroupHandler{groupRepo: groupRepo, roleRepo: roleRepo}
}

func (h *GroupHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("", h.GetAll)
	rg.POST("", h.Create)
	rg.POST("/:groupId/roles/:roleId", h.AssignRole)
	rg.DELETE("/:groupId/roles/:roleId", h.RemoveRole)
}

func (h *GroupHandler) GetAll(c *gin.Context) {
	groups, err := h.groupRepo.FindAll()
	if err != nil {
		apierrors.InternalError(c, "failed to list groups")
		return
	}
	c.JSON(http.StatusOK, groups)
}

func (h *GroupHandler) Create(c *gin.Context) {
	var group model.Group
	if err := c.ShouldBindJSON(&group); err != nil {
		apierrors.BadRequest(c, err.Error())
		return
	}
	if err := h.groupRepo.Create(&group); err != nil {
		apierrors.InternalError(c, "failed to create group")
		return
	}
	c.JSON(http.StatusOK, group)
}

func (h *GroupHandler) AssignRole(c *gin.Context) {
	groupID, err := strconv.ParseInt(c.Param("groupId"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid group ID")
		return
	}
	roleID, err := strconv.ParseInt(c.Param("roleId"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid role ID")
		return
	}

	group, err := h.groupRepo.FindByID(groupID)
	if err != nil {
		apierrors.NotFound(c, "Group not found")
		return
	}
	role, err := h.roleRepo.FindByID(roleID)
	if err != nil {
		apierrors.NotFound(c, "Role not found")
		return
	}

	if err := h.groupRepo.AppendRole(group, role); err != nil {
		apierrors.InternalError(c, "failed to assign role to group")
		return
	}

	// Reload to return updated group with roles
	updated, _ := h.groupRepo.FindByID(groupID)
	if updated != nil {
		c.JSON(http.StatusOK, updated)
	} else {
		c.JSON(http.StatusOK, group)
	}
}

func (h *GroupHandler) RemoveRole(c *gin.Context) {
	groupID, err := strconv.ParseInt(c.Param("groupId"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid group ID")
		return
	}
	roleID, err := strconv.ParseInt(c.Param("roleId"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid role ID")
		return
	}

	group, err := h.groupRepo.FindByID(groupID)
	if err != nil {
		apierrors.NotFound(c, "Group not found")
		return
	}
	role, err := h.roleRepo.FindByID(roleID)
	if err != nil {
		apierrors.NotFound(c, "Role not found")
		return
	}

	if err := h.groupRepo.RemoveRole(group, role); err != nil {
		apierrors.InternalError(c, "failed to remove role from group")
		return
	}

	updated, _ := h.groupRepo.FindByID(groupID)
	if updated != nil {
		c.JSON(http.StatusOK, updated)
	} else {
		c.JSON(http.StatusOK, group)
	}
}
