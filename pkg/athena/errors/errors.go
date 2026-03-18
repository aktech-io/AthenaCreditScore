package errors

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

type ErrorResponse struct {
	Timestamp string `json:"timestamp"`
	Status    int    `json:"status"`
	Error     string `json:"error"`
	Message   string `json:"message"`
}

func Respond(c *gin.Context, status int, errStr, msg string) {
	c.JSON(status, ErrorResponse{
		Timestamp: time.Now().Format(time.RFC3339),
		Status:    status,
		Error:     errStr,
		Message:   msg,
	})
}

func BadRequest(c *gin.Context, msg string) {
	Respond(c, http.StatusBadRequest, "Bad Request", msg)
}

func Unauthorized(c *gin.Context, msg string) {
	Respond(c, http.StatusUnauthorized, "Unauthorized", msg)
}

func Forbidden(c *gin.Context, msg string) {
	Respond(c, http.StatusForbidden, "Forbidden", msg)
}

func NotFound(c *gin.Context, msg string) {
	Respond(c, http.StatusNotFound, "Not Found", msg)
}

func Conflict(c *gin.Context, msg string) {
	Respond(c, http.StatusConflict, "Conflict", msg)
}

func InternalError(c *gin.Context, msg string) {
	Respond(c, http.StatusInternalServerError, "Internal Server Error", msg)
}
