package jwt

import (
	"encoding/base64"
	"fmt"
	"time"

	gojwt "github.com/golang-jwt/jwt/v5"
)

type Claims struct {
	Username   string   `json:"sub"`
	Roles      []string `json:"roles"`
	CustomerID *int64   `json:"customerId,omitempty"`
	TenantID   string   `json:"tenantId,omitempty"`
	gojwt.RegisteredClaims
}

type JWTUtil struct {
	secretBytes []byte
	expMs       int64
}

// New creates a JWTUtil. secret must be the base64-encoded JWT_SECRET
// (matching Java Decoders.BASE64.decode and Python base64.b64decode).
func New(base64Secret string, expirationMs int64) (*JWTUtil, error) {
	raw, err := base64.StdEncoding.DecodeString(base64Secret)
	if err != nil {
		return nil, fmt.Errorf("jwt: failed to base64-decode secret: %w", err)
	}
	return &JWTUtil{secretBytes: raw, expMs: expirationMs}, nil
}

func (j *JWTUtil) GenerateToken(username string, roles []string, customerID *int64) (string, error) {
	return j.GenerateTokenWithTenant(username, roles, customerID, "")
}

func (j *JWTUtil) GenerateTokenWithTenant(username string, roles []string, customerID *int64, tenantID string) (string, error) {
	now := time.Now()
	claims := Claims{
		Username:   username,
		Roles:      roles,
		CustomerID: customerID,
		TenantID:   tenantID,
		RegisteredClaims: gojwt.RegisteredClaims{
			Subject:   username,
			IssuedAt:  gojwt.NewNumericDate(now),
			ExpiresAt: gojwt.NewNumericDate(now.Add(time.Duration(j.expMs) * time.Millisecond)),
		},
	}
	token := gojwt.NewWithClaims(gojwt.SigningMethodHS256, claims)
	return token.SignedString(j.secretBytes)
}

func (j *JWTUtil) ParseToken(tokenStr string) (*Claims, error) {
	token, err := gojwt.ParseWithClaims(tokenStr, &Claims{}, func(t *gojwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*gojwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
		}
		return j.secretBytes, nil
	})
	if err != nil {
		return nil, err
	}
	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, fmt.Errorf("invalid token")
	}
	return claims, nil
}

func (j *JWTUtil) ExtractUsername(tokenStr string) (string, error) {
	claims, err := j.ParseToken(tokenStr)
	if err != nil {
		return "", err
	}
	return claims.Username, nil
}

func (j *JWTUtil) ExtractRoles(tokenStr string) ([]string, error) {
	claims, err := j.ParseToken(tokenStr)
	if err != nil {
		return nil, err
	}
	if claims.Roles == nil {
		return []string{}, nil
	}
	return claims.Roles, nil
}

func (j *JWTUtil) ExtractCustomerID(tokenStr string) (*int64, error) {
	claims, err := j.ParseToken(tokenStr)
	if err != nil {
		return nil, err
	}
	return claims.CustomerID, nil
}
