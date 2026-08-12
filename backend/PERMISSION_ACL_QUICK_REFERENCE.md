# Permission/ACL System - Quick Reference Guide

## At a Glance

```
Permission Levels: NONE < VIEWER < EDITOR < OWNER

Manager Roles: GERENTE_SR, GERENTE_PL, GERENTE_JR, CHEFE
  → Can access ALL resources
  → Can grant/revoke permissions
  → Can edit all weeklies

Department Members: Same department
  → Can view each other's weeklies (VIEWER only)
  → Can view each other's activities
  → Can access shared files

Owners: Created the resource
  → Full access (OWNER level)
  → Can share with others
```

## Common Tasks

### Check Permission Before Action

```python
from app.services.permission_service import PermissionService

# Before viewing
if not PermissionService.can_view_weekly_report(user, weekly, db):
    raise HTTPException(status_code=403)

# Before editing
if not PermissionService.can_edit_weekly_report(user, weekly, db):
    raise HTTPException(status_code=403)

# Before downloading
if not PermissionService.can_download_file(user, attachment, db):
    raise HTTPException(status_code=403)
```

### Get All Accessible Resources

```python
from app.repositories.permission_repo import PermissionRepository

perm_repo = PermissionRepository(db)

# All accessible weeklies
weeklies = perm_repo.get_accessible_weeklies_optimized(user_id)

# All accessible activities
activities = perm_repo.get_accessible_activities_optimized(user_id)

# All shared attachments
attachments = perm_repo.get_shared_attachments_optimized(user_id)
```

### Share a Resource

```python
from app.models.permissions import PermissionLevel

# Share weekly report
PermissionService.grant_weekly_permission(
    weekly_report=report,
    user_id=target_user_id,
    permission_level=PermissionLevel.VIEWER,
    expires_in_days=30,  # Optional
    db=db
)

# Share activity
PermissionService.share_activity(
    activity=activity,
    shared_by_user=current_user,
    shared_with_user_id=target_user_id,
    permission_level=PermissionLevel.EDITOR,
    db=db
)

# Share file
PermissionService.share_file(
    attachment=file,
    shared_by_user=current_user,
    shared_with_department="Qualidade",  # or specific user_id
    permission_level=PermissionLevel.VIEWER,
    expires_in_days=7,
    db=db
)
```

### Auto-Grant Permissions

```python
# Grant to all department members
PermissionService.auto_grant_department_weekly_access(weekly, db)

# Grant to all managers
PermissionService.auto_grant_manager_access(weekly, db)
```

### Revoke Permissions

```python
from app.repositories.permission_repo import PermissionRepository

perm_repo = PermissionRepository(db)

perm_repo.revoke_all_permissions(
    resource_type="weekly",  # or "activity", "file"
    resource_id=resource_id,
    user_id=user_id
)
```

### Log Audit Trail

```python
from app.services.permission_service import PermissionService

# Log action
PermissionService.log_audit(
    user_id=current_user.id,
    action="view_weekly",  # or any action name
    resource_type="weekly",
    resource_id=weekly_id,
    changes={"viewed": True},
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    db=db
)
```

### API Dependencies

```python
from app.api.deps import (
    get_current_user,          # Any authenticated user
    get_current_admin_user,    # Managers only
    get_user_context,          # User + permissions
    get_permission_repo,       # Permission repo injection
)

@router.get("/admin-only")
def admin_endpoint(
    user = Depends(get_current_admin_user)  # 403 if not manager
):
    return {"user": user.name}

@router.get("/with-context")
def context_endpoint(
    context = Depends(get_user_context)
):
    return {
        "accessible_weeklies": context["accessible_weeklies"],
        "is_manager": context["is_manager"],
    }
```

### Use Permission-Filtered Queries

```python
from app.repositories.weekly_repo import WeeklyRepository
from app.repositories.activity_repo import ActivityRepository
from app.repositories.attachment_repo import AttachmentRepository

weekly_repo = WeeklyRepository(db)
activity_repo = ActivityRepository(db)
attachment_repo = AttachmentRepository(db)

# Only accessible weeklies
weeklies = weekly_repo.get_completed_with_permission(user_id)

# Only accessible activities
activities = activity_repo.get_by_week_with_permission(user_id, 2026, 32)

# Only accessible attachments
attachments = attachment_repo.get_by_activity_with_permission(user_id, activity_id)
```

## Permission Checks Flowchart

```
Is User Manager? 
├─ YES → ALLOW ✓
└─ NO  → Continue

Is User Owner?
├─ YES → ALLOW ✓
└─ NO  → Continue

Does Explicit Permission Exist?
├─ YES → Check Level & Expiration → ALLOW/DENY
└─ NO  → Continue

Are They in Same Department?
├─ YES → ALLOW ✓ (for view-only)
└─ NO  → DENY ✗
```

## Permission Levels Explained

| Level | Can View | Can Edit | Can Share | When To Use |
|-------|----------|----------|-----------|------------|
| OWNER | ✓ | ✓ | ✓ | Resource creator |
| EDITOR | ✓ | ✓ | ✗ | Trusted collaborator |
| VIEWER | ✓ | ✗ | ✗ | Read-only access |
| NONE | ✗ | ✗ | ✗ | Denied (revoked) |

## Role Permissions Matrix

|  | Manager | Chief | Analyst (Same Dept) | Analyst (Other Dept) |
|---|---------|-------|---------------------|----------------------|
| View Any Weekly | ✓ | ✓ | ✗ | ✗ |
| View Own Weekly | ✓ | ✓ | ✓ | ✓ |
| Edit Any Weekly | ✓ | ✓ | ✗ | ✗ |
| Edit Own Weekly | ✓ | ✓ | ✓ | ✓ |
| View Any Activity | ✓ | ✓ | ✗ | ✗ |
| View Own Activity | ✓ | ✓ | ✓ | ✓ |
| View Dept Activities | ✓ | ✓ | ✓ | ✗ |
| Download Any File | ✓ | ✓ | ✗ | ✗ |
| Download Own File | ✓ | ✓ | ✓ | ✓ |
| Grant Permissions | ✓ | ✓ | ✗ | ✗ |

## HTTP Status Codes

```
200 OK - Permission granted, action succeeded
201 Created - Resource created
204 No Content - Action succeeded, no response body
400 Bad Request - Invalid parameters
401 Unauthorized - Not authenticated
403 Forbidden - Permission denied
404 Not Found - Resource doesn't exist
500 Internal Server Error - Server error
```

## Audit Log Fields

```
Field              | Meaning
-------------------|------------------------------------------
user_id            | Who performed the action
action             | What action (view, edit, share, etc)
resource_type      | What type (weekly, activity, file)
resource_id        | Which specific resource
changes            | What changed (JSON)
status             | success, failure, partial
ip_address         | IP making the request
user_agent         | Browser/client information
created_at         | When the action happened
```

## Common Audit Actions

```
Permission-Related:
- grant_permission
- revoke_permission
- permission_check
- bulk_grant_permission

Resource-Related:
- create_weekly
- update_weekly
- view_weekly
- download_file
- share_activity
- share_file
```

## Environment & Configuration

```python
# No special configuration needed for basic usage
# Permission models and tables already exist
# All permission levels defined in app.models.permissions

# Optional: Configure department roles
from app.models.permissions import DepartmentRole

DepartmentRole(
    department="Qualidade",
    role="Analista Sr",
    can_share_activities=True,
    can_share_files=True,
    can_view_all_weekly=False,
    can_edit_weekly=False,
    auto_share_files_with_department=True
)
```

## Performance Tips

1. **Use optimized methods**
   ```python
   # ✓ Good (single optimized query)
   weeklies = perm_repo.get_accessible_weeklies_optimized(user_id)
   
   # ✗ Avoid (N+1 queries)
   all_weeklies = db.query(WeeklyReport).all()
   accessible = [w for w in all_weeklies if can_view(user, w)]
   ```

2. **Batch operations when possible**
   ```python
   # ✓ Good (single commit)
   perm_repo.bulk_grant_weekly_permission(weekly_id, user_ids)
   
   # ✗ Avoid (N commits)
   for user_id in user_ids:
       grant_permission(weekly_id, user_id)
       db.commit()
   ```

3. **Use pagination for large result sets**
   ```python
   # ✓ Good
   weeklies = weeklies[skip:skip+limit]
   
   # ✗ Avoid
   weeklies = db.query(WeeklyReport).all()  # Could be 10k+ items
   ```

## Common Errors

```
Error: Permission Denied (403)
  → Check if user has explicit permission
  → Check if user is in same department
  → Check if user is manager
  → Check if permission expired
  → Check user.is_active status

Error: Resource Not Found (404)
  → Verify resource exists in database
  → Check if resource was deleted
  → Verify resource_id is correct

Error: Audit Log Not Found
  → Create audit log first before logging permission changes
  → Ensure db.commit() after creating audit log

Error: N+1 Query Problem
  → Use optimized repository methods
  → Use eager loading with joinedload()
  → Avoid loops with database queries
```

## Testing Checklist

- [ ] Manager can access all resources
- [ ] Users can access own resources
- [ ] Users can't access unshared resources from other depts
- [ ] Explicit permissions work correctly
- [ ] Expired permissions are denied
- [ ] Audit logs are created
- [ ] Bulk operations work
- [ ] Permission revocation works
- [ ] Department auto-share works
- [ ] All permission levels are respected

## Files to Know

| File | Purpose |
|------|---------|
| `app/services/permission_service.py` | Core permission logic |
| `app/repositories/permission_repo.py` | Optimized ACL queries |
| `app/models/permissions.py` | Data models |
| `app/api/deps.py` | API dependencies |
| `PERMISSION_ACL_GUIDE.md` | Full documentation |
| `PERMISSION_ACL_EXAMPLES.py` | 12 endpoint examples |
| `PERMISSION_ACL_TESTS.py` | Test suite (32 tests) |

## Quick Links

- **Full Guide**: See `PERMISSION_ACL_GUIDE.md`
- **Code Examples**: See `PERMISSION_ACL_EXAMPLES.py`
- **Test Examples**: See `PERMISSION_ACL_TESTS.py`
- **Implementation Details**: See `PERMISSION_ACL_IMPLEMENTATION_SUMMARY.md`

## Support

For issues or questions:

1. Check the full guide (`PERMISSION_ACL_GUIDE.md`)
2. Review examples (`PERMISSION_ACL_EXAMPLES.py`)
3. Look at tests (`PERMISSION_ACL_TESTS.py`)
4. Check audit logs for permission failures
5. Enable debug logging for permission checks

---

**Last Updated**: August 2026
**Version**: 1.0
**Status**: Production Ready
