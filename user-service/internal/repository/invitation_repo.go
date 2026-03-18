package repository

import (
	"github.com/athena/user-service/internal/model"
	"gorm.io/gorm"
)

type InvitationRepository struct {
	db *gorm.DB
}

func NewInvitationRepository(db *gorm.DB) *InvitationRepository {
	return &InvitationRepository{db: db}
}

func (r *InvitationRepository) FindByToken(token string) (*model.Invitation, error) {
	var inv model.Invitation
	if err := r.db.Preload("Roles").Preload("Groups").Preload("Groups.Roles").Where("token = ?", token).First(&inv).Error; err != nil {
		return nil, err
	}
	return &inv, nil
}

func (r *InvitationRepository) Create(inv *model.Invitation) error {
	return r.db.Create(inv).Error
}

func (r *InvitationRepository) Save(inv *model.Invitation) error {
	return r.db.Save(inv).Error
}
