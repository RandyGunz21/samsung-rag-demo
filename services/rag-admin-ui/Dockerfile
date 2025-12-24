# RAG Admin UI - Next.js 14 Production Dockerfile
# Multi-stage build for optimal image size

# Stage 1: Builder - Install dependencies and build
FROM node:22-alpine AS builder
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install ALL dependencies (including dev dependencies for build)
# Use npm install since no package-lock.json exists
RUN npm install

# Copy all source files
COPY . .

# Accept build arguments for NEXT_PUBLIC_* variables
ARG NEXT_PUBLIC_RAG_SERVICE_URL
ARG NEXT_PUBLIC_TESTER_SERVICE_URL

# Set environment for build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
# Expose build args as environment variables for Next.js build
ENV NEXT_PUBLIC_RAG_SERVICE_URL=$NEXT_PUBLIC_RAG_SERVICE_URL
ENV NEXT_PUBLIC_TESTER_SERVICE_URL=$NEXT_PUBLIC_TESTER_SERVICE_URL

# Build Next.js application
RUN npm run build

# Stage 2: Runner - Production runtime
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy necessary files from builder
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Start Next.js server
CMD ["node", "server.js"]
