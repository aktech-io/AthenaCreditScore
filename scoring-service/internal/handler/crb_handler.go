package handler

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/athena/scoring-service/internal/client"
	"github.com/athena/scoring-service/internal/routing"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
)

type CrbHandler struct {
	crbClient *client.CrbClient
	router    *routing.ChampionChallengerRouter
}

func NewCrbHandler(crbClient *client.CrbClient, router *routing.ChampionChallengerRouter) *CrbHandler {
	return &CrbHandler{crbClient: crbClient, router: router}
}

func (h *CrbHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.POST("/fetch/:customerId", h.FetchCrbReport)
	rg.GET("/routing-config", h.GetRoutingConfig)
	rg.PUT("/routing-config", h.UpdateRoutingConfig)
}

func (h *CrbHandler) FetchCrbReport(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	nationalID := c.Query("nationalId")
	crb := c.DefaultQuery("crb", "transunion")

	target := h.router.Route()
	log.Info().Int64("customer", customerID).Str("crb", crb).Str("target", string(target)).Msg("CRB fetch")

	var report map[string]interface{}
	if strings.EqualFold(crb, "metropol") {
		report, err = h.crbClient.FetchMetropolReport(nationalID)
	} else {
		report, err = h.crbClient.FetchTransUnionReport(nationalID)
	}

	crbFetched := err == nil && report != nil
	if err != nil {
		log.Warn().Err(err).Msg("CRB fetch failed")
	}

	c.JSON(http.StatusOK, gin.H{
		"customer_id":  customerID,
		"model_target": string(target),
		"crb_fetched":  crbFetched,
		"message":      "CRB report fetched. Scoring request queued.",
	})
}

func (h *CrbHandler) GetRoutingConfig(c *gin.Context) {
	pct := h.router.GetChallengerPct()
	c.JSON(http.StatusOK, gin.H{
		"challenger_traffic_pct": pct,
		"champion_traffic_pct":   1.0 - pct,
	})
}

func (h *CrbHandler) UpdateRoutingConfig(c *gin.Context) {
	pctStr := c.Query("challengerPct")
	pct, err := strconv.ParseFloat(pctStr, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid challengerPct"})
		return
	}

	h.router.UpdateChallengerPct(pct)
	c.JSON(http.StatusOK, gin.H{
		"updated_challenger_pct": h.router.GetChallengerPct(),
		"message":               "Routing config updated",
	})
}
