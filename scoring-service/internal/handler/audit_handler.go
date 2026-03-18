package handler

import (
	"fmt"
	"net/http"
	"strconv"

	"github.com/athena/pkg/middleware"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type AuditHandler struct {
	db *gorm.DB
}

func NewAuditHandler(db *gorm.DB) *AuditHandler {
	return &AuditHandler{db: db}
}

func (h *AuditHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("",
		middleware.RequireRoles("ADMIN", "ANALYST", "CREDIT_RISK"),
		h.GetAuditLog)
}

func (h *AuditHandler) GetAuditLog(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "0"))
	size, _ := strconv.Atoi(c.DefaultQuery("size", "50"))
	action := c.Query("action")
	outcome := c.Query("outcome")

	offset := page * size

	sql := `SELECT log_id as id,
			TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as ts,
			COALESCE(actor_id, 'SYSTEM') as partner,
			COALESCE(CAST((payload->>'customerId') AS VARCHAR),
			         CAST((payload->>'customer_id') AS VARCHAR), '') as customer,
			COALESCE(action, '') as action,
			COALESCE(resource, 'OK') as outcome,
			COALESCE(CAST(ip_address AS VARCHAR), '') as ip
			FROM audit_log WHERE 1=1`

	params := make([]interface{}, 0)
	if action != "" {
		sql += " AND action = ?"
		params = append(params, action)
	}
	if outcome != "" {
		sql += " AND resource = ?"
		params = append(params, outcome)
	}
	sql += fmt.Sprintf(" ORDER BY created_at DESC LIMIT %d OFFSET %d", size, offset)

	var results []map[string]interface{}
	h.db.Raw(sql, params...).Scan(&results)
	if results == nil {
		results = []map[string]interface{}{}
	}

	c.JSON(http.StatusOK, results)
}
