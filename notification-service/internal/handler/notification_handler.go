package handler

import (
	"net/http"
	"strings"

	"github.com/athena/notification-service/internal/model"
	"github.com/athena/notification-service/internal/service"
	apierr "github.com/athena/pkg/errors"
	"github.com/gin-gonic/gin"
)

// NotificationRequest mirrors the Java NotificationRequest DTO.
type NotificationRequest struct {
	ServiceName string                 `json:"serviceName"`
	Type        string                 `json:"type"` // EMAIL, SMS, PUSH
	Recipient   string                 `json:"recipient"`
	Subject     string                 `json:"subject"`
	Message     string                 `json:"message"`
	Metadata    map[string]interface{} `json:"metadata"`
}

type NotificationHandler struct {
	svc *service.NotificationService
}

func NewNotificationHandler(svc *service.NotificationService) *NotificationHandler {
	return &NotificationHandler{svc: svc}
}

func (h *NotificationHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("/config/:type", h.GetConfig)
	rg.POST("/config", h.UpdateConfig)
	rg.POST("/send", h.Send)
}

// GetConfig handles GET /api/v1/notifications/config/:type
func (h *NotificationHandler) GetConfig(c *gin.Context) {
	configType := strings.ToUpper(c.Param("type"))
	cfg, err := h.svc.GetConfig(configType)
	if err != nil {
		apierr.InternalError(c, err.Error())
		return
	}
	if cfg == nil {
		c.JSON(http.StatusOK, nil)
		return
	}
	c.JSON(http.StatusOK, cfg)
}

// UpdateConfig handles POST /api/v1/notifications/config
func (h *NotificationHandler) UpdateConfig(c *gin.Context) {
	var cfg model.NotificationConfig
	if err := c.ShouldBindJSON(&cfg); err != nil {
		apierr.BadRequest(c, "Invalid request body: "+err.Error())
		return
	}
	result, err := h.svc.UpdateConfig(&cfg)
	if err != nil {
		apierr.InternalError(c, err.Error())
		return
	}
	c.JSON(http.StatusOK, result)
}

// Send handles POST /api/v1/notifications/send
func (h *NotificationHandler) Send(c *gin.Context) {
	var req NotificationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		apierr.BadRequest(c, "Invalid request body: "+err.Error())
		return
	}

	notifType := strings.ToUpper(req.Type)

	switch notifType {
	case "EMAIL":
		serviceName := req.ServiceName
		if serviceName == "" {
			serviceName = "api"
		}
		if err := h.svc.SendEmail(serviceName, req.Recipient, req.Subject, req.Message); err != nil {
			// Still return 200 with message for consistency with Java behavior
			// (the log entry captures the failure)
			apierr.InternalError(c, "Failed to send email: "+err.Error())
			return
		}
		c.JSON(http.StatusOK, "Email queued")
	case "SMS":
		c.JSON(http.StatusOK, "SMS not yet implemented")
	default:
		apierr.BadRequest(c, "Unsupported notification type")
	}
}
