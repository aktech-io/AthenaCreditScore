package model

// AdminUser maps to the admin_users table.
// Uses password_hash column (bcrypt), separate from the users table.
type AdminUser struct {
	ID           int64  `gorm:"primaryKey;autoIncrement" json:"id"`
	Username     string `gorm:"uniqueIndex;not null" json:"username"`
	PasswordHash string `gorm:"column:password_hash;not null" json:"-"`
	FirstName    string `gorm:"column:first_name" json:"firstName"`
	LastName     string `gorm:"column:last_name" json:"lastName"`
	Email        string `json:"email"`
	Role         string `gorm:"not null" json:"role"`
	TotpSecret   string `gorm:"column:totp_secret" json:"-"`
	Active       bool   `gorm:"column:is_active;not null;default:true" json:"active"`
}

func (AdminUser) TableName() string { return "admin_users" }
