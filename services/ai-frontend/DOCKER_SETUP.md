# Docker Setup for Vercel AI Chatbot (RAG Demo)

## Overview
This Docker setup is based on the official Vercel AI Chatbot template, configured for self-hosted deployment with the RAG backend.

## Architecture
- **Frontend**: Next.js 16 with Vercel AI SDK
- **Database**: PostgreSQL for chat history and users
- **Cache**: Redis for resumable streams (optional)
- **AI Provider**: Connected to agent-service (RAG backend)

## Environment Variables

### Required
```env
# Authentication (generate with: openssl rand -base64 32)
AUTH_SECRET=your-secret-key-here
AUTH_TRUST_HOST=true

# Database
POSTGRES_URL=postgres://aiuser:aipassword123@postgres:5432/ai_chatbot

# RAG Backend
RAG_BACKEND_URL=http://agent-service:8001

# Optional: Redis for resumable streams
REDIS_URL=redis://redis:6379/0
```

### Optional (for Vercel features)
```env
# AI Gateway (not needed when using RAG backend)
# AI_GATEWAY_API_KEY=

# Vercel Blob Storage (for file uploads)
# BLOB_READ_WRITE_TOKEN=
```

## Build & Run

### Using Docker Compose
```bash
# Build the frontend
docker-compose build frontend

# Start all services
docker-compose up -d

# Check logs
docker logs frontend -f
```

### Standalone Docker
```bash
# Build
docker build -t ai-frontend ./ai-frontend

# Run
docker run -p 3000:3000 \
  -e AUTH_SECRET="your-secret" \
  -e POSTGRES_URL="postgres://..." \
  -e RAG_BACKEND_URL="http://agent-service:8001" \
  ai-frontend
```

## Database Setup

The database is automatically initialized when the frontend starts. Tables created:
- `User` - User accounts (guest and registered)
- `Chat` - Chat conversations
- `MessagePart` - Chat messages
- `Document` - Generated documents/artifacts
- `Suggestion` - Chat suggestions
- `Vote` - Message votes

## Troubleshooting

### Infinite Redirect Loop
If you encounter infinite redirects at the root URL:
1. Ensure `AUTH_SECRET` is set correctly
2. Check that `AUTH_TRUST_HOST=true` is set
3. Verify PostgreSQL is accessible and initialized
4. Check cookie settings (secure cookies disabled for HTTP)

### Database Connection Errors
```bash
# Check PostgreSQL is running
docker exec rag-postgres psql -U aiuser -d ai_chatbot -c "SELECT 1;"

# Verify connection string
echo $POSTGRES_URL
```

### Port Conflicts
If port 3000 is already in use:
```yaml
# In docker-compose.yml, change:
ports:
  - "3001:3000"  # Use 3001 instead
```

## Production Considerations

1. **HTTPS**: Enable secure cookies when using HTTPS
2. **Environment**: Set `NODE_ENV=production`
3. **Secrets**: Use secure secret management (not env files)
4. **Database**: Use managed PostgreSQL with backups
5. **Monitoring**: Add health checks and logging

## Authentication

This setup uses NextAuth with:
- **Guest Mode**: Automatic guest user creation
- **Credentials**: Email/password authentication (optional)
- **Sessions**: JWT-based sessions stored in cookies

For production, consider adding:
- OAuth providers (Google, GitHub, etc.)
- Two-factor authentication
- Rate limiting
- Session management

## API Integration

The chatbot connects to your RAG backend at `RAG_BACKEND_URL`:
- Chat completions: `POST /api/chat`
- Streaming: SSE-based streaming responses
- Context: Automatic conversation history management

## Files Structure

```
ai-frontend/
├── Dockerfile              # Multi-stage build
├── docker-compose.yml      # Service orchestration
├── next.config.ts          # Next.js configuration
├── app/
│   ├── (auth)/            # Authentication routes
│   ├── (chat)/            # Chat interface
│   └── api/               # API routes
├── components/            # React components
├── lib/
│   ├── ai/               # AI SDK integration
│   └── db/               # Database queries
└── proxy.ts              # Middleware (disabled for open access)
```

## Next Steps

1. Configure your AI model provider
2. Customize the UI theme and branding
3. Add custom tools and functions
4. Set up monitoring and analytics
5. Configure backup and disaster recovery
