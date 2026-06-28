# SlopeSense — Production Deployment Guide

This guide covers deploying SlopeSense to a production Linux server using Docker Compose with PostgreSQL + PostGIS, SSL termination via Nginx, and a Celery scheduler for the 6-hour model pipeline.

---

## Table of Contents

1. [Server Requirements](#1-server-requirements)
2. [Environment Configuration](#2-environment-configuration)
3. [Database Setup](#3-database-setup)
4. [SSL / TLS Configuration](#4-ssl--tls-configuration)
5. [Deployment Steps](#5-deployment-steps)
6. [Post-Deployment Verification](#6-post-deployment-verification)
7. [Monitoring and Observability](#7-monitoring-and-observability)
8. [Backup Strategy](#8-backup-strategy)
9. [Scaling Considerations](#9-scaling-considerations)
10. [Rollback Procedure](#10-rollback-procedure)

---

## 1. Server Requirements

### Minimum (pilot / demo)

| Resource | Minimum |
|----------|---------|
| CPU | 4 vCPUs |
| RAM | 8 GB |
| Storage | 100 GB SSD (data cache grows ~5 GB/month) |
| Network | 100 Mbps outbound (satellite data downloads) |
| OS | Ubuntu 22.04 LTS |

### Recommended (production India-wide)

| Resource | Recommended |
|----------|------------|
| CPU | 8 vCPUs |
| RAM | 16 GB |
| Storage | 500 GB SSD |
| Network | 1 Gbps outbound |
| OS | Ubuntu 22.04 LTS |

### Cloud Provider Options (India region)

| Provider | Instance | Monthly Cost (approx.) |
|----------|---------|----------------------|
| AWS (ap-south-1, Mumbai) | c6i.2xlarge | ~$250/month |
| GCP (asia-south1, Mumbai) | c2-standard-8 | ~$220/month |
| Azure (centralindia) | D8s v4 | ~$270/month |
| Hetzner (Finland) | CPX41 | ~$40/month |

---

## 2. Environment Configuration

Copy `.env.example` to `.env` and configure all values:

```bash
# Application
ENVIRONMENT=production
SECRET_KEY=<64-char random hex>
INTERNAL_TRIGGER_TOKEN=<32-char random hex>
API_BASE_URL=https://api.yourdomain.com
FRONTEND_URL=https://yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com

# Database (production — use PostGIS)
DATABASE_URL=postgresql://slopesense:<STRONG_PASSWORD>@db:5432/slopesense

# Redis
REDIS_URL=redis://redis:6379/0

# NASA Earthdata (https://urs.earthdata.nasa.gov)
NASA_EARTHDATA_USERNAME=your_username
NASA_EARTHDATA_PASSWORD=your_password

# ESA Copernicus (https://dataspace.copernicus.eu)
COPERNICUS_CLIENT_ID=your_client_id
COPERNICUS_CLIENT_SECRET=your_client_secret

# WhatsApp Business API (Meta Business Manager)
WHATSAPP_API_TOKEN=EAA...
WHATSAPP_PHONE_NUMBER_ID=1167375806462041
WHATSAPP_VERIFY_TOKEN=<random_verify_token>
WHATSAPP_APP_SECRET=<from_meta_dashboard>

# API Keys (comma-separated list of valid API keys for protected endpoints)
API_KEYS=key1,key2,key3
```

### Generate secure values

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate INTERNAL_TRIGGER_TOKEN
python -c "import secrets; print(secrets.token_hex(16))"
```

---

## 3. Database Setup

### First-time setup

```bash
# Start only the database
docker-compose up -d db

# Wait for healthy status
docker-compose ps

# Run Alembic migrations
docker-compose run --rm api alembic upgrade head

# Seed static geodata (districts, blocks, DEM susceptibility)
docker-compose run --rm api python -m scripts.seed_static

# (Optional) Run retrospective validation
docker-compose run --rm api python -m scripts.retrospective --event wayanad_2024
```

### Applying future migrations

```bash
docker-compose run --rm api alembic upgrade head
docker-compose restart api worker
```

---

## 4. SSL / TLS Configuration

### Using Certbot (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Auto-renewal (already set up by certbot)
sudo systemctl enable certbot.timer
```

### Update nginx.conf

Edit `infra/nginx.conf` to add SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    location / { proxy_pass http://frontend:3000; }
    location /api { proxy_pass http://api:8000; }
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}
```

---

## 5. Deployment Steps

### Initial deployment

```bash
# Clone repository
git clone https://github.com/slopesense/slopesense.git
cd slopesense

# Configure environment
cp .env.example .env
# Edit .env with production values

# Build all images
docker-compose build

# Start infrastructure (DB + Redis first)
docker-compose up -d db redis

# Wait ~30s for DB to be healthy
docker-compose ps

# Run migrations
docker-compose run --rm api alembic upgrade head

# Seed static data
docker-compose run --rm api python -m scripts.seed_static

# Start all services
docker-compose up -d

# Check all services are running
docker-compose ps
docker-compose logs --tail=50 api
```

### Rolling update (zero-downtime)

```bash
# Pull latest code
git pull origin main

# Build new images
docker-compose build api worker frontend

# Apply any new migrations
docker-compose run --rm api alembic upgrade head

# Restart services (Compose handles ordering)
docker-compose up -d --no-deps api worker scheduler frontend

# Verify health
curl -s http://localhost:8000/ | python -m json.tool
```

---

## 6. Post-Deployment Verification

```bash
# Check all containers are running
docker-compose ps

# Verify API health
curl http://localhost:8000/

# Verify database connectivity (should return alert count)
curl http://localhost:8000/v1/alerts/active

# Verify CAP feed
curl http://localhost:8000/v1/cap/feed

# Trigger a test model run (use your INTERNAL_TRIGGER_TOKEN)
curl -X POST "http://localhost:8000/internal/trigger-run?token=YOUR_TOKEN"

# Check logs for errors
docker-compose logs --tail=100 api | grep -i error
docker-compose logs --tail=100 worker | grep -i error
```

### Health check endpoint

The API exposes `GET /` as a health check. Configure your load balancer or uptime monitor to hit this endpoint every 60 seconds.

---

## 7. Monitoring and Observability

### Prometheus Metrics

The API exposes metrics at `GET /metrics` (Prometheus format). Key metrics:

| Metric | Description |
|--------|-------------|
| `slopesense_active_alerts` | Current number of active alerts |
| `slopesense_model_runs_total` | Total model runs since startup |
| `slopesense_messages_sent_total` | Total WhatsApp messages sent |
| `slopesense_fpi_scores` | Histogram of FPI score distribution |
| `http_requests_total` | HTTP request counts by method/endpoint |
| `http_request_duration_seconds` | Request latency histogram |

### Log Management

Logs are written to `./logs/` and also to stdout (captured by Docker):

```bash
# View live API logs
docker-compose logs -f api

# View worker logs
docker-compose logs -f worker

# Search for errors in the last hour
docker-compose logs --since=1h api | grep -E "ERROR|CRITICAL"
```

### Recommended Stack

| Tool | Purpose |
|------|---------|
| Prometheus | Metrics collection |
| Grafana | Dashboards and alerting |
| Loki | Log aggregation |
| UptimeRobot | External uptime monitoring (free tier) |

---

## 8. Backup Strategy

### Database backups

```bash
# Daily backup (add to crontab)
docker-compose exec db pg_dump -U slopesense slopesense | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip -c backup_20240729.sql.gz | docker-compose exec -T db psql -U slopesense slopesense
```

### Crontab for automated backups

```cron
# Daily database backup at 2am, keep 30 days
0 2 * * * /opt/slopesense/scripts/backup.sh >> /var/log/slopesense-backup.log 2>&1
```

### Data directory

The `./data/` directory contains downloaded satellite files. These can be regenerated by the ingestion pipeline, so they don't need to be backed up, but you may want to snapshot them to avoid re-downloading.

---

## 9. Scaling Considerations

### Horizontal scaling (API workers)

Increase Uvicorn workers in `docker-compose.yml`:

```yaml
command: uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or use Gunicorn:

```yaml
command: gunicorn backend.api.main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000
```

### Celery concurrency

Increase Celery concurrency for faster model runs:

```yaml
command: celery -A backend.worker.celery_app worker --loglevel=info --concurrency=4
```

### Database connection pooling

For high traffic, add PgBouncer in front of PostgreSQL:

```yaml
pgbouncer:
  image: pgbouncer/pgbouncer
  environment:
    DATABASES_HOST: db
    DATABASES_PORT: 5432
    DATABASES_USER: slopesense
    DATABASES_PASSWORD: ${DB_PASSWORD}
    MAX_CLIENT_CONN: 100
    DEFAULT_POOL_SIZE: 20
```

---

## 10. Rollback Procedure

### Quick rollback to previous version

```bash
# Identify the previous image tag
docker images | grep slopesense

# Roll back API (replace TAG with previous version)
docker-compose stop api
docker tag slopesense-api:previous slopesense-api:current
docker-compose up -d api

# If migration needs reverting
docker-compose run --rm api alembic downgrade -1
```

### Emergency rollback

```bash
# Stop all services
docker-compose down

# Restore database from backup
gunzip -c backup_YYYYMMDD.sql.gz | docker-compose exec -T db psql -U slopesense slopesense

# Start previous version
git checkout v1.0.0
docker-compose up -d
```

---

## Useful Commands

```bash
# View resource usage
docker stats

# Exec into running container
docker-compose exec api bash
docker-compose exec db psql -U slopesense slopesense

# Force rebuild without cache
docker-compose build --no-cache

# Remove all stopped containers and unused images
docker system prune -f

# View Celery task queue
docker-compose exec worker celery -A backend.worker.celery_app inspect active

# Manually trigger pipeline
curl -X POST "https://api.yourdomain.com/internal/trigger-run?token=YOUR_TOKEN"
```
