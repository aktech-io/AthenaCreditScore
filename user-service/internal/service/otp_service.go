package service

import (
	"crypto/rand"
	"errors"
	"fmt"
	"math/big"
	"time"

	"github.com/athena/user-service/internal/model"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

var (
	// ErrOTPInvalid covers wrong, expired, already-used, and never-issued codes.
	// Callers must not distinguish these to the client — the difference tells an
	// attacker whether a phone number is registered.
	ErrOTPInvalid = errors.New("invalid or expired otp")

	// ErrOTPThrottled means too many codes were requested for this phone.
	ErrOTPThrottled = errors.New("too many otp requests")
)

const (
	otpTTL          = 5 * time.Minute
	otpMaxAttempts  = 5
	otpMaxPerWindow = 3
	otpWindow       = 15 * time.Minute
)

// OTPService issues and verifies single-use sign-in codes for customers.
type OTPService struct {
	db *gorm.DB
}

func NewOTPService(db *gorm.DB) *OTPService {
	return &OTPService{db: db}
}

// Issue generates a code for phone, stores only its bcrypt hash, and returns the
// plaintext so the caller can deliver it. Any earlier unconsumed code for the same
// phone is invalidated, so only the newest one works.
func (s *OTPService) Issue(phone string) (string, error) {
	var recent int64
	if err := s.db.Model(&model.CustomerOTP{}).
		Where("phone = ? AND created_at > ?", phone, time.Now().Add(-otpWindow)).
		Count(&recent).Error; err != nil {
		return "", err
	}
	if recent >= otpMaxPerWindow {
		return "", ErrOTPThrottled
	}

	code, err := randomCode()
	if err != nil {
		return "", err
	}
	hash, err := bcrypt.GenerateFromPassword([]byte(code), bcrypt.DefaultCost)
	if err != nil {
		return "", err
	}

	now := time.Now()
	err = s.db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Model(&model.CustomerOTP{}).
			Where("phone = ? AND consumed_at IS NULL", phone).
			Update("consumed_at", now).Error; err != nil {
			return err
		}
		return tx.Create(&model.CustomerOTP{
			Phone:     phone,
			OTPHash:   string(hash),
			ExpiresAt: now.Add(otpTTL),
			CreatedAt: now,
		}).Error
	})
	if err != nil {
		return "", err
	}
	return code, nil
}

// Verify consumes the newest outstanding code for phone. A code is single-use:
// success marks it consumed, so a replay of the same code fails.
func (s *OTPService) Verify(phone, code string) error {
	var otp model.CustomerOTP
	err := s.db.Where("phone = ? AND consumed_at IS NULL", phone).
		Order("created_at DESC").
		First(&otp).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return ErrOTPInvalid
	}
	if err != nil {
		return err
	}

	if time.Now().After(otp.ExpiresAt) || otp.Attempts >= otpMaxAttempts {
		return ErrOTPInvalid
	}

	if bcrypt.CompareHashAndPassword([]byte(otp.OTPHash), []byte(code)) != nil {
		// Count the failure so a guessing loop burns through the attempt budget.
		s.db.Model(&model.CustomerOTP{}).
			Where("id = ?", otp.ID).
			Update("attempts", otp.Attempts+1)
		return ErrOTPInvalid
	}

	now := time.Now()
	return s.db.Model(&model.CustomerOTP{}).
		Where("id = ?", otp.ID).
		Update("consumed_at", now).Error
}

func randomCode() (string, error) {
	n, err := rand.Int(rand.Reader, big.NewInt(1000000))
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%06d", n.Int64()), nil
}
