FROM golang:1.22-alpine AS build
WORKDIR /src
COPY pkg/athena/ pkg/athena/
COPY customer-service/go.mod customer-service/go.sum customer-service/
WORKDIR /src/customer-service
RUN go mod download
COPY customer-service/ .
RUN CGO_ENABLED=0 go build -o /app ./cmd/main.go

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata
COPY --from=build /app /app
COPY --from=build /src/customer-service/migrations /migrations
EXPOSE 8082
ENTRYPOINT ["/app"]
