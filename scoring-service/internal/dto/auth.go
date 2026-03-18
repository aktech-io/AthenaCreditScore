package dto

type AuthRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
	TotpCode string `json:"totpCode,omitempty"`
}

type AuthResponse struct {
	Token      string   `json:"token"`
	Username   string   `json:"username,omitempty"`
	FirstName  string   `json:"firstName,omitempty"`
	LastName   string   `json:"lastName,omitempty"`
	Email      string   `json:"email,omitempty"`
	Roles      []string `json:"roles"`
	CustomerID *int64   `json:"customerId,omitempty"`
}
