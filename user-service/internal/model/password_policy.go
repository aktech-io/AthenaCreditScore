package model

// PasswordPolicy maps to the password_policies table.
type PasswordPolicy struct {
	ID                 int64  `gorm:"primaryKey;autoIncrement" json:"id"`
	MinLength          int    `gorm:"column:min_length;not null;default:8" json:"minLength"`
	RequireUppercase   bool   `gorm:"column:require_uppercase;not null;default:true" json:"requireUppercase"`
	RequireLowercase   bool   `gorm:"column:require_lowercase;not null;default:true" json:"requireLowercase"`
	RequireNumbers     bool   `gorm:"column:require_numbers;not null;default:true" json:"requireNumbers"`
	RequireSpecialChars bool  `gorm:"column:require_special_chars;not null;default:false" json:"requireSpecialChars"`
	ExpirationDays     int    `gorm:"column:expiration_days;not null;default:90" json:"expirationDays"`
	SpecialChars       string `gorm:"column:special_chars" json:"specialChars"`
}

func (PasswordPolicy) TableName() string { return "password_policies" }
