package model

import "time"

// NotificationLog maps to the notification_logs table.
type NotificationLog struct {
	ID           int64     `json:"id" gorm:"primaryKey;autoIncrement"`
	ServiceName  string    `json:"serviceName" gorm:"column:service_name;not null"`
	Type         string    `json:"type" gorm:"column:type;not null"`     // EMAIL, SMS
	Recipient    string    `json:"recipient" gorm:"column:recipient;not null"`
	Subject      string    `json:"subject" gorm:"column:subject"`
	Body         string    `json:"body" gorm:"column:body;type:text"`
	Status       string    `json:"status" gorm:"column:status;not null"` // SENT, FAILED, SKIPPED
	ErrorMessage string    `json:"errorMessage" gorm:"column:error_message;type:text"`
	SentAt       time.Time `json:"sentAt" gorm:"column:sent_at;autoCreateTime"`
}

func (NotificationLog) TableName() string {
	return "notification_logs"
}
