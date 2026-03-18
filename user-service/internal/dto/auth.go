package dto

// AuthRequest is the login request body.
type AuthRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

// AuthResponse is the login/register response.
type AuthResponse struct {
	Token      string   `json:"token"`
	Username   string   `json:"username"`
	FirstName  string   `json:"firstName,omitempty"`
	LastName   string   `json:"lastName,omitempty"`
	Email      string   `json:"email,omitempty"`
	Roles      []string `json:"roles"`
	Groups     []string `json:"groups,omitempty"`
	CustomerID *int64   `json:"customerId,omitempty"`
}

// PortalLoginResponse is the unified login response for the portal.
type PortalLoginResponse struct {
	Token string   `json:"token"`
	User  UserInfo `json:"user"`
}

// UserInfo is nested user info inside PortalLoginResponse.
type UserInfo struct {
	ID         string `json:"id"`
	Email      string `json:"email"`
	FirstName  string `json:"firstName"`
	LastName   string `json:"lastName"`
	Role       string `json:"role"`
	CustomerID string `json:"customerId,omitempty"`
	MerchantID string `json:"merchantId,omitempty"`
}

// CreateUserRequest is the request body for creating an internal user.
type CreateUserRequest struct {
	Username  string   `json:"username"`
	Password  string   `json:"password"`
	FirstName string   `json:"firstName"`
	LastName  string   `json:"lastName"`
	Email     string   `json:"email"`
	Roles     []string `json:"roles"`
	Groups    []string `json:"groups"`
}

// UpdateUserRequest is the request body for updating an internal user.
type UpdateUserRequest struct {
	Password  *string  `json:"password"`
	FirstName *string  `json:"firstName"`
	LastName  *string  `json:"lastName"`
	Email     *string  `json:"email"`
	Roles     []string `json:"roles"`
	Groups    []string `json:"groups"`
}

// CompleteRegistrationRequest is the request body for completing registration.
type CompleteRegistrationRequest struct {
	Token     string `json:"token" binding:"required"`
	FirstName string `json:"firstName"`
	LastName  string `json:"lastName"`
	Password  string `json:"password" binding:"required"`
}
