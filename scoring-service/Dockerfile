FROM golang:1.22-alpine AS build
WORKDIR /src
COPY pkg/athena/ pkg/athena/
COPY scoring-service/go.mod scoring-service/go.sum scoring-service/
WORKDIR /src/scoring-service
RUN go mod download
COPY scoring-service/ .
RUN CGO_ENABLED=0 go build -o /app ./cmd/main.go

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata
COPY --from=build /app /app
EXPOSE 8080
ENTRYPOINT ["/app"]
