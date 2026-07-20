package model

import "time"

// CustomerOTP maps to the customer_otps table.
// Stores only the bcrypt hash of a one-time code, never the code itself.
type CustomerOTP struct {
	ID         int64      `gorm:"primaryKey;autoIncrement" json:"id"`
	Phone      string     `gorm:"not null" json:"phone"`
	OTPHash    string     `gorm:"column:otp_hash;not null" json:"-"`
	ExpiresAt  time.Time  `gorm:"column:expires_at;not null" json:"expiresAt"`
	Attempts   int        `gorm:"not null;default:0" json:"attempts"`
	ConsumedAt *time.Time `gorm:"column:consumed_at" json:"consumedAt,omitempty"`
	CreatedAt  time.Time  `gorm:"column:created_at;not null" json:"createdAt"`
}

func (CustomerOTP) TableName() string { return "customer_otps" }
