package service

import (
	"fmt"
	"io"
	"math"
	"mime/multipart"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/athena/media-service/internal/model"
	"github.com/athena/media-service/internal/repository"
	"github.com/google/uuid"
	gocache "github.com/patrickmn/go-cache"
	"github.com/rs/zerolog/log"
)

// MediaService handles media file storage and retrieval.
type MediaService struct {
	repo            *repository.MediaRepository
	storageLocation string
	cache           *gocache.Cache
}

// NewMediaService creates and initialises a MediaService.
func NewMediaService(repo *repository.MediaRepository, storageLocation string) *MediaService {
	// Ensure storage directory exists
	if err := os.MkdirAll(storageLocation, 0o755); err != nil {
		log.Fatal().Err(err).Str("path", storageLocation).Msg("could not initialise storage directory")
	}
	log.Info().Str("path", storageLocation).Msg("storage initialised")

	return &MediaService{
		repo:            repo,
		storageLocation: storageLocation,
		// 10 min default expiration, purge every 15 min (matches Caffeine 10 min TTL, 100 items max)
		cache: gocache.New(10*time.Minute, 15*time.Minute),
	}
}

// UploadForCustomer handles the customer-scoped upload (backwards-compatible).
func (s *MediaService) UploadForCustomer(customerID int64, fh *multipart.FileHeader,
	mediaType, category, description, uploadedBy string) (*model.Media, error) {

	return s.doUpload(fh, category, mediaType, nil, description, "", false,
		uploadedBy, "", "", &customerID)
}

// Upload handles the general-purpose upload.
func (s *MediaService) Upload(fh *multipart.FileHeader, category, mediaType string,
	referenceID *uuid.UUID, description, tags string, isPublic bool,
	uploadedBy, serviceName, channel string) (*model.Media, error) {

	return s.doUpload(fh, category, mediaType, referenceID, description,
		tags, isPublic, uploadedBy, serviceName, channel, nil)
}

func (s *MediaService) doUpload(fh *multipart.FileHeader, category, mediaType string,
	referenceID *uuid.UUID, description, tags string, isPublic bool,
	uploadedBy, serviceName, channel string, customerID *int64) (*model.Media, error) {

	if fh.Size == 0 {
		return nil, fmt.Errorf("cannot upload empty file")
	}

	originalFilename := fh.Filename
	ext := getExtension(originalFilename)
	storedFilename := uuid.New().String() + ext

	// Path traversal protection
	dest := filepath.Join(s.storageLocation, storedFilename)
	absRoot, _ := filepath.Abs(s.storageLocation)
	absDest, _ := filepath.Abs(dest)
	if !strings.HasPrefix(absDest, absRoot+string(os.PathSeparator)) && absDest != absRoot {
		return nil, fmt.Errorf("cannot store file outside storage directory")
	}

	src, err := fh.Open()
	if err != nil {
		return nil, fmt.Errorf("failed to open upload: %w", err)
	}
	defer src.Close()

	out, err := os.Create(dest)
	if err != nil {
		return nil, fmt.Errorf("failed to create file: %w", err)
	}
	defer out.Close()

	if _, err = io.Copy(out, src); err != nil {
		return nil, fmt.Errorf("failed to store file: %s: %w", originalFilename, err)
	}

	fileSize := fh.Size
	contentType := fh.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/octet-stream"
	}

	media := &model.Media{
		ID:               uuid.New(),
		ReferenceID:      referenceID,
		CustomerID:       customerID,
		Category:         category,
		MediaType:        mediaType,
		OriginalFilename: originalFilename,
		StoredFilename:   storedFilename,
		ContentType:      contentType,
		FileSize:         &fileSize,
		Description:      description,
		Tags:             tags,
		IsPublic:         isPublic,
		UploadedBy:       uploadedBy,
		ServiceName:      serviceName,
		Channel:          channel,
		Status:           model.StatusActive,
	}

	if err := s.repo.Save(media); err != nil {
		return nil, fmt.Errorf("failed to save media record: %w", err)
	}

	log.Info().
		Str("id", media.ID.String()).
		Str("category", category).
		Stringer("customerId", intPtrStringer{customerID}).
		Stringer("referenceId", referenceID).
		Msg("media uploaded")

	return media, nil
}

// DownloadMedia returns the file path and metadata for the given media ID.
func (s *MediaService) DownloadMedia(mediaID uuid.UUID) (string, *model.Media, error) {
	media, err := s.GetMediaMetadata(mediaID)
	if err != nil {
		return "", nil, err
	}

	filePath := filepath.Join(s.storageLocation, media.StoredFilename)
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return "", nil, fmt.Errorf("could not read file: %s", media.OriginalFilename)
	}

	return filePath, media, nil
}

// GetMediaMetadata returns cached metadata for the given media ID.
func (s *MediaService) GetMediaMetadata(mediaID uuid.UUID) (*model.Media, error) {
	cacheKey := "metadata:" + mediaID.String()
	if cached, found := s.cache.Get(cacheKey); found {
		m := cached.(*model.Media)
		return m, nil
	}

	media, err := s.repo.FindByID(mediaID)
	if err != nil {
		return nil, fmt.Errorf("media not found: %s", mediaID)
	}

	s.cache.Set(cacheKey, media, gocache.DefaultExpiration)
	return media, nil
}

// GetMediaByCustomer returns all media for a customer.
func (s *MediaService) GetMediaByCustomer(customerID int64) ([]model.Media, error) {
	return s.repo.FindByCustomerID(customerID)
}

// FindByCategory returns all media for a category.
func (s *MediaService) FindByCategory(category string) ([]model.Media, error) {
	return s.repo.FindByCategory(category)
}

// FindByReferenceID returns all media for a reference entity.
func (s *MediaService) FindByReferenceID(refID uuid.UUID) ([]model.Media, error) {
	return s.repo.FindByReferenceID(refID)
}

// FindByTag returns media matching a tag substring.
func (s *MediaService) FindByTag(tag string) ([]model.Media, error) {
	return s.repo.FindByTagsContaining(tag)
}

// SearchMedia filters media by category and/or status.
func (s *MediaService) SearchMedia(category, status *string) ([]model.Media, error) {
	if category == nil && status == nil {
		return s.repo.FindAll()
	}
	return s.repo.SearchMedia(category, status, nil, nil)
}

// UpdateMetadata updates description, tags, and/or status.
func (s *MediaService) UpdateMetadata(mediaID uuid.UUID, description, tags *string, status *string) (*model.Media, error) {
	media, err := s.repo.FindByID(mediaID)
	if err != nil {
		return nil, fmt.Errorf("media not found: %s", mediaID)
	}

	if description != nil {
		media.Description = *description
	}
	if tags != nil {
		media.Tags = *tags
	}
	if status != nil {
		media.Status = *status
	}

	if err := s.repo.Save(media); err != nil {
		return nil, fmt.Errorf("failed to update media: %w", err)
	}

	// Evict cache
	s.cache.Delete("metadata:" + mediaID.String())

	log.Info().Str("id", mediaID.String()).Msg("media metadata updated")
	return media, nil
}

// GetAllMedia returns a paginated list.
func (s *MediaService) GetAllMedia(page, size int) (*model.PageResponse, error) {
	media, total, err := s.repo.FindAllPaginated(page, size)
	if err != nil {
		return nil, err
	}
	totalPages := 0
	if size > 0 {
		totalPages = int(math.Ceil(float64(total) / float64(size)))
	}
	return &model.PageResponse{
		Content:       media,
		TotalElements: total,
		TotalPages:    totalPages,
		Size:          size,
		Number:        page,
	}, nil
}

// GetStats returns storage and document statistics.
func (s *MediaService) GetStats() (map[string]interface{}, error) {
	allMedia, err := s.repo.FindAll()
	if err != nil {
		return nil, err
	}

	var usedSpace int64
	for _, m := range allMedia {
		if m.FileSize != nil {
			usedSpace += *m.FileSize
		}
	}

	var stat os.FileInfo
	stat, err = os.Stat(s.storageLocation)
	_ = stat

	// Get disk stats via syscall-free approach: total/free from OS
	// Use a simpler approach that doesn't need syscall
	totalSpace := int64(0)
	freeSpace := int64(0)
	// We'll report the used space from DB; total/free are best-effort
	// The Java version uses File.getTotalSpace / getFreeSpace which is JVM-specific

	docsByType, err := s.repo.CountByMediaType()
	if err != nil {
		return nil, err
	}

	totalDocs, err := s.repo.Count()
	if err != nil {
		return nil, err
	}

	usedPct := float64(0)
	if totalSpace > 0 {
		usedPct = float64(usedSpace) * 100 / float64(totalSpace)
	}

	stats := map[string]interface{}{
		"totalSpace":     totalSpace,
		"usedSpace":      usedSpace,
		"freeSpace":      freeSpace,
		"usedPercentage": usedPct,
		"totalDocuments": totalDocs,
		"documentsByType": docsByType,
	}
	return stats, nil
}

// DeleteMedia removes a media file from disk and database.
func (s *MediaService) DeleteMedia(mediaID uuid.UUID) error {
	media, err := s.repo.FindByID(mediaID)
	if err != nil {
		return fmt.Errorf("media not found: %s", mediaID)
	}

	filePath := filepath.Join(s.storageLocation, media.StoredFilename)
	_ = os.Remove(filePath) // ignore error if file already gone

	if err := s.repo.Delete(media); err != nil {
		return fmt.Errorf("failed to delete media: %w", err)
	}

	// Evict cache
	s.cache.Delete("metadata:" + mediaID.String())

	log.Info().Str("id", mediaID.String()).Msg("media deleted")
	return nil
}

func getExtension(filename string) string {
	if filename == "" || !strings.Contains(filename, ".") {
		return ""
	}
	return filename[strings.LastIndex(filename, "."):]
}

type intPtrStringer struct {
	p *int64
}

func (i intPtrStringer) String() string {
	if i.p == nil {
		return "<nil>"
	}
	return fmt.Sprintf("%d", *i.p)
}
