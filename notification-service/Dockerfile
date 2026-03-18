FROM golang:1.22-alpine AS build
WORKDIR /src
COPY pkg/athena/ pkg/athena/
COPY notification-service/go.mod notification-service/go.sum notification-service/
WORKDIR /src/notification-service
RUN go mod download
COPY notification-service/ .
RUN CGO_ENABLED=0 go build -o /app ./cmd/main.go

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata
COPY --from=build /app /app
COPY --from=build /src/notification-service/migrations /migrations
EXPOSE 8085
ENTRYPOINT ["/app"]
