#!/bin/sh
# Docker entrypoint script for Edison API server
# Handles database migrations and Prisma client generation before starting the server

set -e

echo "🚀 Starting Edison API Server..."

# Extract database host and port from DATABASE_URL
# Format: postgresql://user:pass@host:port/db
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

# Default to localhost:5432 if parsing fails
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

echo "⏳ Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."

# Wait for PostgreSQL to be ready
for i in $(seq 1 30); do
  if nc -z "$DB_HOST" "$DB_PORT" > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready!"
    break
  fi

  if [ "$i" -eq 30 ]; then
    echo "❌ PostgreSQL is not available after 30 seconds"
    exit 1
  fi

  echo "   Still waiting... ($i/30)"
  sleep 1
done

# Navigate to API package directory
cd /app/packages/api || cd /app

echo "🔧 Generating Prisma Client..."
# Generate Prisma client
if [ -f "node_modules/.bin/prisma" ]; then
  npx prisma generate
elif command -v pnpm > /dev/null 2>&1; then
  pnpm prisma generate
else
  echo "⚠️  Warning: Could not generate Prisma client"
fi

echo "🗄️  Running database migrations..."
# Run database migrations
if [ -f "node_modules/.bin/prisma" ]; then
  npx prisma migrate deploy
elif command -v pnpm > /dev/null 2>&1; then
  pnpm prisma migrate deploy
else
  echo "⚠️  Warning: Could not run migrations"
fi

echo "✨ Initialization complete!"
echo "🎯 Starting application..."
echo ""

# Return to app root
cd /app

# Execute the main command (passed as arguments to this script)
exec "$@"
