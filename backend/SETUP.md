# Backend Setup Guide

## Initial Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Create Database Schema

#### Option A: Using Alembic (Recommended)

```bash
# Run all migrations
alembic upgrade head

# Or run specific migration
alembic upgrade 001
```

#### Option B: Using SQLAlchemy directly

```bash
python -m app.db.seeds.runner
```

### 3. Seed Test Data (Optional)

```bash
python -m app.db.seeds.runner
```

This creates:
- 5 test users with different roles
- 35+ test activities
- Proper timestamps and relationships

## Development Workflow

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Specific test file
pytest tests/test_unit/test_utils/test_dates.py -v

# Specific test function
pytest tests/test_unit/test_utils/test_dates.py::TestDateUtils::test_calculate_week_number -v
```

### Creating New Migrations

After modifying models, create a migration:

```bash
# Auto-generate migration (detects schema changes)
alembic revision --autogenerate -m "Add new column to activities"

# Manual migration
alembic revision -m "Add new column to activities"

# Apply migrations
alembic upgrade head

# Revert last migration
alembic downgrade -1
```

### Database Management

```bash
# View migration history
alembic history

# Current version
alembic current

# Downgrade all
alembic downgrade base
```

## Database Schema

### Tables Created

1. **users** - User accounts
   - UUID primary key
   - Unique email and employee_id
   - Relationships: writing_profiles, activities, weekly_reports

2. **writing_profiles** - AI preferences per user
   - Language, tone, objectivity level
   - Auto-generation toggles
   - FK: user_id (1:1)

3. **templates** - Report templates
   - PPTX template files
   - Slide configuration
   - Multi-language support

4. **activities** - Weekly activities log
   - Title, description, metadata
   - Activity date (always UTC)
   - Week number (1-53) and year
   - Status: DRAFT, REGISTERED, PROCESSED, USED_IN_REPORT
   - Tags as JSON array
   - Relationships: user, metadata_entry, attachments
   - **Key Index**: (user_id, year, week_number) for weekly queries

5. **activity_metadata** - AI-processed data
   - KPIs, keywords, technical summary
   - Confidence score
   - Processing timestamp
   - FK: activity_id (1:1)

6. **attachments** - File uploads
   - Original filename + system filename
   - File type, size, MIME type
   - Image usage preferences
   - AI captions and analysis
   - KPI data extracted from charts
   - FK: activity_id (N:1)

7. **weekly_reports** - Generated reports
   - Status: DRAFT, GENERATING, COMPLETED, FAILED
   - Version tracking
   - PPTX path and content as JSON
   - Quality score and confidence index
   - **Unique Constraint**: (user_id, year, week_number)
   - FK: user_id, template_id

## Constraints & Indexes

### Check Constraints
- `activities.week_number` BETWEEN 1 AND 53
- `weekly_reports.week_number` BETWEEN 1 AND 53

### Unique Constraints
- `users.email` UNIQUE
- `users.employee_id` UNIQUE
- `activities_metadata.activity_id` UNIQUE
- `writing_profiles.user_id` UNIQUE
- `weekly_reports` (user_id, year, week_number) UNIQUE

### Key Indexes
- User queries: (email, employee_id, created_at)
- Activity queries: (user_id, year, week_number), (activity_date), (status)
- Weekly reports: (user_id, year, week_number), (status)
- Attachment queries: (activity_id, file_type, created_at)

## Best Practices

### Dates
- All datetime fields are in UTC
- Use `datetime.now(UTC)` for server-side timestamps
- Frontend converts to local timezone for display

### Queries
- Use compound indexes for complex WHERE clauses
- Always filter by user_id for multi-tenant queries
- Use week_number + year instead of date ranges for weekly queries

### Soft Deletes
- Use `is_active` field instead of hard delete
- Filter queries with `WHERE is_active = True`

### JSON Fields
- Always provide default values (dict or list)
- Validate data structure in service layer
- Use dedicated models for complex structures

## Troubleshooting

### Alembic not finding models
```bash
# Ensure app is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"

# Or run from backend directory
cd backend && alembic upgrade head
```

### Foreign key constraint errors
- Check CASCADE settings in migrations
- Ensure parent records exist before child records
- Use `ondelete='SET NULL'` for optional FKs

### Date/timezone issues
- Always use UTC in backend
- Never assume local timezone
- Convert only in UI/API responses

## Testing with Real Database

For integration tests, use:

```python
from sqlalchemy import create_engine
from app.core.database import Base, SessionLocal

# In-memory SQLite for tests (conftest.py already does this)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
```

## Production Considerations

1. **Backup Before Migrations**
   ```bash
   cp qwi.db qwi.db.backup
   alembic upgrade head
   ```

2. **Test Migrations Locally First**
   ```bash
   # Create test DB
   sqlite3 test_qwi.db < /dev/null
   alembic upgrade head --sql  # Shows SQL without executing
   ```

3. **Monitor Migration Progress**
   ```bash
   alembic current
   alembic history
   ```
