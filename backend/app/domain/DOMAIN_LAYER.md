# Domain Layer Architecture - QWI

The Domain Layer represents the heart of the Quality Weekly AI (QWI) application. It encapsulates all business logic, rules, and invariants in pure Python, completely isolated from infrastructure concerns like databases, APIs, or frameworks.

## Core Principles

1. **Business Logic First**: All domain rules and behaviors are expressed in the domain layer
2. **No Infrastructure Dependencies**: Pure Python code with no ORM, framework, or database imports
3. **Immutability**: Value objects are frozen dataclasses, ensuring thread-safety
4. **Type Safety**: Strong typing through value objects and type hints
5. **Encapsulation**: Business rules are enforced through aggregate methods
6. **Event Sourcing Ready**: Domain events represent all state changes

## Directory Structure

```
backend/app/domain/
├── __init__.py              # Public API exports
├── values.py                # Value Objects (immutable domain concepts)
├── entities.py              # Domain Entities (Aggregates)
├── events.py                # Domain Events
├── exceptions.py            # Business Rule Exceptions
├── permission_rules.py      # Permission Logic (Stateless Rules)
└── DOMAIN_LAYER.md          # This file
```

## Key Components

### 1. Value Objects (`values.py`)

Type-safe, immutable domain concepts:

**Identifiers:**
- `UserId`, `ActivityId`, `WeeklyReportId`, `DepartmentId`, `AttachmentId`

**Enumerations:**
- `Permission`: OWNER, EDITOR, VIEWER, NONE
- `Role`: User organization roles (Gerente Sr, Analista Jr, etc.)
- `Sector`: Quality sectors (QM, QA, OQC, IQC, FIELD, CSI)
- `ActivityStatus`, `WeeklyStatus`, `AccessScope`

**Complex Value Objects:**
- `DateRange`: Period with business logic
- `WeekRange`: Week and year pair
- `PermissionGrant`: Permission with expiration
- `WritingProfile`, `UserPreferences`

### 2. Domain Entities (`entities.py`)

Aggregate Roots with business logic and invariants:

#### UserAggregate
```python
user = UserAggregate(
    user_id=UserId("user-123"),
    email="user@company.com",
    name="João Silva",
    department="Qualidade",
    role=Role.ANALISTA_SR,
    sector=Sector.QA,
    is_active=True,
    is_admin=False,
    preferences=UserPreferences(...)
)

# Business methods
user.assert_is_active()  # Raises UserNotActive if inactive
user.is_in_department("Qualidade")  # bool
user.has_higher_or_equal_role(Role.ANALISTA_PL)  # bool
user.can_manage_users()  # bool (managers and admins)
```

#### ActivityAggregate
```python
activity = ActivityAggregate(
    activity_id=ActivityId("act-456"),
    user_id=UserId("user-123"),
    title="Audit OQC",
    department="Qualidade",
    activity_date=datetime.now(),
    status=ActivityStatus.DRAFT,
    week_number=32,
    year=2024
)

# Permission checks
activity.assert_can_view_by(UserId("user-123"))
activity.assert_can_be_modified_by(UserId("user-123"))
activity.assert_can_share_with(UserId("user-123"), UserId("user-456"))

# Business operations
activity.share_with(UserId("user-456"), Permission.VIEWER, by_user_id=UserId("user-123"))
activity.revoke_share(UserId("user-456"), by_user_id=UserId("user-123"))
activity.add_attachment(AttachmentId("att-789"))
activity.transition_to(ActivityStatus.REGISTERED)
```

#### WeeklyReportAggregate
```python
weekly = WeeklyReportAggregate(
    weekly_id=WeeklyReportId("weekly-111"),
    user_id=UserId("user-123"),
    week_number=32,
    year=2024,
    status=WeeklyStatus.DRAFT,
    language=Language.PT
)

# Permission checks
weekly.assert_can_view_by(UserId("user-456"))
weekly.assert_can_edit_by(UserId("user-456"))
weekly.assert_can_share_by(UserId("user-456"))

# Business operations
weekly.grant_permission(
    to_user_id=UserId("user-456"),
    permission=Permission.VIEWER,
    access_scope=AccessScope.PERSONAL
)
weekly.revoke_permission(UserId("user-456"), by_user_id=UserId("user-123"))
weekly.transition_to(WeeklyStatus.GENERATING)
```

#### AttachmentAggregate
```python
attachment = AttachmentAggregate(
    attachment_id=AttachmentId("att-789"),
    activity_id=ActivityId("act-456"),
    user_id=UserId("user-123"),
    metadata=FileMetadata(
        filename="audit_report.pdf",
        original_filename="Relatório de Auditoria.pdf",
        file_path="/storage/files/audit_report.pdf",
        file_type="pdf",
        file_size=2048576,
        mime_type="application/pdf"
    )
)

# Permission checks
attachment.assert_can_view_by(UserId("user-456"))
attachment.assert_can_download_by(UserId("user-456"))
attachment.assert_can_share_by(UserId("user-123"))

# Business operations
attachment.share_with_user(UserId("user-456"), Permission.VIEWER, UserId("user-123"))
attachment.share_with_department("Qualidade", Permission.VIEWER, UserId("user-123"))
attachment.record_download()
```

#### DepartmentAggregate
```python
dept = DepartmentAggregate(
    department_id=DepartmentId("dept-qa"),
    name="Qualidade",
    description="Quality Assurance Department"
)

# User management
dept.add_user(UserId("user-123"))
dept.remove_user(UserId("user-123"))
dept.has_user(UserId("user-123"))  # bool

# Resource sharing
dept.share_resource("weekly-111", Permission.VIEWER)
```

### 3. Domain Events (`events.py`)

Immutable events representing state changes:

```python
# User events
UserCreated(user_id=UserId("user-123"), email="user@company.com", ...)
UserActivated(user_id=UserId("user-123"))
UserPermissionChanged(user_id=UserId("user-123"), resource_id="weekly-111", ...)

# Activity events
ActivityCreated(activity_id=ActivityId("act-456"), user_id=UserId("user-123"), ...)
ActivityShared(activity_id=ActivityId("act-456"), from_user_id=UserId("user-123"), ...)
ActivityModified(activity_id=ActivityId("act-456"), changes={"title": "New Title"})

# Weekly events
WeeklyGenerated(weekly_id=WeeklyReportId("weekly-111"), user_id=UserId("user-123"), ...)
WeeklyShared(weekly_id=WeeklyReportId("weekly-111"), from_user_id=UserId("user-123"), ...)

# Permission events
PermissionGranted(user_id=UserId("user-456"), resource_id="weekly-111", ...)
PermissionRevoked(user_id=UserId("user-456"), resource_id="weekly-111", ...)
```

### 4. Domain Exceptions (`exceptions.py`)

Business rule violations with structured information:

```python
from app.domain import (
    PermissionDenied,
    UnauthorizedAccess,
    UserNotActive,
    ActivityNotFound,
    WeeklyReportNotFound,
    InsufficientPermissions,
    CannotShareWithSelf,
    BusinessRuleViolation
)

try:
    activity.assert_can_view_by(user_id)
except UnauthorizedAccess as e:
    print(e.user_id)      # User ID
    print(e.resource_id)  # Resource ID
    print(e.resource_type) # "activity"
    print(e.error_code)   # "UNAUTHORIZED_ACCESS"
```

### 5. Permission Rules (`permission_rules.py`)

Stateless domain rules for permission checking:

```python
from app.domain import PermissionRules

# High-level permission checks
can_view = PermissionRules.can_view_activity(user, activity)
can_edit = PermissionRules.can_edit_activity(user, activity)
can_share = PermissionRules.can_share_activity(user, activity, target_user)

# Get accessible resources
accessible_activities = PermissionRules.get_accessible_activities(user, all_activities)
accessible_weeklys = PermissionRules.get_accessible_weeklys(user, all_weeklys)
accessible_attachments = PermissionRules.get_accessible_attachments(user, all_attachments)

# Filter by permission level
viewer_activities = PermissionRules.filter_activities_by_permission(
    user, all_activities, permission=Permission.VIEWER
)

# Cross-aggregate rules
can_include = PermissionRules.can_include_activity_in_weekly(user, activity, weekly)
can_add_attachment = PermissionRules.can_add_attachment_to_activity(user, activity)
```

## Usage Patterns

### Pattern 1: Permission Checks Before Operations

```python
# Bad: Let exceptions bubble up
activity.assert_can_view_by(user_id)
render_activity(activity)

# Good: Use permission rules
if PermissionRules.can_view_activity(user, activity):
    render_activity(activity)
else:
    raise PermissionDenied(...)
```

### Pattern 2: Sharing Resources

```python
# Share activity with another user
try:
    activity.share_with(
        target_user_id=target_user.user_id,
        permission=Permission.VIEWER,
        by_user_id=current_user.user_id
    )
    # Publish event
    event_bus.publish(ActivityShared(
        activity_id=activity.activity_id,
        from_user_id=current_user.user_id,
        to_user_id=target_user.user_id,
        permission_level=Permission.VIEWER.value
    ))
except CannotShareWithSelf:
    raise
except PermissionDenied:
    raise
```

### Pattern 3: Filtering Collections

```python
# Get all activities user can view
user_activities = PermissionRules.get_accessible_activities(user, all_activities)

# Get all weeklys with at least viewer permission
weeklys = PermissionRules.filter_weeklys_by_permission(
    user, all_weeklys, permission=Permission.VIEWER
)
```

### Pattern 4: Status Transitions

```python
# Before transitioning, check if valid
if activity.can_transition_to(ActivityStatus.PROCESSED):
    activity.transition_to(ActivityStatus.PROCESSED)
    # Publish event
    event_bus.publish(ActivityProcessed(...))
```

### Pattern 5: Aggregate State Validation

```python
# Ensure preconditions
user.assert_is_active()
activity.assert_can_view_by(user.user_id)

# Perform operation
include_in_report(activity, weekly)
```

## Integration Points

### With Applications Layer
The application layer uses domain entities and services to orchestrate business processes:

```python
# app/applications/activity_service.py
class ActivityService:
    def share_activity(self, user_id: str, activity_id: str, target_user_id: str):
        # Fetch aggregates
        user = self.user_repo.get(UserId(user_id))
        activity = self.activity_repo.get(ActivityId(activity_id))
        target = self.user_repo.get(UserId(target_user_id))
        
        # Use domain logic
        activity.share_with(
            target_user_id=target.user_id,
            permission=Permission.VIEWER,
            by_user_id=user.user_id
        )
        
        # Publish event
        self.event_bus.publish(ActivityShared(...))
        
        # Persist
        self.activity_repo.save(activity)
```

### With Infrastructure Layer
Repositories map ORM models to domain aggregates:

```python
# app/repositories/activity_repo.py
class ActivityRepository:
    def to_domain(self, orm_model) -> ActivityAggregate:
        return ActivityAggregate(
            activity_id=ActivityId(orm_model.id),
            user_id=UserId(orm_model.user_id),
            title=orm_model.title,
            ...
        )
    
    def from_domain(self, aggregate: ActivityAggregate) -> ActivityModel:
        return ActivityModel(
            id=aggregate.activity_id.value,
            user_id=aggregate.user_id.value,
            title=aggregate.title,
            ...
        )
```

## Best Practices

1. **Always Use Value Objects**: Never use raw strings for IDs
   ```python
   # Bad
   activity.share_with("user-123", "viewer")
   
   # Good
   activity.share_with(UserId("user-123"), Permission.VIEWER)
   ```

2. **Check Permissions First**: Use PermissionRules before operations
   ```python
   if not PermissionRules.can_edit_activity(user, activity):
       raise PermissionDenied(...)
   ```

3. **Publish Events After Changes**: Domain events document business events
   ```python
   activity.share_with(...)
   event_bus.publish(ActivityShared(...))
   ```

4. **Use Aggregate Methods**: Let aggregates enforce invariants
   ```python
   # Good: Activity enforces permission check
   activity.share_with(target, permission, by_user)
   
   # Bad: Manual permission checking
   if can_share:
       add_share(activity.id, target.id)
   ```

5. **Exceptions for Domain Violations**: Use domain exceptions
   ```python
   try:
       activity.assert_can_view_by(user_id)
   except UnauthorizedAccess:
       return {"error": "Access denied"}
   ```

## Testing the Domain Layer

```python
def test_user_can_view_shared_activity():
    # Create aggregates
    owner = UserAggregate(user_id=UserId("owner"), ...)
    viewer = UserAggregate(user_id=UserId("viewer"), ...)
    activity = ActivityAggregate(user_id=owner.user_id, ...)
    
    # Share activity
    activity.share_with(viewer.user_id, Permission.VIEWER, owner.user_id)
    
    # Assert viewer can view
    assert PermissionRules.can_view_activity(viewer, activity)

def test_viewer_cannot_modify_activity():
    # Setup
    activity = ActivityAggregate(...)
    activity.share_with(UserId("viewer"), Permission.VIEWER, owner_id)
    
    # Assert raises exception
    with pytest.raises(InsufficientPermissions):
        activity.assert_can_be_modified_by(UserId("viewer"))
```

## Future Extensions

The domain layer is designed for extensibility:

1. **Event Sourcing**: All state changes are domain events
2. **CQRS**: Separate write models (aggregates) from read models
3. **Policy Engines**: Add complex rules without changing aggregates
4. **Time-based Rules**: Expiring permissions use datetime checks
5. **Department Rules**: DepartmentAggregate for org-wide policies
