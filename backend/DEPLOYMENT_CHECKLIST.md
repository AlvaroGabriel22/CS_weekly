# PostgreSQL Deployment Checklist

## Pre-Deployment

- [ ] PostgreSQL 12+ installed on target server
- [ ] Python 3.10+ installed
- [ ] Redis server installed (for caching/Celery)
- [ ] Network access configured (firewall rules)
- [ ] Backup strategy documented
- [ ] Rollback plan tested

## Database Setup

### Step 1: PostgreSQL Configuration

```bash
# Connect to PostgreSQL admin
sudo -u postgres psql

# Create database and user
CREATE DATABASE qwi_db OWNER postgres;
CREATE USER qwi WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE qwi_db TO qwi;

# Enable required extensions
\c qwi_db
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- Text search
CREATE EXTENSION IF NOT EXISTS uuid-ossp;    -- UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- Cryptographic functions

# Set timezone
ALTER DATABASE qwi_db SET timezone = 'UTC';

# Exit psql
\q
```

### Step 2: Performance Tuning

```bash
# Edit /etc/postgresql/<version>/main/postgresql.conf
sudo nano /etc/postgresql/14/main/postgresql.conf

# Recommended settings for moderate workload:
max_connections = 100
shared_buffers = 256MB                    # 25% of system RAM
effective_cache_size = 1GB                # 50-75% of system RAM
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB                            # shared_buffers / max_connections

# Enable slow query logging
log_min_duration_statement = 1000          # Log queries > 1s
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Step 3: Connection Pool Setup

```bash
# Install pgBouncer for connection pooling (optional but recommended)
sudo apt-get install pgbouncer

# Configure /etc/pgbouncer/pgbouncer.ini
sudo nano /etc/pgbouncer/pgbouncer.ini

# Add database configuration:
[databases]
qwi_db = host=localhost port=5432 user=qwi password=strong_password_here

# Add pool configuration:
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 10
reserve_pool_size = 5

# Start pgBouncer
sudo systemctl start pgbouncer
```

## Application Deployment

### Step 1: Environment Configuration

```bash
# Create .env file
cat > /path/to/app/.env << EOF
DATABASE_URL=postgresql://qwi:strong_password_here@localhost:5432/qwi_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
APP_NAME=Quality Weekly Intelligence
CORS_ORIGINS=["https://yourdomain.com"]
EOF

chmod 600 /path/to/app/.env
```

### Step 2: Install Dependencies

```bash
cd /path/to/backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development/testing
```

### Step 3: Database Migration

```bash
# Check Alembic version
alembic current

# Run migrations
alembic upgrade head

# Verify migration
psql -U qwi -d qwi_db -c "\dt"  # List all tables
```

### Step 4: Initialize ACL Rules

```bash
python << 'EOF'
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.models.permissions import DepartmentRole

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

rules = [
    {
        "department": "Qualidade",
        "role": "Gerente Sr",
        "can_view_all_weekly": True,
        "can_edit_weekly": True,
        "can_share_activities": True,
        "can_share_files": True,
        "auto_share_files_with_department": True,
    },
    {
        "department": "Qualidade",
        "role": "Chefe",
        "can_view_all_weekly": True,
        "can_edit_weekly": False,
        "can_share_activities": True,
        "can_share_files": True,
        "auto_share_files_with_department": True,
    },
    {
        "department": "Qualidade",
        "role": "Analista Sr",
        "can_view_all_weekly": False,
        "can_edit_weekly": False,
        "can_share_activities": True,
        "can_share_files": True,
        "auto_share_files_with_department": True,
    },
]

for rule in rules:
    existing = db.query(DepartmentRole).filter(
        DepartmentRole.department == rule["department"],
        DepartmentRole.role == rule["role"],
    ).first()
    
    if not existing:
        db.add(DepartmentRole(**rule))

db.commit()
print("ACL rules initialized")
EOF
```

### Step 5: Start Application

```bash
# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or using supervisor (recommended)
sudo nano /etc/supervisor/conf.d/qwi.conf

# Add:
[program:qwi]
directory=/path/to/backend
command=/path/to/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
user=qwi
autostart=true
autorestart=true
stderr_logfile=/var/log/qwi/error.log
stdout_logfile=/var/log/qwi/access.log

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start qwi
```

### Step 6: Start Celery (Optional)

```bash
# In separate terminal or supervisor process
celery -A app.services.celery_app worker --loglevel=info

# Or with supervisor:
[program:qwi_celery]
directory=/path/to/backend
command=/path/to/backend/venv/bin/celery -A app.services.celery_app worker --loglevel=info
user=qwi
autostart=true
autorestart=true
stderr_logfile=/var/log/qwi/celery_error.log
stdout_logfile=/var/log/qwi/celery.log

# Optional: Celery Beat for scheduled tasks
[program:qwi_celery_beat]
directory=/path/to/backend
command=/path/to/backend/venv/bin/celery -A app.services.celery_app beat --loglevel=info
user=qwi
autostart=true
autorestart=true
```

### Step 7: Configure Web Server (Nginx/Apache)

#### Nginx Configuration

```nginx
upstream qwi_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 50M;

    location / {
        proxy_pass http://qwi_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    location /static/ {
        alias /path/to/backend/static/;
        expires 30d;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain application/json application/javascript;
}
```

## Post-Deployment Verification

- [ ] Database connectivity test
  ```bash
  psql -h localhost -U qwi -d qwi_db -c "SELECT 1;"
  ```

- [ ] Application health check
  ```bash
  curl https://yourdomain.com/api/health
  ```

- [ ] ACL functionality test
  ```bash
  curl -H "Authorization: Bearer TOKEN" https://yourdomain.com/api/weeklies
  ```

- [ ] File upload test
  ```bash
  # Upload test file
  curl -F "file=@test.pdf" -H "Authorization: Bearer TOKEN" https://yourdomain.com/api/activities/upload
  ```

- [ ] Audit logging verification
  ```bash
  psql -U qwi -d qwi_db -c "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10;"
  ```

## Monitoring & Maintenance

### Daily Tasks

```bash
# Check PostgreSQL status
systemctl status postgresql

# Check application logs
tail -f /var/log/qwi/access.log
tail -f /var/log/qwi/error.log

# Monitor disk usage
df -h /var/lib/postgresql
```

### Weekly Tasks

```bash
# Vacuum and analyze database
psql -U qwi -d qwi_db << EOF
VACUUM ANALYZE;
EOF

# Review slow queries
psql -U qwi -d qwi_db -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check index usage
psql -U qwi -d qwi_db << EOF
SELECT schemaname, tablename, indexname, idx_scan FROM pg_stat_user_indexes ORDER BY idx_scan ASC;
EOF
```

### Monthly Tasks

- [ ] Full database backup verification
  ```bash
  pg_dump -U qwi -d qwi_db | gzip > /backups/qwi_db_$(date +%Y%m%d).sql.gz
  ls -lh /backups/qwi_db_*.sql.gz
  ```

- [ ] Audit log retention check
  ```bash
  psql -U qwi -d qwi_db << EOF
  DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '90 days';
  EOF
  ```

- [ ] Permission expiry cleanup
  ```bash
  psql -U qwi -d qwi_db << EOF
  DELETE FROM weekly_permissions WHERE expires_at < NOW();
  DELETE FROM file_shares WHERE expires_at < NOW();
  EOF
  ```

- [ ] Performance review
  ```bash
  psql -U qwi -d qwi_db -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datname = 'qwi_db';"
  ```

## Backup & Restore

### Automated Backup Script

```bash
#!/bin/bash
# /usr/local/bin/backup_qwi_db.sh

BACKUP_DIR="/backups/qwi"
DAYS_TO_KEEP=30
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U qwi -d qwi_db | gzip > $BACKUP_DIR/qwi_db_$DATE.sql.gz

# Backup uploads directory (if applicable)
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /path/to/backend/uploads/

# Remove old backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +$DAYS_TO_KEEP -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +$DAYS_TO_KEEP -delete

# Log backup
echo "Backup completed: $DATE" >> $BACKUP_DIR/backup.log

# Add to crontab for daily runs at 2 AM
# 0 2 * * * /usr/local/bin/backup_qwi_db.sh
```

### Restore from Backup

```bash
# List backups
ls -lh /backups/qwi/

# Restore database
gunzip < /backups/qwi/qwi_db_YYYYMMDD_HHMMSS.sql.gz | psql -U qwi -d qwi_db

# Verify restore
psql -U qwi -d qwi_db -c "SELECT COUNT(*) FROM users;"
```

## Security Checklist

- [ ] PostgreSQL password changed from default
- [ ] PostgreSQL listening only on localhost (or secured with SSL)
- [ ] Application using HTTPS only
- [ ] CORS origins restricted to known domains
- [ ] API rate limiting configured
- [ ] Authentication tokens have expiration
- [ ] File upload directory not web-accessible
- [ ] Database credentials in environment variables
- [ ] Audit logging enabled for compliance
- [ ] Regular security patches applied

## Rollback Procedure

If issues occur:

```bash
# 1. Stop application
sudo supervisorctl stop qwi

# 2. Downgrade database
cd /path/to/backend
alembic downgrade 001

# 3. Restore from backup if needed
gunzip < /backups/qwi/qwi_db_BACKUP_DATE.sql.gz | psql -U qwi -d qwi_db

# 4. Restart application
sudo supervisorctl start qwi

# 5. Verify functionality
curl https://yourdomain.com/api/health
```

## Support Contacts

- PostgreSQL Issues: [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- Application Issues: Check /var/log/qwi/error.log
- Performance Issues: Run `SELECT * FROM pg_stat_statements;`
