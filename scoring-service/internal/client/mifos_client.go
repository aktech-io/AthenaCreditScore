package client

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type MifosClient struct {
	httpClient *http.Client
	baseURL    string
	basicAuth  string
}

func NewMifosClient(baseURL, username, password string) *MifosClient {
	auth := base64.StdEncoding.EncodeToString([]byte(username + ":" + password))
	return &MifosClient{
		httpClient: &http.Client{Timeout: 30 * time.Second},
		baseURL:    baseURL,
		basicAuth:  "Basic " + auth,
	}
}

func (m *MifosClient) GetSavingsTransactions(accountID string, limit int) ([]map[string]interface{}, error) {
	url := fmt.Sprintf("%s/savingsaccounts/%s/transactions?limit=%d", m.baseURL, accountID, limit)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", m.basicAuth)

	resp, err := m.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("mifos: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("mifos: read body: %w", err)
	}

	var result []map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("mifos: unmarshal: %w", err)
	}
	return result, nil
}

func (m *MifosClient) GetClientDetails(clientID string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/clients/%s", m.baseURL, clientID)
	return m.doGet(url)
}

func (m *MifosClient) GetClientAccounts(clientID string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/clients/%s/accounts", m.baseURL, clientID)
	return m.doGet(url)
}

func (m *MifosClient) doGet(url string) (map[string]interface{}, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", m.basicAuth)

	resp, err := m.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("mifos: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("mifos: read body: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("mifos: unmarshal: %w", err)
	}
	return result, nil
}
