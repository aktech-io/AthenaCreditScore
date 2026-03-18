package model

import "time"

// Invitation maps to the invitations table.
type Invitation struct {
	ID         int64     `gorm:"primaryKey;autoIncrement" json:"id"`
	Token      string    `gorm:"uniqueIndex;not null" json:"token"`
	Email      string    `gorm:"not null" json:"email"`
	ExpiryDate time.Time `gorm:"column:expiry_date;not null" json:"expiryDate"`
	Used       bool      `gorm:"not null;default:false" json:"used"`
	Roles      []Role    `gorm:"many2many:invitation_roles" json:"roles"`
	Groups     []Group   `gorm:"many2many:invitation_groups" json:"groups"`
}

func (Invitation) TableName() string { return "invitations" }
