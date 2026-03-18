package dto

type MifosTransactionResponse struct {
	ID                  int64   `json:"id"`
	Date                string  `json:"date"`
	Amount              float64 `json:"amount"`
	Type                string  `json:"type"`
	SubmittedByUsername string  `json:"submittedByUsername"`
	Currency            string  `json:"currency"`
	RunningBalance      float64 `json:"runningBalance"`
}
