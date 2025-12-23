# Vercel AI Chatbot - Development Setup
# Runs the application in development mode with hot reload

FROM node:22-alpine

# Install system dependencies
RUN apk add --no-cache git curl bash

# Install pnpm globally via npm (more reliable than corepack in Docker)
RUN npm install -g pnpm@9.12.3

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Install dependencies
RUN pnpm install

# Expose port 3000
EXPOSE 3000

# Create startup script that runs migrations then starts dev server
RUN printf '#!/bin/sh\nset -e\necho "Running database migrations..."\npnpm db:migrate\necho "Starting development server..."\nexec pnpm dev\n' > /app/start.sh && \
    chmod +x /app/start.sh

# Start with migrations + dev server
CMD ["/bin/sh", "/app/start.sh"]
