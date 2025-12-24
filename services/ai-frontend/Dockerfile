# Multi-stage build for Next.js AI Chatbot
FROM node:22-alpine AS base

# Install pnpm
RUN npm install -g pnpm@9.12.3

# Stage 1: Dependencies
FROM base AS deps
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

# Stage 2: Builder
FROM base AS builder
WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set build-time environment variables
ARG RAG_BACKEND_URL
ARG AUTH_SECRET
ARG POSTGRES_URL

ENV NEXT_TELEMETRY_DISABLED=1
ENV RAG_BACKEND_URL=${RAG_BACKEND_URL}
ENV AUTH_SECRET=${AUTH_SECRET}
ENV POSTGRES_URL=${POSTGRES_URL}

# Build the Next.js application (skip migrations for Docker)
RUN pnpm build:docker

# Stage 3: Runner
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy migration files and dependencies for runtime migration
COPY --from=builder --chown=nextjs:nodejs /app/lib/db ./lib/db
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules

# Copy startup script
COPY --chown=nextjs:nodejs start.sh ./start.sh
RUN chmod +x ./start.sh

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Start the application with migrations
CMD ["./start.sh"]
