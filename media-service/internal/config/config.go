package config

import "os"

// MediaConfig holds media-service-specific configuration.
type MediaConfig struct {
	StorageLocation string
	MaxUploadSizeMB int64
}

func LoadMediaConfig() *MediaConfig {
	return &MediaConfig{
		StorageLocation: getEnv("STORAGE_LOCATION", "/app/storage"),
		MaxUploadSizeMB: 10,
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
