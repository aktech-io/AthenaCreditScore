package repository

import (
	"github.com/athena/user-service/internal/model"
	"gorm.io/gorm"
)

type AdminUserRepository struct {
	db *gorm.DB
}

func NewAdminUserRepository(db *gorm.DB) *AdminUserRepository {
	return &AdminUserRepository{db: db}
}

func (r *AdminUserRepository) FindByUsername(username string) (*model.AdminUser, error) {
	var user model.AdminUser
	if err := r.db.Where("username = ?", username).First(&user).Error; err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *AdminUserRepository) FindByID(id int64) (*model.AdminUser, error) {
	var user model.AdminUser
	if err := r.db.First(&user, id).Error; err != nil {
		return nil, err
	}
	return &user, nil
}
