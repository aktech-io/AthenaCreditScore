package repository

import (
	"github.com/athena/user-service/internal/model"
	"gorm.io/gorm"
)

type GroupRepository struct {
	db *gorm.DB
}

func NewGroupRepository(db *gorm.DB) *GroupRepository {
	return &GroupRepository{db: db}
}

func (r *GroupRepository) FindAll() ([]model.Group, error) {
	var groups []model.Group
	if err := r.db.Preload("Roles").Find(&groups).Error; err != nil {
		return nil, err
	}
	return groups, nil
}

func (r *GroupRepository) FindByID(id int64) (*model.Group, error) {
	var group model.Group
	if err := r.db.Preload("Roles").First(&group, id).Error; err != nil {
		return nil, err
	}
	return &group, nil
}

func (r *GroupRepository) FindByName(name string) (*model.Group, error) {
	var group model.Group
	if err := r.db.Preload("Roles").Where("name = ?", name).First(&group).Error; err != nil {
		return nil, err
	}
	return &group, nil
}

func (r *GroupRepository) Create(group *model.Group) error {
	return r.db.Create(group).Error
}

func (r *GroupRepository) Save(group *model.Group) error {
	return r.db.Save(group).Error
}

// AppendRole adds a role to a group.
func (r *GroupRepository) AppendRole(group *model.Group, role *model.Role) error {
	return r.db.Model(group).Association("Roles").Append(role)
}

// RemoveRole removes a role from a group.
func (r *GroupRepository) RemoveRole(group *model.Group, role *model.Role) error {
	return r.db.Model(group).Association("Roles").Delete(role)
}
