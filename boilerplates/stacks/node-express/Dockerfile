# Node/Express boilerplate — minimal production image.
#
# Build: docker build -t boilerplate/node-express:1.0 boilerplates/stacks/node-express
# Run:   docker run -p 3000:3000 boilerplate/node-express:1.0
#
# Multi-stage: build dependencies in builder, copy only runtime deps to final.
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
# Non-root user for security
RUN addgroup -g 1001 -S nodejs && adduser -S -u 1001 -G nodejs appuser
COPY --from=builder --chown=appuser:nodejs /app/node_modules ./node_modules
COPY --chown=appuser:nodejs . .
USER appuser
EXPOSE 3000
# Health check for k8s readiness/liveness
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:3000/healthz || exit 1
CMD ["node", "server.js"]