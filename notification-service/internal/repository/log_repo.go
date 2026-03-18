package repository

import (
	"github.com/athena/notification-service/internal/model"
	"gorm.io/gorm"
)

type LogRepository struct {
	db *gorm.DB
}

func NewLogRepository(db *gorm.DB) *LogRepository {
	return &LogRepository{db: db}
}

func (r *LogRepository) Save(entry *model.NotificationLog) error {
	return r.db.Create(entry).Error
}

func (r *LogRepository) FindByServiceName(serviceName string) ([]model.NotificationLog, error) {
	var logs []model.NotificationLog
	err := r.db.Where("service_name = ?", serviceName).Find(&logs).Error
	return logs, err
}

func (r *LogRepository) FindByRecipient(recipient string) ([]model.NotificationLog, error) {
	var logs []model.NotificationLog
	err := r.db.Where("recipient = ?", recipient).Find(&logs).Error
	return logs, err
}

func (r *LogRepository) FindByType(logType string) ([]model.NotificationLog, error) {
	var logs []model.NotificationLog
	err := r.db.Where("type = ?", logType).Find(&logs).Error
	return logs, err
}
