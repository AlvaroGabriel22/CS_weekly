# ACL Service Usage Examples

This document provides practical examples of how to use the `PermissionService` in your FastAPI routes.

## Setup

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.permission_service import PermissionService
from app.models import User, Activity, WeeklyReport, Attachment
from app.models.permissions import PermissionLevel, AccessScope

app = FastAPI()
```

## Example 1: Checking View Permissions

### Scenario: Get a weekly report only if user has access

```python
@app.get("/api/weeklies/{weekly_id}")
async def get_weekly_report(
    weekly_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific weekly report if user has permission"""
    
    # Get the weekly report
    weekly_report = db.query(WeeklyReport).filter(
        WeeklyReport.id == weekly_id
    ).first()
    
    if not weekly_report:
        raise HTTPException(status_code=404, detail="Weekly report not found")
    
    # Check if user can view this report
    if not PermissionService.can_view_weekly_report(current_user, weekly_report, db):
        # Log unauthorized access attempt
        PermissionService.log_audit(
            user_id=current_user.id,
            action="view_attempt",
            resource_type="weekly",
            resource_id=weekly_id,
            status="failure",
            error_message="Permission denied",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            db=db,
        )
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Log successful access
    PermissionService.log_audit(
        user_id=current_user.id,
        action="view",
        resource_type="weekly",
        resource_id=weekly_id,
        db=db,
    )
    
    return {
        "id": weekly_report.id,
        "title": weekly_report.title,
        "status": weekly_report.status,
        "created_at": weekly_report.created_at,
    }
```

## Example 2: Getting All Accessible Resources

### Scenario: Get list of all weeklies user can access

```python
@app.get("/api/weeklies")
async def list_accessible_weeklies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all weeklies accessible to the user"""
    
    # Get all accessible weeklies
    weeklies = PermissionService.get_accessible_weeklies(current_user, db)
    
    return [
        {
            "id": w.id,
            "title": w.title,
            "owner": w.user.name,
            "status": w.status,
            "created_at": w.created_at,
        }
        for w in weeklies
    ]
```

### Scenario: Get list of all activities user can access

```python
@app.get("/api/activities")
async def list_accessible_activities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all activities accessible to the user"""
    
    # Get all accessible activities
    activities = PermissionService.get_accessible_activities(current_user, db)
    
    return [
        {
            "id": a.id,
            "title": a.title,
            "department": a.department,
            "owner": a.user.name,
            "activity_date": a.activity_date,
        }
        for a in activities
    ]
```

## Example 3: Sharing Activities

### Scenario: Share an activity with another user

```python
@app.post("/api/activities/{activity_id}/share")
async def share_activity(
    activity_id: str,
    target_user_id: str,
    permission_level: str = "viewer",  # or "editor"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Share an activity with another user"""
    
    # Get the activity
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Check if current user can share this activity
    if not PermissionService.can_share_activity(current_user, activity, db):
        raise HTTPException(status_code=403, detail="Cannot share this activity")
    
    # Verify target user exists
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    try:
        # Share the activity
        perm_level = PermissionLevel[permission_level.upper()]
        share = PermissionService.share_activity(
            activity=activity,
            shared_by_user=current_user,
            shared_with_user_id=target_user_id,
            permission_level=perm_level,
            db=db,
        )
        
        # Log the sharing action
        PermissionService.log_audit(
            user_id=current_user.id,
            action="share",
            resource_type="activity",
            resource_id=activity_id,
            changes={
                "shared_with": target_user_id,
                "permission_level": perm_level.value,
            },
            db=db,
        )
        
        return {
            "status": "shared",
            "activity_id": activity_id,
            "shared_with": target_user.name,
            "permission_level": perm_level.value,
        }
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
```

## Example 4: Granting Weekly Access

### Scenario: Grant permission to view a specific weekly

```python
@app.post("/api/weeklies/{weekly_id}/grant-access")
async def grant_access_to_weekly(
    weekly_id: str,
    target_user_id: str,
    permission_level: str = "viewer",
    expires_in_days: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grant access to a weekly report to another user"""
    
    # Get the weekly report
    weekly_report = db.query(WeeklyReport).filter(
        WeeklyReport.id == weekly_id
    ).first()
    
    if not weekly_report:
        raise HTTPException(status_code=404, detail="Weekly not found")
    
    # Only owner or admins can grant access
    if weekly_report.user_id != current_user.id and not PermissionService._is_privileged_role(current_user):
        raise HTTPException(status_code=403, detail="Cannot grant access")
    
    # Verify target user exists
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Get old permission level for audit
    old_perm = db.query(WeeklyPermission).filter(
        and_(
            WeeklyPermission.weekly_report_id == weekly_id,
            WeeklyPermission.user_id == target_user_id,
        )
    ).first()
    old_level = old_perm.permission_level.value if old_perm else None
    
    # Grant permission
    perm_level = PermissionLevel[permission_level.upper()]
    permission = PermissionService.grant_weekly_permission(
        weekly_report=weekly_report,
        user_id=target_user_id,
        permission_level=perm_level,
        access_scope=AccessScope.PERSONAL,
        expires_in_days=expires_in_days,
        granted_by_user=current_user,
        db=db,
    )
    
    # Log permission change for audit
    audit_log = PermissionService.log_audit(
        user_id=current_user.id,
        action="grant_permission",
        resource_type="weekly",
        resource_id=weekly_id,
        changes={
            "target_user": target_user_id,
            "permission": perm_level.value,
        },
        db=db,
    )
    
    # Log permission change details
    PermissionService.log_permission_change(
        audit_log_id=audit_log.id,
        target_user_id=target_user_id,
        resource_type="weekly",
        resource_id=weekly_id,
        changed_by_user_id=current_user.id,
        old_permission_level=old_level,
        new_permission_level=perm_level.value,
        old_access_scope=old_perm.access_scope.value if old_perm else None,
        new_access_scope=AccessScope.PERSONAL.value,
        reason=f"Granted by {current_user.name}",
        db=db,
    )
    
    return {
        "status": "permission_granted",
        "weekly_id": weekly_id,
        "user": target_user.name,
        "permission_level": perm_level.value,
        "expires_in_days": expires_in_days,
    }
```

## Example 5: Editing Weekly Reports

### Scenario: Update a weekly report with permission check

```python
@app.put("/api/weeklies/{weekly_id}")
async def update_weekly_report(
    weekly_id: str,
    title: str,
    content: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a weekly report if user has edit permission"""
    
    # Get the weekly report
    weekly_report = db.query(WeeklyReport).filter(
        WeeklyReport.id == weekly_id
    ).first()
    
    if not weekly_report:
        raise HTTPException(status_code=404, detail="Weekly not found")
    
    # Check if user can edit
    if not PermissionService.can_edit_weekly_report(current_user, weekly_report, db):
        raise HTTPException(status_code=403, detail="Cannot edit this weekly")
    
    # Perform the update
    weekly_report.title = title
    weekly_report.content = content
    db.commit()
    
    # Log the edit
    PermissionService.log_audit(
        user_id=current_user.id,
        action="edit",
        resource_type="weekly",
        resource_id=weekly_id,
        changes={
            "title": title,
            "content_updated": True,
        },
        db=db,
    )
    
    return {
        "status": "updated",
        "weekly_id": weekly_id,
        "title": weekly_report.title,
    }
```

## Example 6: Downloading Files with Tracking

### Scenario: Download a file with access logging and tracking

```python
from fastapi.responses import FileResponse
import os

@app.get("/api/attachments/{attachment_id}/download")
async def download_file(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a file if user has permission"""
    
    # Get the attachment
    attachment = db.query(Attachment).filter(
        Attachment.id == attachment_id
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user can download
    if not PermissionService.can_download_file(current_user, attachment, db):
        PermissionService.log_audit(
            user_id=current_user.id,
            action="download_attempt",
            resource_type="file",
            resource_id=attachment_id,
            status="failure",
            error_message="Permission denied",
            db=db,
        )
        raise HTTPException(status_code=403, detail="Cannot download this file")
    
    # Log the download
    PermissionService.log_audit(
        user_id=current_user.id,
        action="download",
        resource_type="file",
        resource_id=attachment_id,
        db=db,
    )
    
    # Update file share tracking
    file_share = db.query(FileShare).filter(
        FileShare.attachment_id == attachment_id
    ).first()
    
    if file_share:
        file_share.download_count += 1
        file_share.last_accessed_at = datetime.now(UTC)
        db.commit()
    
    # Return file
    if os.path.exists(attachment.file_path):
        return FileResponse(
            attachment.file_path,
            filename=attachment.original_filename,
        )
    
    raise HTTPException(status_code=404, detail="File not found on disk")
```

## Example 7: Auto-granting Department Access

### Scenario: When creating a weekly, auto-grant department access

```python
@app.post("/api/weeklies")
async def create_weekly_report(
    template_id: str,
    week_number: int,
    year: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new weekly report with auto-permission setup"""
    
    # Create the weekly report
    weekly_report = WeeklyReport(
        user_id=current_user.id,
        template_id=template_id,
        week_number=week_number,
        year=year,
        status=WeeklyStatus.DRAFT,
    )
    db.add(weekly_report)
    db.flush()  # Get the ID before commit
    
    try:
        # Auto-grant department access
        dept_perms = PermissionService.auto_grant_department_weekly_access(weekly_report, db)
        
        # Auto-grant manager access
        mgr_perms = PermissionService.auto_grant_manager_access(weekly_report, db)
        
        db.commit()
        
        # Log creation
        PermissionService.log_audit(
            user_id=current_user.id,
            action="create",
            resource_type="weekly",
            resource_id=weekly_report.id,
            changes={
                "department_perms": len(dept_perms),
                "manager_perms": len(mgr_perms),
            },
            db=db,
        )
        
        return {
            "id": weekly_report.id,
            "status": "created",
            "department_users_granted": len(dept_perms),
            "managers_granted": len(mgr_perms),
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating weekly: {str(e)}")
```

## Example 8: Sharing Files with Department

### Scenario: Auto-share file with entire department

```python
@app.post("/api/attachments/{attachment_id}/share-department")
async def share_file_with_department(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Share a file with the user's department"""
    
    # Get the attachment
    attachment = db.query(Attachment).filter(
        Attachment.id == attachment_id
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get the activity to check ownership
    activity = db.query(Activity).filter(
        Activity.id == attachment.activity_id
    ).first()
    
    if activity.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only share your own files")
    
    # Share with department
    file_share = PermissionService.share_file(
        attachment=attachment,
        shared_by_user=current_user,
        shared_with_department=current_user.department,
        permission_level=PermissionLevel.VIEWER,
        expires_in_days=30,
        db=db,
    )
    
    # Log the sharing
    PermissionService.log_audit(
        user_id=current_user.id,
        action="share_file",
        resource_type="file",
        resource_id=attachment_id,
        changes={
            "department": current_user.department,
            "permission": "viewer",
        },
        db=db,
    )
    
    return {
        "status": "shared",
        "file_id": attachment_id,
        "department": current_user.department,
        "expires_days": 30,
    }
```

## Example 9: Auditing User Activities

### Scenario: Get audit log for user activities

```python
@app.get("/api/admin/audit-log")
async def get_audit_log(
    user_id: str = None,
    resource_type: str = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit log entries (admin only)"""
    
    # Check admin access
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "user": log.user.name if log.user else "Unknown",
            "action": log.action,
            "resource": f"{log.resource_type}:{log.resource_id}",
            "status": log.status,
            "ip_address": log.ip_address,
            "timestamp": log.created_at,
        }
        for log in logs
    ]
```

## Example 10: Cleaning Up Expired Permissions

### Scenario: Scheduled task to clean expired permissions

```python
from celery import Celery
from app.core.database import SessionLocal

celery_app = Celery("qwi")

@celery_app.task
def cleanup_expired_permissions():
    """Clean up expired permissions (run daily)"""
    db = SessionLocal()
    
    try:
        # Delete expired weekly permissions
        expired_weekly = db.query(WeeklyPermission).filter(
            and_(
                WeeklyPermission.expires_at != None,
                WeeklyPermission.expires_at < datetime.now(UTC),
            )
        ).count()
        
        db.query(WeeklyPermission).filter(
            and_(
                WeeklyPermission.expires_at != None,
                WeeklyPermission.expires_at < datetime.now(UTC),
            )
        ).delete()
        
        # Delete expired file shares
        expired_files = db.query(FileShare).filter(
            and_(
                FileShare.expires_at != None,
                FileShare.expires_at < datetime.now(UTC),
            )
        ).count()
        
        db.query(FileShare).filter(
            and_(
                FileShare.expires_at != None,
                FileShare.expires_at < datetime.now(UTC),
            )
        ).delete()
        
        db.commit()
        
        # Log the cleanup
        PermissionService.log_audit(
            user_id=None,
            action="cleanup_expired",
            resource_type="system",
            resource_id="scheduler",
            changes={
                "expired_weekly_permissions": expired_weekly,
                "expired_file_shares": expired_files,
            },
            status="success",
            db=db,
        )
        
        return {
            "expired_weekly": expired_weekly,
            "expired_files": expired_files,
        }
    
    finally:
        db.close()

# Schedule this task daily
# In your Celery beat configuration
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-expired-permissions': {
        'task': 'app.services.celery_tasks.cleanup_expired_permissions',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM UTC
    },
}
```

## Notes

1. Always check permissions before returning data
2. Log all access attempts (successful and failed)
3. Use `PermissionLevel` and `AccessScope` enums
4. Handle timezone-aware datetimes (UTC)
5. Consider performance impact of permission checks
6. Cache permission results if checking frequently
7. Use Celery for async permission grants
8. Archive old audit logs periodically
9. Monitor slow permission queries
10. Test permission scenarios thoroughly

## Security Best Practices

- Always verify user identity before granting permissions
- Log all permission changes for compliance
- Use HTTPS for all API calls
- Implement rate limiting on permission endpoints
- Validate input data (UUIDs, enums)
- Handle expiring permissions gracefully
- Monitor for suspicious permission patterns
- Regular audit log review
- Implement permission revocation mechanisms
