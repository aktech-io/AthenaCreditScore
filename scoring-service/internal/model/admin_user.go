package model

type AdminUser struct {
	ID           int64  `gorm:"column:id;primaryKey;autoIncrement" json:"id"`
	Username     string `gorm:"column:username;uniqueIndex;not null" json:"username"`
	PasswordHash string `gorm:"column:password_hash;not null" json:"-"`
	FirstName    string `gorm:"column:first_name" json:"first_name"`
	LastName     string `gorm:"column:last_name" json:"last_name"`
	Email        string `gorm:"column:email" json:"email"`
	Role         string `gorm:"column:role;not null" json:"role"`
	TotpSecret   string `gorm:"column:totp_secret" json:"-"`
	Active       bool   `gorm:"column:is_active;not null;default:true" json:"active"`
}

func (AdminUser) TableName() string {
	return "admin_users"
}
