# Permission/ACL System Implementation Guide

## Overview

This document describes the comprehensive Permission/Access Control List (ACL) layer implemented for the Quality Weekly AI system. The system provides:

- Role-based permission checking
- Resource-level access control
- Optimized permission queries
- Audit trail logging
- Permission hierarchy management

## Architecture

### Core Components

1. **Permission Models** (`app/models/permissions.py`)
   - `ActivityShare` - Share activities between users
   - `WeeklyPermission` - Control access to weekly reports
   - `FileShare` - Share attachments with departments or users
   - `AuditLog` - Track all permission-related actions
   - `PermissionChange` - Track permission modifications
   - `DepartmentRole` - Define role capabilities per department

2. **Permission Repository** (`app/repositories/permission_repo.py`)
   - Optimized queries for permission checks
   - Batch operations for bulk permission management
   - Audit log retrieval

3. **Permission Service** (`app/services/permission_service.py`)
   - High-level permission operations
   - Auto-sharing logic (department, manager access)
   - Activity and file sharing

4. **API Dependencies** (`app/api/deps.py`)
   - Enhanced `get_current_user` with permission context
   - `get_current_admin_user` for admin-only endpoints
   - `get_user_context` for retrieving user permissions

5. **Updated Repositories**
   - `WeeklyRepository.get_completed_with_permission()`
   - `ActivityRepository.get_by_week_with_permission()`
   - `AttachmentRepository.get_by_activity_with_permission()`

## Permission Levels

```python
class PermissionLevel(str, enum.Enum):
    OWNER = "owner"    # Full access (creator/owner)
    EDITOR = "editor"  # Can edit and view
    VIEWER = "viewer"  # Read-only access
    NONE = "none"      # No access
```

### Permission Hierarchy
```
NONE < VIEWER < EDITOR < OWNER
```

## Access Scopes

```python
class AccessScope(str, enum.Enum):
    PERSONAL = "personal"          # Only for self
    DEPARTMENT = "department"      # Department-wide
    ORGANIZATION = "organization"  # Organization-wide
```

## Role-Based Rules

### Manager/Chief Roles (GERENTE_SR, GERENTE_PL, GERENTE_JR, CHEFE)
- View and manage ALL weekly reports in organization
- View and manage ALL activities
- Download ALL files
- Grant/revoke permissions

### Department Members (Same Department)
- View each other's weekly reports (VIEWER)
- View each other's activities
- Access department-shared files
- Auto-shares configured per department role

### Activity Owners
- Full access to own activities (OWNER)
- Can grant VIEWER/EDITOR to others
- Auto-share with department (configurable)

## Usage Examples

### 1. Check if User Can View Weekly Report

```python
from app.services.permission_service import PermissionService

can_view = PermissionService.can_view_weekly_report(
    user=current_user,
    weekly_report=weekly_report,
    db=session
)

if not can_view:
    raise PermissionError("Access denied")
```

### 2. Get Accessible Resources

```python
from app.repositories.permission_repo import PermissionRepository

perm_repo = PermissionRepository(session)

# Get all accessible weeklies
accessible_weeklies = perm_repo.get_accessible_weeklies_optimized(user_id)

# Get all accessible activities
accessible_activities = perm_repo.get_accessible_activities_optimized(user_id)

# Get shared attachments
shared_attachments = perm_repo.get_shared_attachments_optimized(user_id)
```

### 3. Share a Weekly Report

```python
from app.services.permission_service import PermissionService
from app.models.permissions import PermissionLevel

# Grant viewer access to a user
permission = PermissionService.grant_weekly_permission(
    weekly_report=report,
    user_id=target_user_id,
    permission_level=PermissionLevel.VIEWER,
    expires_in_days=30,
    granted_by_user=current_user,
    db=session
)
```

### 4. Share an Activity

```python
from app.services.permission_service import PermissionService
from app.models.permissions import PermissionLevel

share = PermissionService.share_activity(
    activity=activity,
    shared_by_user=current_user,
    shared_with_user_id=target_user_id,
    permission_level=PermissionLevel.EDITOR,
    db=session
)
```

### 5. Auto-Grant Department Access

```python
# Automatically grant access to all department members
permissions = PermissionService.auto_grant_department_weekly_access(
    weekly_report=report,
    db=session
)

# Automatically grant access to all managers
permissions = PermissionService.auto_grant_manager_access(
    weekly_report=report,
    db=session
)
```

### 6. Get Query-Filtered Results

```python
from app.repositories.weekly_repo import WeeklyRepository
from app.repositories.activity_repo import ActivityRepository

weekly_repo = WeeklyRepository(session)
activity_repo = ActivityRepository(session)

# Get only accessible weeklies
weeklies = weekly_repo.get_completed_with_permission(
    user_id=current_user.id,
    limit=10
)

# Get only accessible activities for a week
activities = activity_repo.get_by_week_with_permission(
    user_id=current_user.id,
    year=2026,
    week=32
)
```

### 7. Using API Dependencies

```python
from fastapi import Depends
from app.api.deps import get_current_user, get_current_admin_user, get_user_context

@router.get("/admin-only-endpoint")
def admin_endpoint(current_user = Depends(get_current_admin_user)):
    """This endpoint only allows managers/chiefs"""
    return {"message": f"Hello {current_user.name}"}

@router.get("/get-user-context")
def context_endpoint(context = Depends(get_user_context)):
    """Get user context with permission info"""
    return {
        "accessible_weeklies": context["accessible_weeklies"],
        "accessible_activities": context["accessible_activities"],
        "is_manager": context["is_manager"],
    }
```

## Database Queries

### Get Accessible Weeklies (Optimized)

```python
# Uses subqueries to efficiently combine:
# 1. Owned weeklies
# 2. Department weeklies
# 3. Explicitly shared weeklies
perm_repo.get_accessible_weeklies_optimized(user_id)
```

Query Plan:
1. Check if user is manager → return all
2. Create subquery for owned items
3. Create subquery for department items
4. Create subquery for shared items
5. Combine with OR and fetch

### Permission Check Performance

- **Owner check**: Direct `user_id` comparison (O(1))
- **Manager check**: Role enum comparison (O(1))
- **Department access**: Single JOIN on Users table
- **Explicit permission**: Indexed query on WeeklyPermission
- **Expiration check**: Uses nullable column with index

### Indexes Used

```sql
-- Permission tables
ix_weekly_permissions_weekly_report_id
ix_weekly_permissions_user_id
ix_weekly_permissions_expires_at

ix_activity_shares_activity_id
ix_activity_shares_shared_with_user_id

ix_file_shares_attachment_id
ix_file_shares_shared_with_department
ix_file_shares_expires_at

-- Audit tables
ix_audit_log_user_id
ix_audit_log_resource_type_id
ix_audit_log_created_at_desc

ix_permission_changes_target_user_id
ix_permission_changes_created_at
```

## Audit Trail

### Log Permission Checks

```python
perm_repo.log_permission_check(
    user_id=user_id,
    resource_type="weekly",
    resource_id=weekly_id,
    action="view",
    allowed=True,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)
```

### Log Permission Changes

```python
PermissionService.log_permission_change(
    audit_log_id=audit_log.id,
    target_user_id=target_user_id,
    resource_type="weekly",
    resource_id=weekly_id,
    changed_by_user_id=current_user.id,
    old_permission_level="none",
    new_permission_level="viewer",
    reason="Shared for project review"
)
```

### Retrieve Audit History

```python
# Get all actions by user
history = perm_repo.get_user_permission_history(user_id, limit=100)

# Get all actions on a resource
resource_history = perm_repo.get_audit_logs_by_resource(
    resource_type="weekly",
    resource_id=weekly_id
)

# Get all actions by specific user
user_history = perm_repo.get_audit_logs_by_user(user_id, limit=100)
```

## Department Role Configuration

Configure capabilities per department role:

```python
from app.models.permissions import DepartmentRole

# Create department role
dept_role = DepartmentRole(
    department="Qualidade",
    role="Analista Sr",
    can_share_activities=True,
    can_share_files=True,
    can_view_all_weekly=False,
    can_edit_weekly=False,
    auto_share_files_with_department=True
)
session.add(dept_role)
session.commit()
```

## Security Considerations

### Permission Expiration
- All permissions can have optional expiration dates
- Automatic cleanup on access (checked at query time)
- Use `expires_in_days` parameter for time-limited access

### Audit Trail
- All permission checks logged to `AuditLog`
- All permission changes logged to `PermissionChange`
- Includes IP address, user agent, and action details
- Enables compliance reporting

### Access Control
- Layered validation: owner → manager → department → explicit shares
- Hierarchical permission levels prevent privilege escalation
- Bulk operations still validate individual permissions

## Migration Steps

1. **Database Setup**
   ```bash
   alembic upgrade head
   ```

2. **Initialize Department Roles**
   ```python
   # Configure department roles for your organization
   # See app/seeds/department_roles.py
   ```

3. **Auto-Grant Existing Resources**
   ```python
   # For each existing weekly report, run:
   PermissionService.auto_grant_department_weekly_access(weekly, db)
   PermissionService.auto_grant_manager_access(weekly, db)
   ```

4. **Update API Endpoints**
   - Add permission checks to endpoints
   - Use `get_user_context` for audit logging
   - Return `403` for unauthorized access

## Best Practices

1. **Always use permission-filtered queries**
   ```python
   # ✓ Good
   weekly_repo.get_completed_with_permission(user_id)
   
   # ✗ Bad - bypasses permission checks
   weekly_repo.get_completed(user_id)
   ```

2. **Log significant permission changes**
   ```python
   PermissionService.log_permission_change(...)
   ```

3. **Check before operations**
   ```python
   if not PermissionService.can_edit_weekly_report(user, weekly, db):
       raise PermissionError()
   ```

4. **Use time-limited shares**
   ```python
   # Share for 7 days only
   grant_permission(..., expires_in_days=7)
   ```

5. **Audit admin actions**
   ```python
   log_audit(
       user_id=admin_id,
       action="permission_grant",
       resource_type="weekly",
       reason="Temporary access for project"
   )
   ```

## Troubleshooting

### User can't see resource they should have access to

1. Check if permission exists
2. Verify permission level > NONE
3. Check if permission expired
4. Verify department matches (if using department access)
5. Check audit logs for errors

### Performance issues with large user bases

1. Use optimized repository methods
2. Ensure indexes exist on permission tables
3. Consider pagination for large result sets
4. Profile slow queries with `EXPLAIN ANALYZE`

### Audit logs growing too large

1. Archive old logs periodically
2. Use indexes on created_at for efficient pruning
3. Consider log retention policies
4. Use views for compliance reporting

## Future Enhancements

- Fine-grained object ACLs
- Delegation of sharing permissions
- Dynamic role assignments
- Permission inheritance hierarchies
- Self-service sharing requests
- Permission analytics dashboard
