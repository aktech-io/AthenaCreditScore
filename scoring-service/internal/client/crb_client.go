package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

type CrbClient struct {
	httpClient      *http.Client
	transunionURL   string
	transunionKey   string
	metropolURL     string
	metropolKey     string
}

func NewCrbClient(transunionURL, transunionKey, metropolURL, metropolKey string) *CrbClient {
	return &CrbClient{
		httpClient:    &http.Client{Timeout: 30 * time.Second},
		transunionURL: transunionURL,
		transunionKey: transunionKey,
		metropolURL:   metropolURL,
		metropolKey:   metropolKey,
	}
}

func (c *CrbClient) FetchTransUnionReport(nationalID string) (map[string]interface{}, error) {
	log.Info().Str("nationalId", nationalID).Msg("fetching TransUnion report")
	payload := map[string]string{
		"nationalId": nationalID,
		"requestId":  uuid.New().String(),
	}
	return c.postWithRetry(c.transunionURL, payload, map[string]string{
		"Authorization": "Bearer " + c.transunionKey,
		"Content-Type":  "application/json",
	}, "TransUnion")
}

func (c *CrbClient) FetchMetropolReport(nationalID string) (map[string]interface{}, error) {
	log.Info().Str("nationalId", nationalID).Msg("fetching Metropol report")
	payload := map[string]string{
		"nationalId": nationalID,
	}
	return c.postWithRetry(c.metropolURL, payload, map[string]string{
		"X-Api-Key":    c.metropolKey,
		"Content-Type": "application/json",
	}, "Metropol")
}

func (c *CrbClient) postWithRetry(url string, payload interface{}, headers map[string]string, name string) (map[string]interface{}, error) {
	var lastErr error
	for attempt := 0; attempt < 3; attempt++ {
		if attempt > 0 {
			delay := time.Duration(math.Pow(2, float64(attempt-1))) * time.Second
			time.Sleep(delay)
		}

		body, err := json.Marshal(payload)
		if err != nil {
			return nil, fmt.Errorf("%s: marshal: %w", name, err)
		}

		req, err := http.NewRequest("POST", url, bytes.NewReader(body))
		if err != nil {
			return nil, fmt.Errorf("%s: create request: %w", name, err)
		}
		for k, v := range headers {
			req.Header.Set(k, v)
		}

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = fmt.Errorf("%s: attempt %d: %w", name, attempt+1, err)
			log.Warn().Err(lastErr).Msg("CRB fetch failed, retrying")
			continue
		}

		respBody, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			lastErr = fmt.Errorf("%s: read body: %w", name, err)
			continue
		}

		if resp.StatusCode >= 400 {
			lastErr = fmt.Errorf("%s error: status %d: %s", name, resp.StatusCode, string(respBody))
			log.Warn().Err(lastErr).Msg("CRB fetch error, retrying")
			continue
		}

		var result map[string]interface{}
		if err := json.Unmarshal(respBody, &result); err != nil {
			return nil, fmt.Errorf("%s: unmarshal: %w", name, err)
		}
		log.Info().Str("crb", name).Str("nationalId", fmt.Sprintf("%v", payload)).Msg("CRB report received")
		return result, nil
	}
	return nil, lastErr
}
