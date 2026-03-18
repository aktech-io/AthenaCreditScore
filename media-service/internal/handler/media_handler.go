package handler

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/athena/media-service/internal/model"
	"github.com/athena/media-service/internal/service"
	"github.com/athena/pkg/middleware"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// MediaHandler handles media REST endpoints.
type MediaHandler struct {
	svc *service.MediaService
}

// NewMediaHandler creates a new MediaHandler.
func NewMediaHandler(svc *service.MediaService) *MediaHandler {
	return &MediaHandler{svc: svc}
}

// RegisterRoutes registers all media endpoints on the given router group.
func (h *MediaHandler) RegisterRoutes(rg *gin.RouterGroup) {
	rg.POST("/upload/:customerId", h.UploadForCustomer)
	rg.POST("/upload", h.Upload)
	rg.GET("/customer/:customerId", h.GetCustomerMedia)
	rg.GET("/download/:mediaId", h.DownloadMedia)
	rg.GET("/metadata/:mediaId", h.GetMetadata)
	rg.GET("/reference/:referenceId", h.GetByReference)
	rg.GET("/category/:category", h.GetByCategory)
	rg.GET("", h.Search)
	rg.PATCH("/:mediaId", h.UpdateMetadata)
	rg.DELETE("/:mediaId", h.DeleteMedia)
}

// UploadForCustomer handles POST /api/v1/media/upload/:customerId
func (h *MediaHandler) UploadForCustomer(c *gin.Context) {
	customerIDStr := c.Param("customerId")
	customerID, err := strconv.ParseInt(customerIDStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid customer ID"})
		return
	}

	file, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "File is required"})
		return
	}

	mediaType := c.PostForm("mediaType")
	if mediaType == "" || !model.ValidMediaTypes[mediaType] {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Valid mediaType is required"})
		return
	}

	category := c.DefaultPostForm("category", model.CategoryCustomerDocument)
	if !model.ValidCategories[category] {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid category"})
		return
	}

	description := c.PostForm("description")
	uploadedBy := middleware.GetUsername(c)

	// Max upload size check (10MB)
	if file.Size > 10*1024*1024 {
		c.JSON(http.StatusRequestEntityTooLarge, gin.H{
			"error":   "File too large",
			"message": "File size exceeds the maximum allowed size of 10MB.",
		})
		return
	}

	media, err := h.svc.UploadForCustomer(customerID, file, mediaType, category, description, uploadedBy)
	if err != nil {
		handleError(c, err)
		return
	}

	c.JSON(http.StatusOK, media)
}

// Upload handles POST /api/v1/media/upload
func (h *MediaHandler) Upload(c *gin.Context) {
	file, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "File is required"})
		return
	}

	category := c.PostForm("category")
	if category == "" || !model.ValidCategories[category] {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Valid category is required"})
		return
	}

	mediaType := c.PostForm("mediaType")
	if mediaType == "" || !model.ValidMediaTypes[mediaType] {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Valid mediaType is required"})
		return
	}

	var referenceID *uuid.UUID
	if refStr := c.PostForm("referenceId"); refStr != "" {
		parsed, err := uuid.Parse(refStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid referenceId"})
			return
		}
		referenceID = &parsed
	}

	description := c.PostForm("description")
	tags := c.PostForm("tags")
	isPublicStr := c.DefaultPostForm("isPublic", "false")
	isPublic := isPublicStr == "true"
	serviceName := c.PostForm("serviceName")
	channel := c.PostForm("channel")
	uploadedBy := middleware.GetUsername(c)

	if file.Size > 10*1024*1024 {
		c.JSON(http.StatusRequestEntityTooLarge, gin.H{
			"error":   "File too large",
			"message": "File size exceeds the maximum allowed size of 10MB.",
		})
		return
	}

	media, err := h.svc.Upload(file, category, mediaType, referenceID, description,
		tags, isPublic, uploadedBy, serviceName, channel)
	if err != nil {
		handleError(c, err)
		return
	}

	c.JSON(http.StatusOK, media)
}

// GetCustomerMedia handles GET /api/v1/media/customer/:customerId
func (h *MediaHandler) GetCustomerMedia(c *gin.Context) {
	customerID, err := strconv.ParseInt(c.Param("customerId"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid customer ID"})
		return
	}

	media, err := h.svc.GetMediaByCustomer(customerID)
	if err != nil {
		handleError(c, err)
		return
	}
	c.JSON(http.StatusOK, media)
}

// DownloadMedia handles GET /api/v1/media/download/:mediaId
func (h *MediaHandler) DownloadMedia(c *gin.Context) {
	mediaID, err := uuid.Parse(c.Param("mediaId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid media ID"})
		return
	}

	filePath, meta, err := h.svc.DownloadMedia(mediaID)
	if err != nil {
		handleError(c, err)
		return
	}

	c.Header("Content-Disposition", `attachment; filename="`+meta.OriginalFilename+`"`)
	c.File(filePath)
}

// GetMetadata handles GET /api/v1/media/metadata/:mediaId
func (h *MediaHandler) GetMetadata(c *gin.Context) {
	mediaID, err := uuid.Parse(c.Param("mediaId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid media ID"})
		return
	}

	media, err := h.svc.GetMediaMetadata(mediaID)
	if err != nil {
		handleError(c, err)
		return
	}
	c.JSON(http.StatusOK, media)
}

// GetByReference handles GET /api/v1/media/reference/:referenceId
func (h *MediaHandler) GetByReference(c *gin.Context) {
	refID, err := uuid.Parse(c.Param("referenceId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid reference ID"})
		return
	}

	media, err := h.svc.FindByReferenceID(refID)
	if err != nil {
		handleError(c, err)
		return
	}
	c.JSON(http.StatusOK, media)
}

// GetByCategory handles GET /api/v1/media/category/:category
func (h *MediaHandler) GetByCategory(c *gin.Context) {
	category := c.Param("category")
	if !model.ValidCategories[category] {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid category"})
		return
	}

	media, err := h.svc.FindByCategory(category)
	if err != nil {
		handleError(c, err)
		return
	}
	c.JSON(http.StatusOK, media)
}

// Search handles GET /api/v1/media
func (h *MediaHandler) Search(c *gin.Context) {
	tag := c.Query("tag")
	if tag != "" {
		media, err := h.svc.FindByTag(tag)
		if err != nil {
			handleError(c, err)
			return
		}
		c.JSON(http.StatusOK, media)
		return
	}

	var categoryPtr, statusPtr *string
	if cat := c.Query("category"); cat != "" {
		categoryPtr = &cat
	}
	if st := c.Query("status"); st != "" {
		statusPtr = &st
	}

	media, err := h.svc.SearchMedia(categoryPtr, statusPtr)
	if err != nil {
		handleError(c, err)
		return
	}
	c.JSON(http.StatusOK, media)
}

// UpdateMetadata handles PATCH /api/v1/media/:mediaId
func (h *MediaHandler) UpdateMetadata(c *gin.Context) {
	mediaID, err := uuid.Parse(c.Param("mediaId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid media ID"})
		return
	}

	var descriptionPtr, tagsPtr, statusPtr *string
	if v := c.Query("description"); v != "" {
		descriptionPtr = &v
	}
	if v := c.Query("tags"); v != "" {
		tagsPtr = &v
	}
	if v := c.Query("status"); v != "" {
		if !model.ValidStatuses[v] {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid status"})
			return
		}
		statusPtr = &v
	}

	media, err := h.svc.UpdateMetadata(mediaID, descriptionPtr, tagsPtr, statusPtr)
	if err != nil {
		handleError(c, err)
		return
	}
	c.JSON(http.StatusOK, media)
}

// DeleteMedia handles DELETE /api/v1/media/:mediaId
func (h *MediaHandler) DeleteMedia(c *gin.Context) {
	mediaID, err := uuid.Parse(c.Param("mediaId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": "Invalid media ID"})
		return
	}

	if err := h.svc.DeleteMedia(mediaID); err != nil {
		handleError(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

// handleError maps service errors to HTTP responses matching Java GlobalExceptionHandler.
func handleError(c *gin.Context, err error) {
	msg := err.Error()
	if strings.Contains(msg, "not found") {
		c.JSON(http.StatusNotFound, gin.H{"error": "Not Found", "message": msg})
		return
	}
	c.JSON(http.StatusBadRequest, gin.H{"error": "Error", "message": msg})
}
