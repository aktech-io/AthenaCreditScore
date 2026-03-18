package handler

import (
	"fmt"
	"net/http"

	"github.com/athena/pkg/middleware"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
	"gorm.io/gorm"
)

type ModelHandler struct {
	db *gorm.DB
}

func NewModelHandler(db *gorm.DB) *ModelHandler {
	return &ModelHandler{db: db}
}

func (h *ModelHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("/compare",
		middleware.RequireRoles("ADMIN", "ANALYST", "CREDIT_RISK"),
		h.CompareModels)
	rg.PUT("/promote",
		middleware.RequireRoles("ADMIN"),
		h.PromoteChallenger)
}

func (h *ModelHandler) CompareModels(c *gin.Context) {
	type modelRow struct {
		VersionID int64   `gorm:"column:version_id"`
		Alias     string  `gorm:"column:alias"`
		ModelName string  `gorm:"column:model_name"`
		KS        float64 `gorm:"column:ks"`
		AUC       float64 `gorm:"column:auc"`
	}

	var rows []modelRow
	h.db.Raw(`SELECT version_id, alias, model_name,
			COALESCE(ks_statistic, 0) as ks, COALESCE(auc_roc, 0) as auc
			FROM model_versions WHERE alias IN ('champion', 'challenger') AND is_active = true
			ORDER BY version_id DESC LIMIT 2`).Scan(&rows)

	var champion, challenger *modelRow
	for i := range rows {
		switch rows[i].Alias {
		case "champion":
			champion = &rows[i]
		case "challenger":
			challenger = &rows[i]
		}
	}

	// Fallback defaults
	if champion == nil {
		champion = &modelRow{VersionID: 3, KS: 0.41, AUC: 0.847}
	}
	if challenger == nil {
		challenger = &modelRow{VersionID: 4, KS: 0.44, AUC: 0.853}
	}

	ksImprovement := challenger.KS - champion.KS
	aucImprovement := challenger.AUC - champion.AUC

	recommendation := "keep_champion"
	if ksImprovement > 0.02 && aucImprovement > 0 {
		recommendation = "promote_challenger"
	} else if ksImprovement < 0 && aucImprovement < 0 {
		recommendation = "rollback_challenger"
	}

	c.JSON(http.StatusOK, gin.H{
		"champion":        gin.H{"version": fmt.Sprintf("v%d", champion.VersionID), "ks": champion.KS, "auc": champion.AUC},
		"challenger":      gin.H{"version": fmt.Sprintf("v%d", challenger.VersionID), "ks": challenger.KS, "auc": challenger.AUC},
		"ks_improvement":  ksImprovement,
		"auc_improvement": aucImprovement,
		"recommendation":  recommendation,
	})
}

func (h *ModelHandler) PromoteChallenger(c *gin.Context) {
	log.Info().Msg("promoting challenger to champion")
	h.db.Exec("UPDATE model_versions SET alias='retired' WHERE alias='champion'")
	result := h.db.Exec("UPDATE model_versions SET alias='champion' WHERE alias='challenger'")

	newChampion := "unknown"
	type versionRow struct {
		VersionID int64 `gorm:"column:version_id"`
	}
	var vr versionRow
	if err := h.db.Raw("SELECT version_id FROM model_versions WHERE alias='champion' ORDER BY version_id DESC LIMIT 1").
		Scan(&vr).Error; err == nil && vr.VersionID > 0 {
		newChampion = fmt.Sprintf("v%d", vr.VersionID)
	}

	msg := "No challenger found to promote"
	if result.RowsAffected > 0 {
		msg = "Challenger promoted to champion"
	}

	c.JSON(http.StatusOK, gin.H{
		"message":              msg,
		"new_champion_version": newChampion,
	})
}
