package seed

import (
	"github.com/athena/user-service/internal/model"
	"github.com/athena/user-service/internal/repository"
	"github.com/rs/zerolog/log"
)

// Initialize seeds roles, groups, and default password policy.
func Initialize(
	roleRepo *repository.RoleRepository,
	groupRepo *repository.GroupRepository,
	policyRepo *repository.PasswordPolicyRepository,
) {
	// Athena Credit Score roles
	createRoleIfNotFound(roleRepo, "USER", "Standard internal user")
	createRoleIfNotFound(roleRepo, "ADMIN", "Administrator with full access")
	createRoleIfNotFound(roleRepo, "ANALYST", "Credit analyst — view scores and reports")
	createRoleIfNotFound(roleRepo, "VIEWER", "Read-only access to dashboard")
	createRoleIfNotFound(roleRepo, "CREDIT_RISK", "Credit risk officer — model configuration")

	// Athena Credit Score groups
	createGroupIfNotFound(groupRepo, "ADMINISTRATORS", "System administrators")
	createGroupIfNotFound(groupRepo, "ANALYSTS", "Credit analysts team")
	createGroupIfNotFound(groupRepo, "CREDIT_RISK_TEAM", "Credit risk management team")

	// Default password policy
	if policyRepo.Count() == 0 {
		log.Info().Msg("Seeding default password policy")
		policy := &model.PasswordPolicy{
			MinLength:          8,
			RequireUppercase:   true,
			RequireLowercase:   true,
			RequireNumbers:     true,
			RequireSpecialChars: false,
			ExpirationDays:     90,
		}
		if err := policyRepo.Create(policy); err != nil {
			log.Error().Err(err).Msg("failed to seed password policy")
		}
	}
}

func createRoleIfNotFound(repo *repository.RoleRepository, name, description string) {
	if _, err := repo.FindByName(name); err != nil {
		log.Info().Str("role", name).Msg("Seeding role")
		role := &model.Role{Name: name, Description: description}
		if err := repo.Create(role); err != nil {
			log.Error().Err(err).Str("role", name).Msg("failed to seed role")
		}
	}
}

func createGroupIfNotFound(repo *repository.GroupRepository, name, description string) {
	if _, err := repo.FindByName(name); err != nil {
		log.Info().Str("group", name).Msg("Seeding group")
		group := &model.Group{Name: name, Description: description}
		if err := repo.Create(group); err != nil {
			log.Error().Err(err).Str("group", name).Msg("failed to seed group")
		}
	}
}
