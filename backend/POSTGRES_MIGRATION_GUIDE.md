# PostgreSQL Migration Guide - QWI Database Refactor

## Overview

This guide documents the migration from SQLite to PostgreSQL with comprehensive ACL (Access Control List) support, audit logging, and performance optimizations.

## Key Changes

### 1. Database Driver Changes

**Before (SQLite):**
```python
DATABASE_URL: str = "sqlite:///./qwi.db"
```

**After (PostgreSQL):**
```python
DATABASE_URL: str = "postgresql://qwi:qwi_secret@localhost:5432/qwi_db"
```

### 2. New Dependencies

Added to `requirements.txt`:
- `psycopg2-binary==2.9.9` - PostgreSQL DBAPI
- `asyncpg==0.29.0` - Async PostgreSQL driver (optional)
- `redis==5.0.1` - Caching and Celery broker
- `celery==5.3.4` - Async task processing

### 3. Database Schema Changes

#### Timezone-Aware Timestamps
- All `DateTime` columns now use `DateTime(timezone=True)`
- Automatically handled by SQLAlchemy for both read and write
- PostgreSQL timezone configuration: UTC

#### Removed SQLite Workarounds
- No more PRAGMA foreign_keys
- Native PostgreSQL constraints
- Proper JSON support
- Native ENUM types

#### New ACL Tables

```
activity_shares
├── activity_id (FK → activities)
├── shared_by_user_id (FK → users)
├── shared_with_user_id (FK → users)
└── permission_level: ENUM(owner, editor, viewer, none)

weekly_permissions
├── weekly_report_id (FK → weekly_reports)
├── user_id (FK → users)
├── permission_level: ENUM(owner, editor, viewer, none)
├── access_scope: ENUM(personal, department, organization)
└── expires_at (nullable)

file_shares
├── attachment_id (FK → attachments)
├── shared_by_user_id (FK → users)
├── shared_with_department (nullable)
├── shared_with_user_id (nullable, FK → users)
├── permission_level: ENUM(owner, editor, viewer, none)
├── access_scope: ENUM(personal, department, organization)
├── download_count
├── last_accessed_at
└── expires_at (nullable)

audit_log
├── user_id (nullable, FK → users)
├── action (e.g., 'view', 'edit', 'delete', 'share')
├── resource_type (e.g., 'weekly', 'activity', 'file')
├── resource_id
├── changes (JSON)
├── ip_address
├── user_agent
├── status (success, failure, partial)
└── error_message (nullable)

permission_changes
├── audit_log_id (FK → audit_log)
├── changed_by_user_id (FK → users)
├── target_user_id (FK → users)
├── resource_type
├── resource_id
├── old_permission_level
├── new_permission_level
├── old_access_scope
├── new_access_scope
└── reason (nullable)

department_roles
├── department
├── role
├── can_share_activities
├── can_share_files
├── can_view_all_weekly
├── can_edit_weekly
└── auto_share_files_with_department
```

### 4. Permission Rules

#### Manager/Chief Access (GERENTE/CHEFE)
- Access to ALL weeklies across organization
- Access to ALL activities
- Can grant permissions
- Auto-added to all weekly permission lists

#### Department-Level Access
- Users can view/access activities of same department
- Department members share files automatically (configurable)
- Can view department members' weeklies

#### Personal Sharing
- Users can explicitly share activities with specific users
- Users can share files with specific users or departments
- Permissions can expire

#### Permission Hierarchy
1. Owner (full access)
2. Editor (can modify)
3. Viewer (read-only)
4. None (no access)

## Migration Steps

### 1. Prepare PostgreSQL Database

```bash
# Create database and user
createdb qwi_db
createuser qwi -P  # Will prompt for password

# Grant privileges
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE qwi_db TO qwi;"
```

### 2. Update Configuration

```bash
# Update .env file
DATABASE_URL=postgresql://qwi:qwi_secret@localhost:5432/qwi_db
REDIS_URL=redis://localhost:6379/0
```

### 3. Install New Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Migrations

```bash
# Initialize Alembic (if not done)
alembic upgrade head

# Or manually with specific versions
alembic upgrade 001  # Initial schema
alembic upgrade 002  # ACL schema
```

### 5. Update Models

Replace imports in your code:

```python
# Old
from app.models import User, Activity, WeeklyReport

# New (same import works, models now use postgres_models)
from app.models import User, Activity, WeeklyReport
```

The `__init__.py` in models should re-export from `postgres_models.py`.

### 6. Initialize ACL Rules

```python
from sqlalchemy.orm import Session
from app.models import DepartmentRole
from datetime import datetime, UTC

def setup_acl_rules(db: Session):
    """Initialize department role permissions"""
    
    rules = [
        {
            "department": "Qualidade",
            "role": "Gerente Sr",
            "can_view_all_weekly": True,
            "can_edit_weekly": True,
            "can_share_activities": True,
            "can_share_files": True,
        },
        {
            "department": "Qualidade",
            "role": "Chefe",
            "can_view_all_weekly": True,
            "can_share_activities": True,
            "can_share_files": True,
        },
        # ... more rules
    ]
    
    for rule in rules:
        existing = db.query(DepartmentRole).filter(
            DepartmentRole.department == rule["department"],
            DepartmentRole.role == rule["role"],
        ).first()
        
        if not existing:
            db.add(DepartmentRole(**rule))
    
    db.commit()
```

## Performance Optimizations

### Indexes Added

**User Table**
- `(department, is_active)` - Filter active users by department
- `(created_at DESC)` - Timeline queries
- `(email)` - Authentication lookups
- `(employee_id)` - Employee ID searches

**Activity Table**
- `(user_id, year, week_number)` - Weekly activity queries
- `(department)` - Department-wide searches
- `(status)` - Status filtering
- `(created_at DESC)` - Recent activity

**Weekly Reports**
- `(user_id, year, week_number)` - User's weekly reports
- `(status)` - Report status filters
- `(created_at DESC)` - Recent reports

**ACL Tables**
- `(department)` - Department-level queries
- `(expires_at)` - Expired permission cleanup
- `(resource_type, resource_id)` - Permission queries by resource
- `(created_at DESC)` - Audit trail queries

### Query Optimization Tips

```python
# Bad - N+1 query problem
for weekly in weeklies:
    user = db.query(User).filter(User.id == weekly.user_id).first()

# Good - Use relationships
from sqlalchemy.orm import joinedload
weeklies = db.query(WeeklyReport).options(joinedload(WeeklyReport.user)).all()

# Good - Use department index
from sqlalchemy import and_
users = db.query(User).filter(
    and_(
        User.department == "Qualidade",
        User.is_active == True
    )
).all()
```

## Audit Logging

Every significant action is logged:

```python
from app.services.permission_service import PermissionService

# Log an action
PermissionService.log_audit(
    user_id=current_user.id,
    action="view",
    resource_type="weekly",
    resource_id=weekly_id,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    db=db
)

# Log permission change
PermissionService.log_permission_change(
    audit_log_id=audit_log.id,
    target_user_id=user_id,
    resource_type="weekly",
    resource_id=weekly_id,
    old_permission_level="viewer",
    new_permission_level="editor",
    changed_by_user_id=current_user.id,
    reason="User promoted to team lead",
    db=db
)
```

## Using the ACL Service

### Check Permissions

```python
from app.services.permission_service import PermissionService

# Check view access
if PermissionService.can_view_weekly_report(current_user, weekly_report, db):
    # User can see this report
    pass

# Check edit access
if PermissionService.can_edit_weekly_report(current_user, weekly_report, db):
    # User can modify this report
    pass

# Check activity access
if PermissionService.can_view_activity(current_user, activity, db):
    # User can see this activity
    pass

# Check file download
if PermissionService.can_download_file(current_user, attachment, db):
    # User can download this file
    pass
```

### Grant Permissions

```python
from app.models.permissions import PermissionLevel, AccessScope

# Share activity with specific user
PermissionService.share_activity(
    activity=activity,
    shared_by_user=current_user,
    shared_with_user_id=target_user_id,
    permission_level=PermissionLevel.VIEWER,
    db=db
)

# Grant weekly access with expiration
PermissionService.grant_weekly_permission(
    weekly_report=weekly_report,
    user_id=target_user_id,
    permission_level=PermissionLevel.EDITOR,
    access_scope=AccessScope.DEPARTMENT,
    expires_in_days=30,
    granted_by_user=current_user,
    db=db
)

# Auto-grant department access
PermissionService.auto_grant_department_weekly_access(weekly_report, db)

# Auto-grant manager access
PermissionService.auto_grant_manager_access(weekly_report, db)

# Share file
PermissionService.share_file(
    attachment=attachment,
    shared_by_user=current_user,
    shared_with_department="Qualidade",
    permission_level=PermissionLevel.VIEWER,
    expires_in_days=90,
    db=db
)
```

### Get Accessible Resources

```python
# Get all accessible weeklies
weeklies = PermissionService.get_accessible_weeklies(current_user, db)

# Get all accessible activities
activities = PermissionService.get_accessible_activities(current_user, db)
```

## Celery Integration (Optional)

For async task processing with Celery:

```python
from celery import Celery
from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(__name__)
celery_app.conf.broker_url = settings.REDIS_URL
celery_app.conf.result_backend = settings.REDIS_URL

@celery_app.task
def auto_grant_permissions(weekly_report_id: str):
    """Async task to auto-grant permissions when weekly is created"""
    # Implementation
    pass
```

## Monitoring & Cleanup

### Cleanup Expired Permissions

```python
from datetime import datetime, UTC

# Remove expired permissions
db.query(WeeklyPermission).filter(
    WeeklyPermission.expires_at < datetime.now(UTC)
).delete()

db.query(FileShare).filter(
    FileShare.expires_at < datetime.now(UTC)
).delete()

db.commit()
```

### Query Audit Logs

```python
# Get recent activity for user
logs = db.query(AuditLog).filter(
    AuditLog.user_id == user_id
).order_by(AuditLog.created_at.desc()).limit(100).all()

# Get all changes to a resource
changes = db.query(PermissionChange).filter(
    and_(
        PermissionChange.resource_type == "weekly",
        PermissionChange.resource_id == weekly_id
    )
).all()
```

## Troubleshooting

### Connection Issues

```python
# Test connection
from sqlalchemy import create_engine, text
engine = create_engine(DATABASE_URL, echo=True)
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
```

### Migration Issues

```bash
# Check current migration version
alembic current

# Show upgrade path
alembic upgrade --sql head

# Downgrade if needed
alembic downgrade -1
```

### Timezone Issues

All timestamps are UTC. Client-side conversion is recommended:

```python
from datetime import datetime, timezone, timedelta

# Convert UTC to local timezone
utc_dt = datetime.fromisoformat("2026-08-10T12:00:00+00:00")
local_tz = timezone(timedelta(hours=-3))  # Brazil timezone
local_dt = utc_dt.astimezone(local_tz)
```

## Production Deployment

### PostgreSQL Server Setup

```sql
-- Create database
CREATE DATABASE qwi_db OWNER qwi;

-- Set timezone
ALTER DATABASE qwi_db SET timezone = 'UTC';

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search
CREATE EXTENSION IF NOT EXISTS uuid-ossp;  -- For UUID generation

-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_users_active ON users(is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_activities_recent ON activities(created_at DESC);
```

### Performance Tuning

```sql
-- Update table statistics
ANALYZE;

-- Monitor slow queries
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
SELECT pg_reload_conf();
```

### Backup Strategy

```bash
# Daily backups
pg_dump -h localhost -U qwi qwi_db | gzip > /backups/qwi_db_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip < backup_file.sql.gz | psql -U qwi -d qwi_db
```

## Rollback Plan

If you need to rollback:

```bash
# Downgrade to previous migration
alembic downgrade 001

# Or specific revision
alembic downgrade <revision_id>
```

## Files Modified/Created

- `backend/app/models/permissions.py` - NEW: ACL models
- `backend/app/models/postgres_models.py` - NEW: PostgreSQL models
- `backend/app/core/database.py` - UPDATED: PostgreSQL configuration
- `backend/app/services/permission_service.py` - NEW: ACL service
- `backend/app/db/migrations/versions/002_postgresql_schema.py` - NEW: Migration
- `backend/requirements.txt` - UPDATED: New dependencies

## Support & Questions

For issues with the migration:
1. Check audit logs: `SELECT * FROM audit_log ORDER BY created_at DESC`
2. Review migration status: `alembic current`
3. Check PostgreSQL logs: `SELECT * FROM pg_logs`
