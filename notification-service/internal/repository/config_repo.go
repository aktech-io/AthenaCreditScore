package repository

import (
	"github.com/athena/notification-service/internal/model"
	"gorm.io/gorm"
)

type ConfigRepository struct {
	db *gorm.DB
}

func NewConfigRepository(db *gorm.DB) *ConfigRepository {
	return &ConfigRepository{db: db}
}

func (r *ConfigRepository) FindByType(configType string) (*model.NotificationConfig, error) {
	var cfg model.NotificationConfig
	result := r.db.Where("type = ?", configType).First(&cfg)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			return nil, nil
		}
		return nil, result.Error
	}
	return &cfg, nil
}

func (r *ConfigRepository) Save(cfg *model.NotificationConfig) error {
	return r.db.Save(cfg).Error
}

func (r *ConfigRepository) Create(cfg *model.NotificationConfig) error {
	return r.db.Create(cfg).Error
}
