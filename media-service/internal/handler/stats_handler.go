package handler

import (
	"net/http"
	"strconv"

	"github.com/athena/media-service/internal/service"
	"github.com/gin-gonic/gin"
)

// StatsHandler handles stats REST endpoints.
type StatsHandler struct {
	svc *service.MediaService
}

// NewStatsHandler creates a new StatsHandler.
func NewStatsHandler(svc *service.MediaService) *StatsHandler {
	return &StatsHandler{svc: svc}
}

// RegisterRoutes registers stats endpoints on the given router group.
func (h *StatsHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("", h.GetStats)
	rg.GET("/all", h.GetAllMedia)
}

// GetStats handles GET /api/v1/media/stats
func (h *StatsHandler) GetStats(c *gin.Context) {
	stats, err := h.svc.GetStats()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, stats)
}

// GetAllMedia handles GET /api/v1/media/stats/all (paginated)
func (h *StatsHandler) GetAllMedia(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "0"))
	size, _ := strconv.Atoi(c.DefaultQuery("size", "20"))

	if page < 0 {
		page = 0
	}
	if size <= 0 {
		size = 20
	}

	result, err := h.svc.GetAllMedia(page, size)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}
