package repository

import (
	"github.com/athena/user-service/internal/model"
	"gorm.io/gorm"
)

type PasswordPolicyRepository struct {
	db *gorm.DB
}

func NewPasswordPolicyRepository(db *gorm.DB) *PasswordPolicyRepository {
	return &PasswordPolicyRepository{db: db}
}

func (r *PasswordPolicyRepository) FindFirst() (*model.PasswordPolicy, error) {
	var policy model.PasswordPolicy
	if err := r.db.First(&policy).Error; err != nil {
		return nil, err
	}
	return &policy, nil
}

func (r *PasswordPolicyRepository) Count() int64 {
	var count int64
	r.db.Model(&model.PasswordPolicy{}).Count(&count)
	return count
}

func (r *PasswordPolicyRepository) Create(policy *model.PasswordPolicy) error {
	return r.db.Create(policy).Error
}

func (r *PasswordPolicyRepository) Save(policy *model.PasswordPolicy) error {
	return r.db.Save(policy).Error
}
