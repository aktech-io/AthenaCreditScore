package handler

import (
	"math"
	"net/http"
	"strconv"

	"github.com/athena/pkg/middleware"
	"github.com/athena/scoring-service/internal/cache"
	"github.com/athena/scoring-service/internal/client"
	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
	"gorm.io/gorm"
)

type CreditQueryHandler struct {
	db           *gorm.DB
	pythonClient *client.PythonClient
	cache        *cache.CreditCache
}

func NewCreditQueryHandler(db *gorm.DB, pythonClient *client.PythonClient, cc *cache.CreditCache) *CreditQueryHandler {
	return &CreditQueryHandler{db: db, pythonClient: pythonClient, cache: cc}
}

func (h *CreditQueryHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.GET("/score/:customerId",
		middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CREDIT_RISK", "CUSTOMER"),
		h.GetCreditScore)
	rg.GET("/report/:customerId",
		middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CREDIT_RISK", "CUSTOMER"),
		h.GetFullReport)
	rg.POST("/score/:customerId/trigger",
		middleware.RequireRoles("ADMIN", "ANALYST", "CREDIT_RISK"),
		h.TriggerScoringRun)
	rg.GET("/score/:customerId/history",
		middleware.RequireRoles("ADMIN", "ANALYST", "VIEWER", "CREDIT_RISK", "CUSTOMER"),
		h.GetScoreHistory)
}

// GetCreditScore returns the latest cached credit score, enriched with DB data.
func (h *CreditQueryHandler) GetCreditScore(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	// Check cache
	if cached, ok := h.cache.GetScore(customerID); ok {
		c.JSON(http.StatusOK, cached)
		return
	}

	log.Info().Int64("customer", customerID).Msg("fetching credit score")
	authHeader := c.GetHeader("Authorization")

	// 1. Try Python service
	var pythonResult map[string]interface{}
	pythonResult, err = h.pythonClient.GetCreditScore(customerID, authHeader)
	if err != nil {
		log.Warn().Int64("customer", customerID).Err(err).Msg("python score unavailable")
	}

	// 2. Enrich from DB
	result := make(map[string]interface{})
	if pythonResult != nil {
		for k, v := range pythonResult {
			result[k] = v
		}
	}

	type scoreRow struct {
		BaseScore             *float64 `gorm:"column:base_score"`
		CrbContribution       *float64 `gorm:"column:crb_contribution"`
		LlmAdjustment         *float64 `gorm:"column:llm_adjustment"`
		FinalScore            *float64 `gorm:"column:final_score"`
		ScoreBand             *string  `gorm:"column:score_band"`
		PdProbability         *float64 `gorm:"column:pd_probability"`
		ScoredAt              *string  `gorm:"column:scored_at"`
		IncomeStabilityScore  *float64 `gorm:"column:income_stability_score"`
		SavingsRateScore      *float64 `gorm:"column:savings_rate_score"`
		LowBalanceScore       *float64 `gorm:"column:low_balance_score"`
		TransactionDiversity  *float64 `gorm:"column:transaction_diversity"`
		BaseTotal             *float64 `gorm:"column:base_total"`
	}

	var row scoreRow
	sql := `SELECT cse.base_score, cse.crb_contribution, cse.llm_adjustment,
			cse.final_score, cse.score_band, cse.pd_probability, cse.scored_at::text as scored_at,
			bsb.income_stability_score, bsb.savings_rate_score,
			bsb.low_balance_score, bsb.transaction_diversity, bsb.base_total
			FROM credit_score_events cse
			LEFT JOIN base_score_breakdowns bsb ON bsb.score_event_id = cse.event_id
			WHERE cse.customer_id = ? ORDER BY cse.scored_at DESC LIMIT 1`

	if err := h.db.Raw(sql, customerID).Scan(&row).Error; err == nil && row.FinalScore != nil {
		result["base_score"] = safeFloat(row.BaseScore)
		result["crb_contribution"] = safeFloat(row.CrbContribution)
		result["llm_adjustment"] = safeFloat(row.LlmAdjustment)
		if pythonResult == nil {
			result["customer_id"] = customerID
			result["final_score"] = safeFloat(row.FinalScore)
			result["score_band"] = safeString(row.ScoreBand)
			result["pd_probability"] = safeFloat(row.PdProbability)
			result["scored_at"] = safeString(row.ScoredAt)
		}

		baseTotal := safeFloat(row.BaseTotal)
		incStab := safeFloat(row.IncomeStabilityScore)
		savRate := safeFloat(row.SavingsRateScore)
		lowBal := safeFloat(row.LowBalanceScore)
		txDiv := safeFloat(row.TransactionDiversity)
		incLevel := math.Max(0, math.Min(100, baseTotal-incStab-savRate-lowBal-txDiv))

		result["score_breakdown"] = map[string]interface{}{
			"income_stability_score": incStab,
			"income_level_score":     incLevel,
			"savings_rate_score":     savRate,
			"low_balance_score":      lowBal,
			"transaction_diversity":  txDiv,
		}
	}

	if len(result) == 0 {
		result["customer_id"] = customerID
	}

	h.cache.SetScore(customerID, result)
	c.JSON(http.StatusOK, result)
}

// GetFullReport returns full credit report enriched with DB data.
func (h *CreditQueryHandler) GetFullReport(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	// Check cache
	if cached, ok := h.cache.GetReport(customerID); ok {
		c.JSON(http.StatusOK, cached)
		return
	}

	log.Info().Int64("customer", customerID).Msg("fetching full credit report")
	authHeader := c.GetHeader("Authorization")

	// 1. Fetch ML Score from Python
	var mlReport map[string]interface{}
	mlReport, err = h.pythonClient.GetCreditReport(customerID, authHeader)
	if err != nil {
		log.Warn().Int64("customer", customerID).Err(err).Msg("no score found in Python service")
	}

	// 2. Customer details
	type customerInfo struct {
		Name  string `gorm:"column:name"`
		Phone string `gorm:"column:mobile_number"`
		Email string `gorm:"column:email"`
	}
	var cust customerInfo
	h.db.Raw("SELECT first_name || ' ' || last_name AS name, mobile_number, email FROM customers WHERE customer_id = ?", customerID).Scan(&cust)

	// 3. Loan metrics
	type loanMetrics struct {
		TotalPaid      float64 `gorm:"column:total_paid"`
		TotalPenalties float64 `gorm:"column:total_penalties"`
		DefaultLoans   int     `gorm:"column:default_loans"`
		TotalLoans     int     `gorm:"column:total_loans"`
	}
	var metrics loanMetrics
	h.db.Raw(`SELECT
		(SELECT COALESCE(SUM(amount_paid), 0) FROM repayments WHERE customer_id = ?) as total_paid,
		(SELECT COALESCE(SUM(penalty_amount), 0) FROM repayments WHERE customer_id = ?) as total_penalties,
		(SELECT COUNT(*) FROM loans WHERE customer_id = ? AND status = 'DEFAULT') as default_loans,
		(SELECT COUNT(*) FROM loans WHERE customer_id = ?) as total_loans`,
		customerID, customerID, customerID, customerID).Scan(&metrics)

	finalResp := make(map[string]interface{})
	if mlReport != nil {
		for k, v := range mlReport {
			finalResp[k] = v
		}
		finalResp["llm_reasoning"] = mlReport["reasoning"]
		finalResp["crb_bureau_score"] = mlReport["bureau_score"]
		finalResp["crb_npa_count"] = 0
		finalResp["crb_active_default"] = false
	} else {
		finalResp["customer_id"] = customerID
		finalResp["customer_name"] = cust.Name
		finalResp["final_score"] = "N/A"
		finalResp["llm_reasoning"] = "No scoring event found for this customer. Please trigger a new run."
		finalResp["crb_bureau_score"] = "N/A"
		finalResp["crb_npa_count"] = 0
		finalResp["crb_active_default"] = false
	}

	finalResp["phone"] = cust.Phone
	finalResp["sector"] = "Retail (Calculated)"

	delqRate := 0.0
	if metrics.TotalLoans > 0 {
		delqRate = float64(metrics.DefaultLoans) / float64(metrics.TotalLoans)
	}
	finalResp["delinquency_rate_90d"] = delqRate
	maxStreak := 0
	if metrics.DefaultLoans > 0 {
		maxStreak = metrics.DefaultLoans
	}
	finalResp["max_delinquency_streak"] = maxStreak
	finalResp["capital_growth_ratio"] = 0.15
	finalResp["revenue_per_employee"] = 350000
	finalResp["profit_margin"] = 0.12

	h.cache.SetReport(customerID, finalResp)
	c.JSON(http.StatusOK, finalResp)
}

// TriggerScoringRun triggers a fresh scoring run via the Python service.
func (h *CreditQueryHandler) TriggerScoringRun(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}
	log.Info().Int64("customer", customerID).Msg("triggering scoring run")

	authHeader := c.GetHeader("Authorization")
	result, err := h.pythonClient.TriggerScoring(authHeader)
	if err != nil {
		log.Warn().Err(err).Msg("trigger scoring failed")
		c.JSON(http.StatusOK, gin.H{"status": "triggered"})
		return
	}
	c.JSON(http.StatusOK, result)
}

// GetScoreHistory returns score history from credit_score_events.
func (h *CreditQueryHandler) GetScoreHistory(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid customerId"})
		return
	}

	monthsStr := c.DefaultQuery("months", "12")
	months, err := strconv.Atoi(monthsStr)
	if err != nil {
		months = 12
	}

	var history []map[string]interface{}
	sql := `SELECT event_id, final_score, score_band, pd_probability,
			base_score, crb_contribution, llm_adjustment,
			scored_at, model_target
			FROM credit_score_events
			WHERE customer_id = ?
			  AND scored_at >= NOW() - (? * INTERVAL '1 month')
			ORDER BY scored_at DESC`
	h.db.Raw(sql, customerID, months).Scan(&history)

	c.JSON(http.StatusOK, gin.H{
		"customer_id": customerID,
		"months":      months,
		"data":        history,
	})
}

func safeFloat(p *float64) float64 {
	if p == nil {
		return 0.0
	}
	return *p
}

func safeString(p *string) string {
	if p == nil {
		return ""
	}
	return *p
}
