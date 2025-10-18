# Edison Docker Setup

This guide explains how to run Edison using Docker for local development and production deployment.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 20.10 or later)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0 or later)

## Quick Start

### Development Mode

1. **Copy the environment template:**
   ```bash
   cp .env.docker.example .env
   ```

2. **Edit `.env` and add your API keys:**
   ```bash
   # At minimum, set these values:
   OPENAI_API_KEY=sk-your-key-here
   ANTHROPIC_API_KEY=sk-ant-your-key-here

   # Generate secure secrets:
   JWT_SECRET=$(openssl rand -hex 32)
   ENCRYPTION_KEY=$(openssl rand -hex 32)
   ```

3. **Start all services:**
   ```bash
   docker-compose up
   ```

4. **Access the application:**
   - Web UI: [http://localhost:3000](http://localhost:3000)
   - API: [http://localhost:8080](http://localhost:8080)
   - API Health: [http://localhost:8080/healthz](http://localhost:8080/healthz)

### Production Mode

1. **Set up production environment:**
   ```bash
   cp .env.docker.example .env
   # Edit .env with production values and strong secrets
   ```

2. **Build and start production services:**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

3. **Monitor logs:**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

## Architecture

The Docker setup consists of four services:

### Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `postgres` | `postgres:18-alpine` | 5432 | PostgreSQL database |
| `redis` | `redis:7.4-alpine` | 6379 | Redis cache & job queue |
| `api` | Custom build | 8080 | Hono + tRPC API server |
| `web` | Custom build | 3000 | Next.js web application |

### Technology Versions

- **Node.js**: 22.20.0 (LTS)
- **pnpm**: 10.18.3 (latest)
- **PostgreSQL**: 18 (latest stable)
- **Redis**: 7.4 (latest stable)

## Docker Commands

### Development

```bash
# Start all services
docker-compose up

# Start in detached mode (background)
docker-compose up -d

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes all data)
docker-compose down -v

# Rebuild images
docker-compose build

# Rebuild specific service
docker-compose build api

# Restart a service
docker-compose restart api

# Execute command in running container
docker-compose exec api sh
docker-compose exec web sh

# Run database migrations manually
docker-compose exec api pnpm --filter @edison/api prisma migrate deploy

# Access PostgreSQL CLI
docker-compose exec postgres psql -U edison -d edison

# Access Redis CLI
docker-compose exec redis redis-cli
```

### Production

```bash
# Build and start
docker-compose -f docker-compose.prod.yml up --build -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Scale API workers (if needed)
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

## Development Workflow

### Hot Reload

Both the API and web services support hot-reload in development mode:

- **API**: Uses `tsx watch` to restart on file changes
- **Web**: Uses Next.js dev server with Fast Refresh

Your local code is mounted into the containers, so changes are reflected immediately.

### Adding Dependencies

When you add new npm packages:

```bash
# Option 1: Restart the service to reinstall
docker-compose restart api

# Option 2: Install inside the container
docker-compose exec api pnpm --filter @edison/api add package-name

# Option 3: Rebuild the container
docker-compose build api && docker-compose up -d api
```

### Database Migrations

```bash
# Create a new migration
docker-compose exec api sh -c "cd packages/api && pnpm prisma migrate dev --name add_feature"

# Apply migrations
docker-compose exec api pnpm --filter @edison/api prisma migrate deploy

# Reset database (⚠️ deletes all data)
docker-compose exec api pnpm --filter @edison/api prisma migrate reset

# Open Prisma Studio
docker-compose exec api pnpm --filter @edison/api prisma studio
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `JWT_SECRET` | JWT signing secret (≥32 chars) | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | AES encryption key (64 chars hex) | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | Database password | `strong-password-123` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `REDIS_PORT` | Redis port | `6379` |
| `API_PORT` | API server port | `8080` |
| `WEB_PORT` | Web application port | `3000` |
| `LOG_LEVEL` | Logging level | `debug` (dev), `info` (prod) |
| `OPENAI_API_KEY` | OpenAI API key | (optional) |
| `ANTHROPIC_API_KEY` | Anthropic API key | (optional) |

## Troubleshooting

### Containers won't start

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs

# Check for port conflicts
lsof -i :3000
lsof -i :8080
lsof -i :5432
lsof -i :6379
```

### Database connection errors

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U edison -d edison -c "SELECT 1;"
```

### API not responding

```bash
# Check API logs
docker-compose logs api

# Verify migrations ran
docker-compose exec api pnpm --filter @edison/api prisma migrate status

# Restart API service
docker-compose restart api
```

### Clear all data and start fresh

```bash
# ⚠️ WARNING: This deletes all data
docker-compose down -v
docker-compose up
```

### Permission errors

If you encounter permission errors with volumes:

```bash
# Reset ownership (Linux/macOS)
sudo chown -R $USER:$USER .

# Or remove volumes and recreate
docker-compose down -v
docker-compose up
```

## Production Deployment

### Recommended Steps

1. **Use strong secrets:**
   ```bash
   export JWT_SECRET=$(openssl rand -hex 32)
   export ENCRYPTION_KEY=$(openssl rand -hex 32)
   export POSTGRES_PASSWORD=$(openssl rand -base64 32)
   ```

2. **Configure logging:**
   ```bash
   LOG_LEVEL=info  # or 'warn' for less verbosity
   ```

3. **Set up reverse proxy:**
   - Use nginx or Traefik to handle SSL/TLS
   - Configure domain names and certificates
   - Set up rate limiting and security headers

4. **Configure backups:**
   ```bash
   # Backup PostgreSQL
   docker-compose -f docker-compose.prod.yml exec postgres \
     pg_dump -U edison edison > backup-$(date +%Y%m%d).sql

   # Restore from backup
   docker-compose -f docker-compose.prod.yml exec -T postgres \
     psql -U edison edison < backup.sql
   ```

5. **Monitor resources:**
   ```bash
   # View resource usage
   docker stats

   # Check service health
   docker-compose -f docker-compose.prod.yml ps
   ```

### Security Considerations

- Never commit `.env` files with real credentials
- Use Docker secrets for sensitive data in production
- Enable firewall rules to restrict database/redis access
- Regularly update base images for security patches
- Use HTTPS/TLS for all external connections
- Implement rate limiting at the reverse proxy level
- Set up monitoring and alerting

## Advanced Configuration

### Custom Network

```yaml
# docker-compose.override.yml
networks:
  edison-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### Persistent Data Location

By default, Docker volumes store data in `/var/lib/docker/volumes/`. To use a custom location:

```yaml
volumes:
  postgres-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/postgres/data
```

### Resource Limits

Adjust limits in `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

## Performance Tuning

### PostgreSQL

Edit postgres service:
```yaml
environment:
  POSTGRES_SHARED_BUFFERS: 256MB
  POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
  POSTGRES_WORK_MEM: 16MB
```

### Redis

Adjust memory limits:
```yaml
command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

## Support

For issues or questions:
- Check the main [README.md](./README.md)
- Review Docker Compose logs
- Check service health endpoints
- Consult the Edison documentation

## License

MIT
