# Repository Pattern - Data Access Layer

## Overview

The Repository pattern provides a clean separation between the data access logic and business logic. All database queries are centralized in repository classes, making the codebase more maintainable and testable.

## Architecture

```
                    FastAPI Routes
                         ↓
                      Services
                         ↓
                    Repositories
                         ↓
                    SQLAlchemy ORM
                         ↓
                    SQLite Database
```

## Base Repository

### `BaseRepository[T]`

Generic CRUD operations for any model.

**Available Methods:**

```python
# Create
repo.create(obj_in: dict) -> T

# Read
repo.read(id: str) -> T
repo.read_all(skip: int, limit: int) -> List[T]

# Update
repo.update(id: str, obj_in: dict) -> T

# Delete
repo.delete(id: str) -> bool           # Hard delete
repo.soft_delete(id: str) -> bool      # Soft delete via is_active

# Query
repo.exists(**filters) -> bool
repo.count(**filters) -> int
repo.get_by_filters(**filters) -> List[T]
repo.get_by_filter(**filters) -> T
repo.get_paginated(skip, limit, order_by, descending, **filters) -> (List[T], int)

# Bulk Operations
repo.bulk_create(objects: List[dict]) -> List[T]
repo.bulk_update(updates: List[(id, dict)]) -> int
repo.bulk_delete(ids: List[str]) -> int
repo.bulk_soft_delete(ids: List[str]) -> int
```

## Specialized Repositories

### UserRepository

```python
repo = UserRepository(session)

# Get by field
user = repo.get_by_email(email)
user = repo.get_by_employee_id(emp_id)

# Get by role/sector
users = repo.get_by_role(UserRole.ANALISTA_SR)
users = repo.get_by_sector(QualitySector.CSI)

# Search
users = repo.search_by_name("João")

# Check existence
exists = repo.email_exists(email)
exists = repo.employee_id_exists(emp_id)

# Activation
repo.deactivate(user_id)
repo.activate(user_id)

# Stats
count = repo.count_active()
count = repo.count_by_role(UserRole.ANALISTA_SR)
```

### ActivityRepository

```python
repo = ActivityRepository(session)

# Get by week (OPTIMIZED with indexes)
activities = repo.get_by_week(user_id, year, week)
activities = repo.get_by_week_with_attachments(user_id, year, week)

# Get by date range
activities = repo.get_by_date_range(user_id, start_date, end_date)

# Get by status
activities = repo.get_by_status(user_id, ActivityStatus.REGISTERED)

# Get for report
activities = repo.get_for_weekly_report(user_id, year, week)

# Search
activities = repo.search(user_id, query="keyword")

# Stats
count = repo.count_by_week(user_id, year, week)
summary = repo.get_weekly_summary(user_id, year, week)
# Returns: {
#   'total': int,
#   'by_status': {status: count},
#   'by_category': {category: count},
#   'by_project': {project: count},
#   'included_in_report': int,
# }
```

### WeeklyRepository

```python
repo = WeeklyRepository(session)

# Get or create
report = repo.get_or_create_draft(user_id, year, week)

# Get specific
report = repo.get_by_user_week(user_id, year, week)

# Get by status
reports = repo.get_by_status(user_id, WeeklyStatus.COMPLETED)
reports = repo.get_completed(user_id, limit=10)

# Generation workflow
repo.start_generation(report_id)
repo.complete_generation(report_id, content, pptx_path)
repo.mark_failed(report_id, error_msg)

# Stats
count = repo.count_completed(user_id)
stats = repo.get_quality_stats(user_id)
# Returns: {
#   'average': float,
#   'min': float,
#   'max': float,
#   'count': int,
# }
```

### AttachmentRepository

```python
repo = AttachmentRepository(session)

# Get by activity
attachments = repo.get_by_activity(activity_id)
images = repo.get_images(activity_id)

# Get for report
images = repo.get_images_for_report(activity_id)

# Get needing processing
attachments = repo.get_needing_ai_analysis(limit=50)
images = repo.get_needing_captions(limit=50)

# Update AI results
repo.update_ai_analysis(attachment_id, analysis_dict)
repo.update_ai_caption(attachment_id, caption)
repo.update_kpi_data(attachment_id, kpi_data)

# Stats
total_size = repo.get_total_size_for_activity(activity_id)
counts = repo.count_by_type(activity_id)  # Returns {'image': 2, 'document': 1}
```

## Usage in Services

```python
from app.repositories import ActivityRepository
from sqlalchemy.orm import Session

class ActivityService:
    def __init__(self, db: Session):
        self.repo = ActivityRepository(db)

    def get_week_activities(self, user_id: str, year: int, week: int):
        # Repository handles the SQL
        return self.repo.get_by_week(user_id, year, week)

    def create_activity(self, user_id: str, data: ActivityCreate):
        # Repository handles insert + commit
        activity = self.repo.create({
            'user_id': user_id,
            **data.dict(),
        })
        return activity
```

## Best Practices

### 1. Always Use Repositories

❌ **Bad:**
```python
# Direct SQLAlchemy in service
activity = db.query(Activity).filter(...).first()
```

✅ **Good:**
```python
# Through repository
activity = repo.get_by_week(user_id, year, week)
```

### 2. Specialized Queries

❌ **Bad:**
```python
# Complex query in service
activities = (
    db.query(Activity)
    .filter(Activity.user_id == user_id)
    .filter(Activity.year == year)
    .filter(Activity.week_number == week)
    .order_by(Activity.activity_date.desc())
    .all()
)
```

✅ **Good:**
```python
# Named, tested, reusable
activities = repo.get_by_week(user_id, year, week)
```

### 3. Eager Loading for Related Data

✅ **Good:**
```python
# Load with relationships
activities = repo.get_by_week_with_attachments(user_id, year, week)
# Avoids N+1 queries
```

### 4. Pagination

✅ **Good:**
```python
items, total = repo.get_paginated(skip=0, limit=50, order_by='created_at')
```

### 5. Bulk Operations

✅ **Good:**
```python
# Efficiently update multiple records
updates = [
    (activity_id_1, {'status': ActivityStatus.PROCESSED}),
    (activity_id_2, {'status': ActivityStatus.PROCESSED}),
]
count = repo.bulk_update(updates)
```

## Testing Repositories

```python
def test_get_by_week(db, test_user, test_activity):
    """Test week query"""
    repo = ActivityRepository(db)
    
    activities = repo.get_by_week(
        test_user.id,
        test_activity.year,
        test_activity.week_number
    )
    
    assert test_activity in activities
```

## Performance Considerations

### Indexes Used

Each repository leverages specific indexes:

**ActivityRepository:**
- `(user_id, year, week_number)` - Fast week queries
- `(activity_date, user_id)` - Date range queries
- `(status, user_id)` - Status filtering

**WeeklyRepository:**
- `(user_id, year, week_number)` UNIQUE - Ensures one per week
- `(user_id, status)` - Status filtering

**AttachmentRepository:**
- `(activity_id)` - Get all for activity
- `(file_type)` - Filter by type

### Query Optimization

```python
# ✅ GOOD: Eager load relationships
activities = repo.get_by_week_with_attachments(user_id, year, week)

# ❌ BAD: N+1 query problem
activities = repo.get_by_week(user_id, year, week)
for activity in activities:
    print(len(activity.attachments))  # Triggers query for each activity
```

## Adding New Methods

1. **Identify the query pattern**
   ```python
   # Examples: get_by_*, search_*, count_*
   ```

2. **Add to specialized repository**
   ```python
   def get_by_custom_filter(self, **filters):
       return self.session.query(self.model).filter(...).all()
   ```

3. **Add tests**
   ```python
   def test_get_by_custom_filter(self, db):
       repo = ActivityRepository(db)
       results = repo.get_by_custom_filter(...)
       assert len(results) > 0
   ```

4. **Document in README**
   ```markdown
   ### get_by_custom_filter
   
   Description of what it does...
   ```

## Database Transactions

Repositories handle commits automatically:

```python
# Single operation (auto-commits)
user = repo.create({'email': 'test@example.com'})

# Multiple operations (manual commit in service)
user1 = repo.create(data1)
user2 = repo.create(data2)
db.commit()  # If service needs atomic operations
```

## Related Files

- `base.py` - Generic BaseRepository
- `user_repo.py` - User-specific queries
- `activity_repo.py` - Activity-specific queries
- `weekly_repo.py` - Weekly report queries
- `attachment_repo.py` - File attachment queries
- `tests/test_integration/test_repositories.py` - Repository tests
