package service

import (
	"fmt"
	"regexp"

	"github.com/athena/user-service/internal/model"
	"github.com/athena/user-service/internal/repository"
)

type PasswordPolicyService struct {
	repo *repository.PasswordPolicyRepository
}

func NewPasswordPolicyService(repo *repository.PasswordPolicyRepository) *PasswordPolicyService {
	return &PasswordPolicyService{repo: repo}
}

// ValidatePassword validates a password against the current policy.
// Returns nil if no policy is configured.
func (s *PasswordPolicyService) ValidatePassword(password string) error {
	policy, err := s.repo.FindFirst()
	if err != nil {
		// No policy configured — allow any password
		return nil
	}

	if len(password) < policy.MinLength {
		return fmt.Errorf("Password must be at least %d characters long", policy.MinLength)
	}
	if policy.RequireUppercase {
		if matched, _ := regexp.MatchString(`[A-Z]`, password); !matched {
			return fmt.Errorf("Password must contain at least one uppercase letter")
		}
	}
	if policy.RequireLowercase {
		if matched, _ := regexp.MatchString(`[a-z]`, password); !matched {
			return fmt.Errorf("Password must contain at least one lowercase letter")
		}
	}
	if policy.RequireNumbers {
		if matched, _ := regexp.MatchString(`[0-9]`, password); !matched {
			return fmt.Errorf("Password must contain at least one number")
		}
	}
	if policy.RequireSpecialChars {
		specialPattern := `[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?]`
		if policy.SpecialChars != "" {
			specialPattern = "[" + regexp.QuoteMeta(policy.SpecialChars) + "]"
		}
		if matched, _ := regexp.MatchString(specialPattern, password); !matched {
			return fmt.Errorf("Password must contain at least one special character")
		}
	}
	return nil
}

// GetCurrentPolicy returns the current password policy.
func (s *PasswordPolicyService) GetCurrentPolicy() (*model.PasswordPolicy, error) {
	policy, err := s.repo.FindFirst()
	if err != nil {
		return nil, fmt.Errorf("No password policy configured")
	}
	return policy, nil
}

// UpdatePolicy updates the current password policy, or creates one if none exists.
func (s *PasswordPolicyService) UpdatePolicy(newPolicy *model.PasswordPolicy) (*model.PasswordPolicy, error) {
	existing, err := s.repo.FindFirst()
	if err != nil {
		// No existing policy — create one
		existing = &model.PasswordPolicy{}
	}
	existing.MinLength = newPolicy.MinLength
	existing.RequireUppercase = newPolicy.RequireUppercase
	existing.RequireLowercase = newPolicy.RequireLowercase
	existing.RequireNumbers = newPolicy.RequireNumbers
	existing.RequireSpecialChars = newPolicy.RequireSpecialChars
	existing.ExpirationDays = newPolicy.ExpirationDays
	existing.SpecialChars = newPolicy.SpecialChars

	if err := s.repo.Save(existing); err != nil {
		return nil, err
	}
	return existing, nil
}
