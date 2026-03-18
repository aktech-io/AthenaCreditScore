package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/athena/customer-service/internal/dto"
)

// MediaClient calls media-service over HTTP (replaces Java Feign client).
type MediaClient struct {
	baseURL    string
	httpClient *http.Client
}

func NewMediaClient() *MediaClient {
	baseURL := os.Getenv("MEDIA_SERVICE_URL")
	if baseURL == "" {
		baseURL = "http://media-service:8083"
	}
	return &MediaClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// GetMediaMetadata fetches metadata for a media file by UUID.
func (mc *MediaClient) GetMediaMetadata(id string) (*dto.MediaResponse, error) {
	url := fmt.Sprintf("%s/api/v1/media/%s", mc.baseURL, id)
	resp, err := mc.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("media-service request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("media-service returned status %d for id=%s", resp.StatusCode, id)
	}

	var media dto.MediaResponse
	if err := json.NewDecoder(resp.Body).Decode(&media); err != nil {
		return nil, fmt.Errorf("failed to decode media response: %w", err)
	}
	return &media, nil
}
