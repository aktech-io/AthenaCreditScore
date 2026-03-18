package dto

// CustomerRequest mirrors the Java CustomerRequest DTO.
type CustomerRequest struct {
	FirstName           string  `json:"firstName"`
	LastName            string  `json:"lastName"`
	MobileNumber        string  `json:"mobileNumber"`
	Email               string  `json:"email,omitempty"`
	NationalID          string  `json:"nationalId"`
	DateOfBirth         *string `json:"dateOfBirth,omitempty"` // YYYY-MM-DD
	Gender              string  `json:"gender,omitempty"`      // MALE, FEMALE
	County              string  `json:"county,omitempty"`
	Region              string  `json:"region,omitempty"`
	BankName            string  `json:"bankName,omitempty"`
	AccountNumber       string  `json:"accountNumber,omitempty"`
	RegistrationChannel string  `json:"registrationChannel,omitempty"` // WEB_APP, MOBILE_APP, ADMIN_PORTAL, PARTNER_API
}
