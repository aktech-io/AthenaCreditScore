package handler

import (
	"net/http"
	"strconv"

	"github.com/athena/pkg/middleware"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type DisputeHandler struct {
	db *gorm.DB
}

func NewDisputeHandler(db *gorm.DB) *DisputeHandler {
	return &DisputeHandler{db: db}
}

func (h *DisputeHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("",
		middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CREDIT_RISK"),
		h.ListDisputes)
	rg.PUT("/:id",
		middleware.RequireRoles("ADMIN", "ANALYST"),
		h.UpdateDispute)
}

func (h *DisputeHandler) ListDisputes(c *gin.Context) {
	status := c.Query("status")

	var results []map[string]interface{}

	if status != "" && status != "ALL" {
		sql := `SELECT d.dispute_id as id, d.customer_id as "customerId",
				c.first_name || ' ' || c.last_name as customer,
				'Credit Report' as field, d.reason as desc,
				d.status, CAST(d.created_at AS DATE) as filed
				FROM disputes d
				JOIN customers c ON d.customer_id = c.customer_id
				WHERE d.status = ? ORDER BY d.created_at DESC`
		h.db.Raw(sql, status).Scan(&results)
	} else {
		sql := `SELECT d.dispute_id as id, d.customer_id as "customerId",
				c.first_name || ' ' || c.last_name as customer,
				'Credit Report' as field, d.reason as desc,
				d.status, CAST(d.created_at AS DATE) as filed
				FROM disputes d
				JOIN customers c ON d.customer_id = c.customer_id
				ORDER BY d.created_at DESC`
		h.db.Raw(sql).Scan(&results)
	}

	if results == nil {
		results = []map[string]interface{}{}
	}
	c.JSON(http.StatusOK, results)
}

func (h *DisputeHandler) UpdateDispute(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid dispute id"})
		return
	}

	var body map[string]string
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if status, ok := body["status"]; ok {
		h.db.Exec("UPDATE disputes SET status = ? WHERE dispute_id = ?", status, id)
	}

	c.Status(http.StatusOK)
}
