package config

import (
	"fmt"
	"os"
	"strconv"
)

type Config struct {
	Port        string
	DBHost      string
	DBPort      string
	DBUser      string
	DBPassword  string
	DBName      string
	JWTSecret   string
	JWTExpMs    int64
	RabbitMQURL string
}

func Load() *Config {
	return &Config{
		Port:        getEnv("PORT", "8080"),
		DBHost:      getEnv("DB_HOST", "localhost"),
		DBPort:      getEnv("DB_PORT", "5432"),
		DBUser:      getEnv("DB_USER", "athena"),
		DBPassword:  getEnv("DB_PASSWORD", "athena_secret_change_me"),
		DBName:      getEnv("DB_NAME", "athena_db"),
		JWTSecret:   getEnv("JWT_SECRET", ""),
		JWTExpMs:    getEnvInt64("JWT_EXPIRATION", 86400000),
		RabbitMQURL: getEnv("RABBITMQ_URL", "amqp://athena:athena_secret_change_me@localhost:5672/"),
	}
}

func (c *Config) DSN() string {
	return fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		c.DBHost, c.DBPort, c.DBUser, c.DBPassword, c.DBName)
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvInt64(key string, fallback int64) int64 {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.ParseInt(v, 10, 64); err == nil {
			return i
		}
	}
	return fallback
}
