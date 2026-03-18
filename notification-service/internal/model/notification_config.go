package model

// NotificationConfig maps to the notification_configs table.
type NotificationConfig struct {
	ID          int64  `json:"id" gorm:"primaryKey;autoIncrement"`
	Type        string `json:"type" gorm:"column:type;uniqueIndex;not null"`         // EMAIL, SMS
	Provider    string `json:"provider" gorm:"column:provider"`                       // SMTP, AFRICAS_TALKING
	Host        string `json:"host" gorm:"column:host"`
	Port        int    `json:"port" gorm:"column:port"`
	Username    string `json:"username" gorm:"column:username"`
	Password    string `json:"password" gorm:"column:password"`
	FromAddress string `json:"fromAddress" gorm:"column:from_address"`
	ApiKey      string `json:"apiKey" gorm:"column:api_key"`
	ApiSecret   string `json:"apiSecret" gorm:"column:api_secret"`
	SenderID    string `json:"senderId" gorm:"column:sender_id"`
	Enabled     bool   `json:"enabled" gorm:"column:enabled;not null;default:false"`
}

func (NotificationConfig) TableName() string {
	return "notification_configs"
}
