# Vercel AI Chatbot - Dockerized Setup

This is a containerized version of the [Vercel AI Chatbot](https://github.com/vercel/ai-chatbot) that clones the official repository and runs it in Docker following the official setup instructions.

## What This Container Does

1. **Clones** the official Vercel AI chatbot repository from GitHub
2. **Installs** dependencies using pnpm (as specified in the official README)
3. **Builds** the Next.js application
4. **Runs** the application in production mode
5. **Integrates** with the RAG system backend services

## Architecture

The container follows a multi-stage build process:

- **Base Stage**: Clones repo, installs system dependencies and pnpm
- **Builder Stage**: Installs Node dependencies and builds the application
- **Runner Stage**: Minimal production image with only necessary files

## Environment Variables

Required environment variables (configured in docker-compose.yml):

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_URL` | PostgreSQL connection string | `postgres://aiuser:aipassword123@postgres:5432/ai_chatbot` |
| `AUTH_SECRET` | NextAuth session encryption key | Generated value |
| `AUTH_TRUST_HOST` | Trust proxy headers | `true` |
| `RAG_BACKEND_URL` | RAG agent service URL | `http://agent-service:8001` |
| `REDIS_URL` | Redis for resumable streams (optional) | `redis://redis:6379/0` |
| `NEXT_TELEMETRY_DISABLED` | Disable Vercel telemetry | `1` |

## Running the Container

### Via Docker Compose (Recommended)

From the project root:
```bash
cd /mnt/c/Users/rangunaw/Documents/rag-demo
docker-compose -f services/docker-compose.yml up vercel-chatbot -d
```

From the services directory:
```bash
cd services
docker-compose up vercel-chatbot -d
```

### Build Only
```bash
docker-compose -f services/docker-compose.yml build vercel-chatbot
```

### View Logs
```bash
docker-compose -f services/docker-compose.yml logs -f vercel-chatbot
```

### Stop Container
```bash
docker-compose -f services/docker-compose.yml down vercel-chatbot
```

## Accessing the Application

Once running, the chatbot will be available at:
- **URL**: http://localhost:3100
- **Port**: 3100 (external), 3000 (internal)

## Integration with RAG System

The chatbot integrates with the RAG demo backend services:

- **Agent Service**: AI orchestration at `http://agent-service:8001`
- **PostgreSQL**: Chat history and user data at `postgres:5432`
- **Redis**: Optional resumable streams at `redis:6379`

## Database Setup

The container depends on PostgreSQL being healthy before starting. Database migrations run automatically during the build process.

## Health Checks

The container includes a health check that:
- Runs every 30 seconds
- Checks if the Next.js server is responding on port 3000
- Allows 60 seconds for initial startup
- Retries 3 times before marking unhealthy

## Differences from Official Setup

This Docker setup differs from the official Vercel deployment:

1. **No Vercel CLI**: Doesn't use `vercel link` or `vercel env pull`
2. **Environment Variables**: Set directly in docker-compose.yml
3. **Database**: Uses self-hosted PostgreSQL instead of Vercel Postgres
4. **Storage**: Uses self-hosted solutions instead of Vercel Blob
5. **AI Models**: Can be configured to use local models via RAG backend

## Troubleshooting

### Container won't start
- Check PostgreSQL is running: `docker-compose -f services/docker-compose.yml ps postgres`
- Verify environment variables are set correctly in docker-compose.yml
- Check logs: `docker-compose -f services/docker-compose.yml logs vercel-chatbot`

### Database connection errors
- Ensure `POSTGRES_URL` is correctly formatted
- Verify PostgreSQL container is healthy
- Check network connectivity between containers

### Build failures
- Ensure Git is accessible (clone step)
- Check Node.js version compatibility (requires Node 20+)
- Verify pnpm installation succeeded

## Official Documentation

For more information about the Vercel AI Chatbot, see:
- **GitHub**: https://github.com/vercel/ai-chatbot
- **Vercel AI SDK**: https://sdk.vercel.ai/docs

## License

This Docker configuration follows the same license as the original Vercel AI Chatbot project.
