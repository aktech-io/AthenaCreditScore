package handler

import (
	"math"
	"net/http"

	"github.com/athena/pkg/middleware"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type DashboardHandler struct {
	db *gorm.DB
}

func NewDashboardHandler(db *gorm.DB) *DashboardHandler {
	return &DashboardHandler{db: db}
}

func (h *DashboardHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("/stats",
		middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CREDIT_RISK"),
		h.GetDashboardStats)
}

func (h *DashboardHandler) GetDashboardStats(c *gin.Context) {
	stats := make(map[string]interface{})

	var totalScored int64
	h.db.Raw("SELECT COUNT(*) FROM credit_score_events").Scan(&totalScored)
	stats["totalScored"] = totalScored

	var avgScore *float64
	h.db.Raw("SELECT AVG(final_score) FROM credit_score_events").Scan(&avgScore)
	if avgScore != nil {
		stats["avgScore"] = int64(math.Round(*avgScore))
	} else {
		stats["avgScore"] = 0
	}

	var approvalRate *float64
	h.db.Raw("SELECT (COUNT(*) FILTER (WHERE final_score >= 500)::float / NULLIF(COUNT(*), 0)) FROM credit_score_events").Scan(&approvalRate)
	if approvalRate != nil {
		stats["approvalRate"] = *approvalRate
	} else {
		stats["approvalRate"] = 0.0
	}

	var defaultRate *float64
	h.db.Raw("SELECT (COUNT(*) FILTER (WHERE status = 'DEFAULTED')::float / NULLIF(COUNT(*), 0)) FROM loans").Scan(&defaultRate)
	if defaultRate != nil {
		stats["defaultRate"] = *defaultRate
	} else {
		stats["defaultRate"] = 0.0
	}

	var openDisputes int64
	h.db.Raw("SELECT COUNT(*) FROM disputes WHERE status IN ('OPEN', 'UNDER_REVIEW')").Scan(&openDisputes)
	stats["openDisputes"] = openDisputes

	// Mocked values until MLflow integration is deeper
	stats["ksStatistic"] = 0.42
	stats["psiValue"] = 0.08
	stats["championVersion"] = "v1.2"
	stats["challengerVersion"] = "v1.3-xgb"
	stats["challengerPct"] = 0.20

	c.JSON(http.StatusOK, stats)
}
