package repository

import (
	"github.com/athena/user-service/internal/model"
	"gorm.io/gorm"
)

type UserRepository struct {
	db *gorm.DB
}

func NewUserRepository(db *gorm.DB) *UserRepository {
	return &UserRepository{db: db}
}

func (r *UserRepository) FindAll() ([]model.User, error) {
	var users []model.User
	if err := r.db.Preload("Roles").Preload("Groups").Preload("Groups.Roles").Find(&users).Error; err != nil {
		return nil, err
	}
	return users, nil
}

func (r *UserRepository) FindByID(id int64) (*model.User, error) {
	var user model.User
	if err := r.db.Preload("Roles").Preload("Groups").Preload("Groups.Roles").First(&user, id).Error; err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *UserRepository) FindByUsername(username string) (*model.User, error) {
	var user model.User
	if err := r.db.Preload("Roles").Preload("Groups").Preload("Groups.Roles").Where("username = ?", username).First(&user).Error; err != nil {
		return nil, err
	}
	return &user, nil
}

func (r *UserRepository) ExistsByUsername(username string) bool {
	var count int64
	r.db.Model(&model.User{}).Where("username = ?", username).Count(&count)
	return count > 0
}

func (r *UserRepository) Create(user *model.User) error {
	return r.db.Create(user).Error
}

func (r *UserRepository) Save(user *model.User) error {
	return r.db.Save(user).Error
}

func (r *UserRepository) Delete(id int64) error {
	// Clear associations first
	var user model.User
	user.ID = id
	r.db.Model(&user).Association("Roles").Clear()
	r.db.Model(&user).Association("Groups").Clear()
	return r.db.Delete(&model.User{}, id).Error
}

func (r *UserRepository) ExistsByID(id int64) bool {
	var count int64
	r.db.Model(&model.User{}).Where("id = ?", id).Count(&count)
	return count > 0
}

// ReplaceRoles clears and replaces all roles for a user.
func (r *UserRepository) ReplaceRoles(user *model.User, roles []model.Role) error {
	return r.db.Model(user).Association("Roles").Replace(roles)
}

// ReplaceGroups clears and replaces all groups for a user.
func (r *UserRepository) ReplaceGroups(user *model.User, groups []model.Group) error {
	return r.db.Model(user).Association("Groups").Replace(groups)
}

// AppendRole adds a role to a user.
func (r *UserRepository) AppendRole(user *model.User, role *model.Role) error {
	return r.db.Model(user).Association("Roles").Append(role)
}

// AppendGroup adds a group to a user.
func (r *UserRepository) AppendGroup(user *model.User, group *model.Group) error {
	return r.db.Model(user).Association("Groups").Append(group)
}
