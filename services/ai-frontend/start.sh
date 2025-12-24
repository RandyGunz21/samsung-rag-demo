#!/bin/sh
set -e

echo "🚀 Starting AI Frontend..."
echo "📍 Database URL: ${POSTGRES_URL:0:30}..." # Show partial URL for debugging

# Run database migrations
echo "⏳ Running database migrations..."
npx tsx lib/db/migrate.ts

if [ $? -eq 0 ]; then
  echo "✅ Migrations completed successfully"
else
  echo "❌ Migrations failed"
  exit 1
fi

# Start Next.js server
echo "🌐 Starting Next.js server..."
exec node server.js
