package model

// User maps to the users table.
// Uses password column (bcrypt), separate from admin_users.
type User struct {
	ID        int64   `gorm:"primaryKey;autoIncrement" json:"id"`
	Username  string  `gorm:"uniqueIndex;not null" json:"username"`
	Password  string  `gorm:"not null" json:"-"`
	FirstName string  `gorm:"column:first_name" json:"firstName"`
	LastName  string  `gorm:"column:last_name" json:"lastName"`
	Email     string  `json:"email"`
	Status    string  `gorm:"not null;default:ACTIVE" json:"status"` // ACTIVE, PENDING, DISABLED
	Roles     []Role  `gorm:"many2many:user_roles" json:"roles"`
	Groups    []Group `gorm:"many2many:user_group_members" json:"groups"`
}

func (User) TableName() string { return "users" }
