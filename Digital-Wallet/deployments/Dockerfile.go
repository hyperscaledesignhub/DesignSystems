FROM golang:1.21-alpine AS builder

# Accept service path as argument
ARG SERVICE_PATH

WORKDIR /app

# Install git for go modules
RUN apk add --no-cache git

# Copy go mod files
COPY ${SERVICE_PATH}/go.mod ${SERVICE_PATH}/go.sum ./
RUN go mod download

# Copy source code
COPY ${SERVICE_PATH}/ .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates
WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/main .

# Expose port
EXPOSE 9085

# Run the binary
CMD ["./main"]