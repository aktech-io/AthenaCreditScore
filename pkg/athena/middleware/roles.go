package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// RequireRoles returns middleware that checks if the authenticated user
// has at least one of the specified roles.
func RequireRoles(roles ...string) gin.HandlerFunc {
	allowed := make(map[string]bool, len(roles))
	for _, r := range roles {
		allowed[r] = true
	}
	return func(c *gin.Context) {
		userRoles := GetRoles(c)
		for _, r := range userRoles {
			if allowed[r] {
				c.Next()
				return
			}
		}
		c.AbortWithStatusJSON(http.StatusForbidden, gin.H{
			"error":   "Forbidden",
			"message": "Insufficient permissions",
		})
	}
}
