package dto

// MediaResponse mirrors the Java MediaResponse DTO returned by media-service.
type MediaResponse struct {
	ID               string `json:"id"`
	MediaType        string `json:"mediaType"`
	OriginalFilename string `json:"originalFilename"`
	ContentType      string `json:"contentType"`
	FileSize         int64  `json:"fileSize"`
	ServiceName      string `json:"serviceName"`
	Channel          string `json:"channel"`
}
