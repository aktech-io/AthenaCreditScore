FROM golang:1.22-alpine AS build
WORKDIR /src
COPY pkg/athena/ pkg/athena/
COPY media-service/go.mod media-service/go.sum media-service/
WORKDIR /src/media-service
RUN go mod download
COPY media-service/ .
RUN CGO_ENABLED=0 go build -o /server ./cmd/main.go

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata && mkdir -p /app/storage
COPY --from=build /server /server
COPY --from=build /src/media-service/migrations /migrations
EXPOSE 8083
ENTRYPOINT ["/server"]
