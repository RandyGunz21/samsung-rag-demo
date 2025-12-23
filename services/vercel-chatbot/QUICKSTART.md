# Vercel AI Chatbot - Quick Start Guide

## 🚀 Quick Commands

### Start
```bash
docker-compose up -d vercel-chatbot
```

### Stop
```bash
docker-compose stop vercel-chatbot
```

### Restart
```bash
docker-compose restart vercel-chatbot
```

### View Logs
```bash
docker-compose logs -f vercel-chatbot
```

### Rebuild After Code Changes
```bash
docker-compose build vercel-chatbot && docker-compose up -d vercel-chatbot
```

### Full Restart (for env var changes)
```bash
docker-compose down && docker-compose up -d
```

## 🌐 Access

**Application URL**: http://localhost:3000

**Guest Login**: Automatic (no credentials needed)

## 🔍 Troubleshooting

### Check if Running
```bash
docker-compose ps | grep vercel-chatbot
```

### Check Environment
```bash
docker exec vercel-chatbot env | grep NODE_ENV
# Should show: NODE_ENV=development
```

### Test Page Load
```bash
curl -sL http://localhost:3000 | grep -o "<title>.*</title>"
# Should show: <title>Next.js Chatbot Template</title>
```

### Check Cookies
```bash
curl -sL -I http://localhost:3000/api/auth/guest | grep set-cookie
# Should see: set-cookie: authjs.session-token=...
```

## ⚠️ Common Issues

### Redirect Loop
**Symptom**: Browser keeps loading, never shows page
**Cause**: `NODE_ENV=production` on HTTP
**Fix**: Ensure `NODE_ENV=development` in docker-compose.yml

### Database Error
**Symptom**: Migration failed errors
**Cause**: PostgreSQL not running or database doesn't exist
**Fix**:
```bash
docker-compose ps postgres  # Check if running
docker exec rag-postgres psql -U aiuser -d postgres -c "\l"  # List databases
```

### Container Won't Start
**Symptom**: Container exits immediately
**Cause**: Build error or dependency issue
**Fix**:
```bash
docker-compose logs vercel-chatbot  # Check error
docker-compose build --no-cache vercel-chatbot  # Rebuild from scratch
```

## 📊 Health Check

**Quick Status Check**:
```bash
# All should return 200 or show content
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000  # Should be 307
curl -sL -o /dev/null -w "%{http_code}" http://localhost:3000  # Should be 200
docker-compose ps vercel-chatbot  # Should show "Up"
```

## 🔧 Configuration

**Key Environment Variables** (in docker-compose.yml):
```yaml
POSTGRES_URL: postgres://aiuser:aipassword123@postgres:5432/vercel_chatbot
AUTH_SECRET: da97c81767f3849ebf6141f18ee5cf1d
NODE_ENV: development  # REQUIRED for HTTP cookies
REDIS_URL: redis://redis:6379/1
RAG_BACKEND_URL: http://agent-service:8001
```

## 📝 Development Workflow

1. **Make Code Changes**: Edit files in `services/vercel-chatbot/`
2. **Hot Reload**: Changes auto-reload (dev mode)
3. **If Docker Changes**: Rebuild with `docker-compose build vercel-chatbot`
4. **Test**: Access http://localhost:3000
5. **Check Logs**: `docker-compose logs -f vercel-chatbot`

## 🎯 Success Indicators

✅ Container status: "Up (healthy)"
✅ Logs show: "✓ Ready in X.Xs"
✅ Page loads with title: "Next.js Chatbot Template"
✅ No infinite redirect loop
✅ Session cookies are set

## 📚 Related Documentation

- **SETUP_COMPLETE.md**: Full implementation details
- **README.md**: Comprehensive setup guide
- **.env.example**: Environment variable reference
- **Dockerfile**: Container configuration

## 🆘 Get Help

**View full implementation notes**:
```bash
cat services/vercel-chatbot/SETUP_COMPLETE.md
```

**Check session memory**:
```bash
cat .serena/memories/vercel_chatbot_implementation_2025-12-09.md
```
