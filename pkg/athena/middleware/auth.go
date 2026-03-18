package middleware

import (
	"net/http"
	"strings"

	"github.com/athena/pkg/jwt"
	"github.com/gin-gonic/gin"
)

func JWTAuth(jwtUtil *jwt.JWTUtil) gin.HandlerFunc {
	return func(c *gin.Context) {
		header := c.GetHeader("Authorization")
		if header == "" || !strings.HasPrefix(header, "Bearer ") {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"error":   "Unauthorized",
				"message": "Missing or invalid Authorization header",
			})
			return
		}
		tokenStr := strings.TrimPrefix(header, "Bearer ")

		claims, err := jwtUtil.ParseToken(tokenStr)
		if err != nil {
			msg := "Invalid token"
			if strings.Contains(err.Error(), "expired") {
				msg = "Token expired"
			}
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"error":   msg,
				"message": "Your session has expired. Please log in again.",
			})
			return
		}

		c.Set("username", claims.Username)
		c.Set("roles", claims.Roles)
		if claims.CustomerID != nil {
			c.Set("customerId", *claims.CustomerID)
		}
		if claims.TenantID != "" {
			c.Set("tenantId", claims.TenantID)
		}

		c.Next()
	}
}

// OptionalJWTAuth extracts JWT claims if present but does not require auth.
func OptionalJWTAuth(jwtUtil *jwt.JWTUtil) gin.HandlerFunc {
	return func(c *gin.Context) {
		header := c.GetHeader("Authorization")
		if header != "" && strings.HasPrefix(header, "Bearer ") {
			tokenStr := strings.TrimPrefix(header, "Bearer ")
			if claims, err := jwtUtil.ParseToken(tokenStr); err == nil {
				c.Set("username", claims.Username)
				c.Set("roles", claims.Roles)
				if claims.CustomerID != nil {
					c.Set("customerId", *claims.CustomerID)
				}
			}
		}
		c.Next()
	}
}

func GetUsername(c *gin.Context) string {
	if v, ok := c.Get("username"); ok {
		return v.(string)
	}
	return "system"
}

func GetRoles(c *gin.Context) []string {
	if v, ok := c.Get("roles"); ok {
		return v.([]string)
	}
	return nil
}

func GetCustomerID(c *gin.Context) (int64, bool) {
	if v, ok := c.Get("customerId"); ok {
		return v.(int64), true
	}
	return 0, false
}
