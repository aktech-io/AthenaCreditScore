package dto

// PageResponse is a generic paginated response wrapper.
type PageResponse struct {
	Content       interface{} `json:"content"`
	PageNumber    int         `json:"pageNumber"`
	PageSize      int         `json:"pageSize"`
	TotalElements int64       `json:"totalElements"`
	TotalPages    int         `json:"totalPages"`
	Last          bool        `json:"last"`
}
