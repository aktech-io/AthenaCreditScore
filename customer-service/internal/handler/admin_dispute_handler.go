package handler

import (
	"net/http"

	"github.com/athena/pkg/errors"
	"github.com/athena/pkg/middleware"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// AdminDisputeHandler handles admin-level dispute endpoints.
type AdminDisputeHandler struct {
	db *gorm.DB
}

func NewAdminDisputeHandler(db *gorm.DB) *AdminDisputeHandler {
	return &AdminDisputeHandler{db: db}
}

// RegisterRoutes registers all /api/v1/disputes routes.
func (h *AdminDisputeHandler) RegisterRoutes(rg *gin.RouterGroup) {
	disputes := rg.Group("/disputes")
	{
		disputes.GET("", middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CREDIT_RISK"), h.ListDisputes)
		disputes.PUT("/:id", middleware.RequireRoles("ADMIN", "ANALYST"), h.UpdateDispute)
	}
}

// ListDisputes returns all disputes across all customers, optionally filtered by status.
func (h *AdminDisputeHandler) ListDisputes(c *gin.Context) {
	status := c.Query("status")

	sql := `SELECT d.dispute_id as id, d.customer_id as "customerId",
		c.first_name || ' ' || c.last_name as customer,
		'Credit Report' as field, d.reason as desc,
		d.status, CAST(d.created_at AS DATE) as filed
		FROM disputes d
		JOIN customers c ON d.customer_id = c.customer_id `

	var results []map[string]interface{}
	if status != "" && status != "ALL" {
		sql += "WHERE d.status = ? ORDER BY d.created_at DESC"
		h.db.Raw(sql, status).Scan(&results)
	} else {
		sql += "ORDER BY d.created_at DESC"
		h.db.Raw(sql).Scan(&results)
	}

	c.JSON(http.StatusOK, results)
}

// UpdateDispute updates a dispute's status.
func (h *AdminDisputeHandler) UpdateDispute(c *gin.Context) {
	id := c.Param("id")

	var body map[string]string
	if err := c.ShouldBindJSON(&body); err != nil {
		errors.BadRequest(c, "Invalid request body")
		return
	}

	status := body["status"]
	if status != "" {
		h.db.Exec("UPDATE disputes SET status = ? WHERE dispute_id = ?", status, id)
	}

	c.Status(http.StatusOK)
}
