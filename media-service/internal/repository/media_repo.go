package repository

import (
	"time"

	"github.com/athena/media-service/internal/model"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

// MediaRepository provides data access for media_files.
type MediaRepository struct {
	db *gorm.DB
}

// NewMediaRepository creates a new MediaRepository.
func NewMediaRepository(db *gorm.DB) *MediaRepository {
	return &MediaRepository{db: db}
}

func (r *MediaRepository) Save(m *model.Media) error {
	return r.db.Save(m).Error
}

func (r *MediaRepository) FindByID(id uuid.UUID) (*model.Media, error) {
	var m model.Media
	if err := r.db.First(&m, "id = ?", id).Error; err != nil {
		return nil, err
	}
	return &m, nil
}

func (r *MediaRepository) FindByCustomerID(customerID int64) ([]model.Media, error) {
	var media []model.Media
	if err := r.db.Where("customer_id = ?", customerID).Find(&media).Error; err != nil {
		return nil, err
	}
	return media, nil
}

func (r *MediaRepository) FindByCategory(category string) ([]model.Media, error) {
	var media []model.Media
	if err := r.db.Where("category = ?", category).Find(&media).Error; err != nil {
		return nil, err
	}
	return media, nil
}

func (r *MediaRepository) FindByReferenceID(refID uuid.UUID) ([]model.Media, error) {
	var media []model.Media
	if err := r.db.Where("reference_id = ?", refID).Find(&media).Error; err != nil {
		return nil, err
	}
	return media, nil
}

func (r *MediaRepository) FindByTagsContaining(tag string) ([]model.Media, error) {
	var media []model.Media
	if err := r.db.Where("tags LIKE ?", "%"+tag+"%").Find(&media).Error; err != nil {
		return nil, err
	}
	return media, nil
}

func (r *MediaRepository) SearchMedia(category *string, status *string, fromDate, toDate *time.Time) ([]model.Media, error) {
	var media []model.Media
	q := r.db.Model(&model.Media{})
	if category != nil {
		q = q.Where("category = ?", *category)
	}
	if status != nil {
		q = q.Where("status = ?", *status)
	}
	if fromDate != nil {
		q = q.Where("created_at >= ?", *fromDate)
	}
	if toDate != nil {
		q = q.Where("created_at <= ?", *toDate)
	}
	if err := q.Find(&media).Error; err != nil {
		return nil, err
	}
	return media, nil
}

func (r *MediaRepository) FindAll() ([]model.Media, error) {
	var media []model.Media
	if err := r.db.Find(&media).Error; err != nil {
		return nil, err
	}
	return media, nil
}

func (r *MediaRepository) FindAllPaginated(page, size int) ([]model.Media, int64, error) {
	var media []model.Media
	var total int64
	r.db.Model(&model.Media{}).Count(&total)
	if err := r.db.Offset(page * size).Limit(size).Order("created_at DESC").Find(&media).Error; err != nil {
		return nil, 0, err
	}
	return media, total, nil
}

func (r *MediaRepository) Count() (int64, error) {
	var count int64
	if err := r.db.Model(&model.Media{}).Count(&count).Error; err != nil {
		return 0, err
	}
	return count, nil
}

// CountByMediaType returns a map of media_type -> count.
func (r *MediaRepository) CountByMediaType() (map[string]int64, error) {
	type result struct {
		MediaType string
		Count     int64
	}
	var results []result
	if err := r.db.Model(&model.Media{}).
		Select("media_type, count(*) as count").
		Group("media_type").
		Scan(&results).Error; err != nil {
		return nil, err
	}
	m := make(map[string]int64, len(results))
	for _, r := range results {
		m[r.MediaType] = r.Count
	}
	return m, nil
}

// CountByCategory returns a map of category -> count.
func (r *MediaRepository) CountByCategory() (map[string]int64, error) {
	type result struct {
		Category string
		Count    int64
	}
	var results []result
	if err := r.db.Model(&model.Media{}).
		Select("category, count(*) as count").
		Group("category").
		Scan(&results).Error; err != nil {
		return nil, err
	}
	m := make(map[string]int64, len(results))
	for _, r := range results {
		m[r.Category] = r.Count
	}
	return m, nil
}

func (r *MediaRepository) Delete(m *model.Media) error {
	return r.db.Delete(m).Error
}
