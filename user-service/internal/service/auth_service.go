package service

import (
	"fmt"

	"github.com/athena/pkg/jwt"
	"github.com/athena/user-service/internal/dto"
	"github.com/athena/user-service/internal/repository"
	"golang.org/x/crypto/bcrypt"
)

type AuthService struct {
	userRepo      *repository.UserRepository
	roleRepo      *repository.RoleRepository
	jwtUtil       *jwt.JWTUtil
	policyService *PasswordPolicyService
}

func NewAuthService(
	userRepo *repository.UserRepository,
	roleRepo *repository.RoleRepository,
	jwtUtil *jwt.JWTUtil,
	policyService *PasswordPolicyService,
) *AuthService {
	return &AuthService{
		userRepo:      userRepo,
		roleRepo:      roleRepo,
		jwtUtil:       jwtUtil,
		policyService: policyService,
	}
}

// Authenticate validates credentials against the users table and returns a JWT.
func (s *AuthService) Authenticate(req dto.AuthRequest) (*dto.AuthResponse, error) {
	user, err := s.userRepo.FindByUsername(req.Username)
	if err != nil {
		return nil, fmt.Errorf("Invalid credentials")
	}

	if err := bcrypt.CompareHashAndPassword([]byte(user.Password), []byte(req.Password)); err != nil {
		return nil, fmt.Errorf("Invalid credentials")
	}

	roles := make([]string, 0, len(user.Roles))
	for _, r := range user.Roles {
		roles = append(roles, r.Name)
	}
	groups := make([]string, 0, len(user.Groups))
	for _, g := range user.Groups {
		groups = append(groups, g.Name)
	}

	token, err := s.jwtUtil.GenerateToken(user.Username, roles, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to generate token: %w", err)
	}

	return &dto.AuthResponse{
		Token:     token,
		Username:  user.Username,
		FirstName: user.FirstName,
		LastName:  user.LastName,
		Email:     user.Email,
		Roles:     roles,
		Groups:    groups,
	}, nil
}
