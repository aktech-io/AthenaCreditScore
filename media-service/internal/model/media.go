package model

import (
	"time"

	"github.com/google/uuid"
)

// Media category constants matching Java MediaCategory enum.
const (
	CategoryCustomerDocument = "CUSTOMER_DOCUMENT"
	CategoryUserProfile      = "USER_PROFILE"
	CategoryFinancial        = "FINANCIAL"
	CategorySystem           = "SYSTEM"
	CategoryOther            = "OTHER"
)

// Media type constants matching Java MediaType enum.
const (
	TypeIDFront        = "ID_FRONT"
	TypeIDBack         = "ID_BACK"
	TypePassport       = "PASSPORT"
	TypeSelfie         = "SELFIE"
	TypeProofOfAddress = "PROOF_OF_ADDRESS"
	TypeProfilePicture = "PROFILE_PICTURE"
	TypeSignature      = "SIGNATURE"
	TypeReceipt        = "RECEIPT"
	TypeInvoice        = "INVOICE"
	TypeContract       = "CONTRACT"
	TypeOther          = "OTHER"
)

// Media status constants matching Java MediaStatus enum.
const (
	StatusActive   = "ACTIVE"
	StatusArchived = "ARCHIVED"
	StatusDeleted  = "DELETED"
)

// ValidCategories for validation.
var ValidCategories = map[string]bool{
	CategoryCustomerDocument: true,
	CategoryUserProfile:      true,
	CategoryFinancial:        true,
	CategorySystem:           true,
	CategoryOther:            true,
}

// ValidMediaTypes for validation.
var ValidMediaTypes = map[string]bool{
	TypeIDFront:        true,
	TypeIDBack:         true,
	TypePassport:       true,
	TypeSelfie:         true,
	TypeProofOfAddress: true,
	TypeProfilePicture: true,
	TypeSignature:      true,
	TypeReceipt:        true,
	TypeInvoice:        true,
	TypeContract:       true,
	TypeOther:          true,
}

// ValidStatuses for validation.
var ValidStatuses = map[string]bool{
	StatusActive:   true,
	StatusArchived: true,
	StatusDeleted:  true,
}

// Media maps to the media_files table.
type Media struct {
	ID               uuid.UUID  `gorm:"type:uuid;primaryKey;default:gen_random_uuid()" json:"id"`
	ReferenceID      *uuid.UUID `gorm:"type:uuid" json:"referenceId,omitempty"`
	CustomerID       *int64     `gorm:"column:customer_id" json:"customerId,omitempty"`
	Category         string     `gorm:"column:category;not null" json:"category"`
	MediaType        string     `gorm:"column:media_type;not null" json:"mediaType"`
	OriginalFilename string     `gorm:"column:original_filename;not null" json:"originalFilename"`
	StoredFilename   string     `gorm:"column:stored_filename;not null" json:"storedFilename"`
	ContentType      string     `gorm:"column:content_type;not null" json:"contentType"`
	FileSize         *int64     `gorm:"column:file_size" json:"fileSize,omitempty"`
	UploadedBy       string     `gorm:"column:uploaded_by" json:"uploadedBy,omitempty"`
	ServiceName      string     `gorm:"column:service_name" json:"serviceName,omitempty"`
	Channel          string     `gorm:"column:channel" json:"channel,omitempty"`
	Tags             string     `gorm:"column:tags;size:500" json:"tags,omitempty"`
	Description      string     `gorm:"column:description;type:text" json:"description,omitempty"`
	IsPublic         bool       `gorm:"column:is_public;not null;default:false" json:"isPublic"`
	Thumbnail        string     `gorm:"column:thumbnail" json:"thumbnail,omitempty"`
	Status           string     `gorm:"column:status;not null;default:ACTIVE" json:"status"`
	CreatedAt        time.Time  `gorm:"column:created_at;autoCreateTime" json:"createdAt"`
}

// TableName overrides GORM default table name.
func (Media) TableName() string {
	return "media_files"
}

// PageResponse wraps a paginated list of media items.
type PageResponse struct {
	Content       []Media `json:"content"`
	TotalElements int64   `json:"totalElements"`
	TotalPages    int     `json:"totalPages"`
	Size          int     `json:"size"`
	Number        int     `json:"number"`
}
