package handler

import (
	"net/http"
	"strconv"
	"time"

	apierrors "github.com/athena/pkg/errors"
	"github.com/athena/pkg/rabbitmq"
	"github.com/athena/user-service/internal/dto"
	"github.com/athena/user-service/internal/model"
	"github.com/athena/user-service/internal/repository"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

type UserManagementHandler struct {
	userRepo       *repository.UserRepository
	groupRepo      *repository.GroupRepository
	roleRepo       *repository.RoleRepository
	invitationRepo *repository.InvitationRepository
	rabbitClient   *rabbitmq.Client
}

func NewUserManagementHandler(
	userRepo *repository.UserRepository,
	groupRepo *repository.GroupRepository,
	roleRepo *repository.RoleRepository,
	invitationRepo *repository.InvitationRepository,
	rabbitClient *rabbitmq.Client,
) *UserManagementHandler {
	return &UserManagementHandler{
		userRepo:       userRepo,
		groupRepo:      groupRepo,
		roleRepo:       roleRepo,
		invitationRepo: invitationRepo,
		rabbitClient:   rabbitClient,
	}
}

func (h *UserManagementHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("", h.GetAllUsers)
	rg.POST("", h.CreateUser)
	rg.PUT("/:id", h.UpdateUser)
	rg.DELETE("/:id", h.DeleteUser)
	rg.POST("/:userId/groups/:groupId", h.AssignToGroup)
	rg.POST("/:userId/roles/:roleId", h.AssignRole)
	rg.POST("/invite", h.InviteUser)
}

func (h *UserManagementHandler) GetAllUsers(c *gin.Context) {
	users, err := h.userRepo.FindAll()
	if err != nil {
		apierrors.InternalError(c, "failed to list users")
		return
	}
	c.JSON(http.StatusOK, users)
}

func (h *UserManagementHandler) CreateUser(c *gin.Context) {
	var req dto.CreateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierrors.BadRequest(c, err.Error())
		return
	}

	if h.userRepo.ExistsByUsername(req.Username) {
		apierrors.Conflict(c, "User already exists: "+req.Username)
		return
	}

	hashed, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		apierrors.InternalError(c, "failed to hash password")
		return
	}

	user := model.User{
		Username:  req.Username,
		Email:     req.Email,
		Password:  string(hashed),
		FirstName: req.FirstName,
		LastName:  req.LastName,
		Status:    "ACTIVE",
	}

	// Resolve roles by name
	if req.Roles != nil {
		for _, name := range req.Roles {
			if role, err := h.roleRepo.FindByName(name); err == nil {
				user.Roles = append(user.Roles, *role)
			}
		}
	}
	// Resolve groups by name
	if req.Groups != nil {
		for _, name := range req.Groups {
			if group, err := h.groupRepo.FindByName(name); err == nil {
				user.Groups = append(user.Groups, *group)
			}
		}
	}

	if err := h.userRepo.Create(&user); err != nil {
		apierrors.InternalError(c, "failed to create user")
		return
	}

	// Reload to include associations
	created, _ := h.userRepo.FindByID(user.ID)
	if created != nil {
		c.JSON(http.StatusOK, created)
	} else {
		c.JSON(http.StatusOK, user)
	}
}

func (h *UserManagementHandler) UpdateUser(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid user ID")
		return
	}

	user, err := h.userRepo.FindByID(id)
	if err != nil {
		apierrors.NotFound(c, "User not found: "+strconv.FormatInt(id, 10))
		return
	}

	var req dto.UpdateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierrors.BadRequest(c, err.Error())
		return
	}

	if req.Password != nil && *req.Password != "" {
		hashed, err := bcrypt.GenerateFromPassword([]byte(*req.Password), bcrypt.DefaultCost)
		if err != nil {
			apierrors.InternalError(c, "failed to hash password")
			return
		}
		user.Password = string(hashed)
	}
	if req.FirstName != nil {
		user.FirstName = *req.FirstName
	}
	if req.LastName != nil {
		user.LastName = *req.LastName
	}
	if req.Email != nil {
		user.Email = *req.Email
	}

	if err := h.userRepo.Save(user); err != nil {
		apierrors.InternalError(c, "failed to update user")
		return
	}

	// Replace roles if provided
	if req.Roles != nil {
		var roles []model.Role
		for _, name := range req.Roles {
			role, err := h.roleRepo.FindByName(name)
			if err != nil {
				apierrors.NotFound(c, "Role not found: "+name)
				return
			}
			roles = append(roles, *role)
		}
		if err := h.userRepo.ReplaceRoles(user, roles); err != nil {
			apierrors.InternalError(c, "failed to update roles")
			return
		}
	}

	// Replace groups if provided
	if req.Groups != nil {
		var groups []model.Group
		for _, name := range req.Groups {
			group, err := h.groupRepo.FindByName(name)
			if err != nil {
				apierrors.NotFound(c, "Group not found: "+name)
				return
			}
			groups = append(groups, *group)
		}
		if err := h.userRepo.ReplaceGroups(user, groups); err != nil {
			apierrors.InternalError(c, "failed to update groups")
			return
		}
	}

	// Reload
	updated, _ := h.userRepo.FindByID(id)
	if updated != nil {
		c.JSON(http.StatusOK, updated)
	} else {
		c.JSON(http.StatusOK, user)
	}
}

func (h *UserManagementHandler) DeleteUser(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid user ID")
		return
	}

	if !h.userRepo.ExistsByID(id) {
		apierrors.NotFound(c, "User not found: "+strconv.FormatInt(id, 10))
		return
	}

	if err := h.userRepo.Delete(id); err != nil {
		apierrors.InternalError(c, "failed to delete user")
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *UserManagementHandler) AssignToGroup(c *gin.Context) {
	userID, err := strconv.ParseInt(c.Param("userId"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid user ID")
		return
	}
	groupID, err := strconv.ParseInt(c.Param("groupId"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid group ID")
		return
	}

	user, err := h.userRepo.FindByID(userID)
	if err != nil {
		apierrors.NotFound(c, "User not found")
		return
	}
	group, err := h.groupRepo.FindByID(groupID)
	if err != nil {
		apierrors.NotFound(c, "Group not found")
		return
	}

	if err := h.userRepo.AppendGroup(user, group); err != nil {
		apierrors.InternalError(c, "failed to assign group")
		return
	}

	updated, _ := h.userRepo.FindByID(userID)
	if updated != nil {
		c.JSON(http.StatusOK, updated)
	} else {
		c.JSON(http.StatusOK, user)
	}
}

func (h *UserManagementHandler) AssignRole(c *gin.Context) {
	userID, err := strconv.ParseInt(c.Param("userId"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid user ID")
		return
	}
	roleID, err := strconv.ParseInt(c.Param("roleId"), 10, 64)
	if err != nil {
		apierrors.BadRequest(c, "invalid role ID")
		return
	}

	user, err := h.userRepo.FindByID(userID)
	if err != nil {
		apierrors.NotFound(c, "User not found")
		return
	}
	role, err := h.roleRepo.FindByID(roleID)
	if err != nil {
		apierrors.NotFound(c, "Role not found")
		return
	}

	if err := h.userRepo.AppendRole(user, role); err != nil {
		apierrors.InternalError(c, "failed to assign role")
		return
	}

	updated, _ := h.userRepo.FindByID(userID)
	if updated != nil {
		c.JSON(http.StatusOK, updated)
	} else {
		c.JSON(http.StatusOK, user)
	}
}

func (h *UserManagementHandler) InviteUser(c *gin.Context) {
	var req dto.CreateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierrors.BadRequest(c, err.Error())
		return
	}

	if h.userRepo.ExistsByUsername(req.Email) {
		apierrors.Conflict(c, "User with this email already exists")
		return
	}

	token := uuid.New().String()

	invitation := model.Invitation{
		Token:      token,
		Email:      req.Email,
		ExpiryDate: time.Now().Add(24 * time.Hour),
		Used:       false,
	}

	// Resolve roles
	if req.Roles != nil {
		for _, name := range req.Roles {
			role, err := h.roleRepo.FindByName(name)
			if err != nil {
				apierrors.NotFound(c, "Role not found: "+name)
				return
			}
			invitation.Roles = append(invitation.Roles, *role)
		}
	}

	// Resolve groups
	if req.Groups != nil {
		for _, name := range req.Groups {
			group, err := h.groupRepo.FindByName(name)
			if err != nil {
				apierrors.NotFound(c, "Group not found: "+name)
				return
			}
			invitation.Groups = append(invitation.Groups, *group)
		}
	}

	if err := h.invitationRepo.Create(&invitation); err != nil {
		apierrors.InternalError(c, "failed to create invitation")
		return
	}

	// Publish USER_INVITATION event to RabbitMQ
	if h.rabbitClient != nil {
		event := map[string]interface{}{
			"type":  "USER_INVITATION",
			"email": req.Email,
			"token": token,
		}
		if err := h.rabbitClient.Publish(rabbitmq.NotificationKey, event); err != nil {
			// Log but don't fail the request
			c.Error(err)
		}
	}

	c.JSON(http.StatusOK, "Invitation sent to "+req.Email)
}
