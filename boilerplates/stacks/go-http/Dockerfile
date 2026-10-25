# Go HTTP boilerplate — minimal production image.
#
# Build: docker build -t boilerplate/go-http:1.0 boilerplates/stacks/go-http
# Run:   docker run -p 8080:8080 boilerplate/go-http:1.0
#
# Multi-stage: build in builder, copy static binary to scratch/distroless.
FROM golang:1.23-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /server ./main.go

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /
COPY --from=builder /server /server
ENV PORT=8080
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/server"]