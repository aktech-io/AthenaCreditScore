package model

// Role maps to the roles table.
type Role struct {
	ID          int64  `gorm:"primaryKey;autoIncrement" json:"id"`
	Name        string `gorm:"uniqueIndex;not null" json:"name"`
	Description string `json:"description"`
}

func (Role) TableName() string { return "roles" }
