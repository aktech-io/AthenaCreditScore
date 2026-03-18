package client

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/rs/zerolog/log"
)

type PythonClient struct {
	baseURL    string
	httpClient *http.Client
}

func NewPythonClient(baseURL string) *PythonClient {
	return &PythonClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (p *PythonClient) GetCreditScore(customerID int64, authHeader string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/credit-score/%d", p.baseURL, customerID)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}
	if authHeader != "" {
		req.Header.Set("Authorization", authHeader)
	}
	return p.doJSON(req)
}

func (p *PythonClient) GetCreditReport(customerID int64, authHeader string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/credit-report/%d", p.baseURL, customerID)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}
	if authHeader != "" {
		req.Header.Set("Authorization", authHeader)
	}
	return p.doJSON(req)
}

func (p *PythonClient) TriggerScoring(authHeader string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/credit-reports", p.baseURL)
	req, err := http.NewRequest("POST", url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-Api-Key", "dev-key")
	if authHeader != "" {
		req.Header.Set("Authorization", authHeader)
	}
	return p.doJSON(req)
}

func (p *PythonClient) GetCreditScoreByAPIKey(customerID int64) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/credit-score/%d", p.baseURL, customerID)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-Api-Key", "dev-key")
	return p.doJSON(req)
}

func (p *PythonClient) doJSON(req *http.Request) (map[string]interface{}, error) {
	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("python client: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("python client: read body: %w", err)
	}

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("not found")
	}
	if resp.StatusCode >= 400 {
		log.Warn().Int("status", resp.StatusCode).Str("body", string(body)).Msg("python client: error response")
		return nil, fmt.Errorf("python client: status %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("python client: unmarshal: %w", err)
	}
	return result, nil
}
