package model

// Group maps to the user_groups table.
type Group struct {
	ID          int64  `gorm:"primaryKey;autoIncrement" json:"id"`
	Name        string `gorm:"uniqueIndex;not null" json:"name"`
	Description string `json:"description"`
	Roles       []Role `gorm:"many2many:group_roles" json:"roles"`
}

func (Group) TableName() string { return "user_groups" }
