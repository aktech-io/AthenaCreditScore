FROM golang:1.22-alpine AS build
WORKDIR /src
COPY pkg/athena/ pkg/athena/
COPY user-service/go.mod user-service/go.sum user-service/
WORKDIR /src/user-service
RUN go mod download
COPY user-service/ .
RUN CGO_ENABLED=0 go build -o /app ./cmd/main.go

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata
COPY --from=build /app /app
COPY --from=build /src/user-service/migrations /migrations
EXPOSE 8081
ENTRYPOINT ["/app"]
