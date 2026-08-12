"""
Examples of using the Permission/ACL system in FastAPI routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_current_admin_user,
    get_user_context,
    get_permission_repo,
    get_db,
)
from app.models import User, WeeklyReport, Activity, Attachment
from app.models.permissions import PermissionLevel
from app.repositories.permission_repo import PermissionRepository
from app.repositories.weekly_repo import WeeklyRepository
from app.repositories.activity_repo import ActivityRepository
from app.repositories.attachment_repo import AttachmentRepository
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/v1/examples", tags=["examples"])


# ============================================================================
# Example 1: Permission Check Before Resource Access
# ============================================================================

@router.get("/weeklies/{weekly_id}")
def get_weekly_with_permission(
    weekly_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    GET endpoint with permission check
    Returns 403 if user doesn't have access
    """
    # Get the resource
    weekly = db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
    if not weekly:
        raise HTTPException(status_code=404, detail="Weekly report not found")

    # Check permission
    if not PermissionService.can_view_weekly_report(current_user, weekly, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this report"
        )

    return {"id": weekly.id, "status": weekly.status}


# ============================================================================
# Example 2: Get Only Accessible Resources
# ============================================================================

@router.get("/weeklies")
def list_accessible_weeklies(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    perm_repo: PermissionRepository = Depends(get_permission_repo),
):
    """
    List only weeklies the user can access
    Includes: owned, department, and explicitly shared
    """
    # Use optimized query that includes permission filters
    weeklies = perm_repo.get_accessible_weeklies_optimized(current_user.id)

    # Apply pagination
    total = len(weeklies)
    weeklies = weeklies[skip : skip + limit]

    return {
        "items": [
            {
                "id": w.id,
                "status": w.status,
                "owner": w.user_id,
                "week": w.week_number,
                "year": w.year,
            }
            for w in weeklies
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


# ============================================================================
# Example 3: Admin-Only Endpoint
# ============================================================================

@router.post("/weeklies/{weekly_id}/grant-access")
def grant_weekly_access(
    weekly_id: str,
    target_user_id: str,
    permission_level: PermissionLevel = PermissionLevel.VIEWER,
    expires_in_days: int = None,
    current_user: User = Depends(get_current_admin_user),  # Admin required
    db: Session = Depends(get_db),
):
    """
    Grant access to a weekly report
    Only managers/chiefs can perform this action
    """
    weekly = db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
    if not weekly:
        raise HTTPException(status_code=404, detail="Weekly report not found")

    # Grant permission
    perm = PermissionService.grant_weekly_permission(
        weekly_report=weekly,
        user_id=target_user_id,
        permission_level=permission_level,
        expires_in_days=expires_in_days,
        granted_by_user=current_user,
        db=db,
    )

    # Log the action
    PermissionService.log_audit(
        user_id=current_user.id,
        action="grant_weekly_permission",
        resource_type="weekly",
        resource_id=weekly_id,
        changes={
            "target_user_id": target_user_id,
            "permission_level": permission_level,
            "expires_in_days": expires_in_days,
        },
        db=db,
    )

    return {
        "message": "Access granted successfully",
        "permission_id": perm.id,
        "expires_at": perm.expires_at,
    }


# ============================================================================
# Example 4: Share Activity with Audit Logging
# ============================================================================

@router.post("/activities/{activity_id}/share")
def share_activity(
    activity_id: str,
    target_user_id: str,
    permission_level: PermissionLevel = PermissionLevel.VIEWER,
    current_user: User = Depends(get_current_user),
    context: dict = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    """
    Share an activity with another user
    Includes audit logging with IP address and user agent
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check if user can share
    if not PermissionService.can_share_activity(current_user, activity, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to share this activity"
        )

    # Share the activity
    share = PermissionService.share_activity(
        activity=activity,
        shared_by_user=current_user,
        shared_with_user_id=target_user_id,
        permission_level=permission_level,
        db=db,
    )

    # Log audit with context info
    audit_log = PermissionService.log_audit(
        user_id=current_user.id,
        action="share_activity",
        resource_type="activity",
        resource_id=activity_id,
        changes={
            "target_user_id": target_user_id,
            "permission_level": permission_level,
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        db=db,
    )

    return {
        "message": "Activity shared successfully",
        "share_id": share.id,
        "audit_log_id": audit_log.id,
    }


# ============================================================================
# Example 5: Get Activities with Permission Filter
# ============================================================================

@router.get("/activities")
def list_accessible_activities(
    year: int,
    week: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get activities for a specific week that user can access
    Uses optimized query with permission filters
    """
    activity_repo = ActivityRepository(db)

    # Use permission-filtered query
    activities = activity_repo.get_by_week_with_permission(
        user_id=current_user.id,
        year=year,
        week=week,
    )

    return {
        "activities": [
            {
                "id": a.id,
                "title": a.title,
                "owner_id": a.user_id,
                "status": a.status,
                "date": a.activity_date,
            }
            for a in activities
        ],
        "total": len(activities),
    }


# ============================================================================
# Example 6: Check Specific Permission Before Operation
# ============================================================================

@router.patch("/weeklies/{weekly_id}")
def update_weekly_report(
    weekly_id: str,
    title: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a weekly report
    Requires EDITOR permission level
    """
    weekly = db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
    if not weekly:
        raise HTTPException(status_code=404, detail="Weekly report not found")

    # Check edit permission
    if not PermissionService.can_edit_weekly_report(current_user, weekly, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this report"
        )

    # Perform update
    weekly.title = title
    db.commit()

    # Log the change
    PermissionService.log_audit(
        user_id=current_user.id,
        action="update_weekly",
        resource_type="weekly",
        resource_id=weekly_id,
        changes={"title": title},
        db=db,
    )

    return {"message": "Weekly report updated successfully"}


# ============================================================================
# Example 7: Auto-Grant Permissions
# ============================================================================

@router.post("/weeklies/{weekly_id}/auto-grant-access")
def auto_grant_access(
    weekly_id: str,
    scope: str = "department",  # "department" or "organization"
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Automatically grant access to department members or all managers
    Only admins can perform this
    """
    weekly = db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
    if not weekly:
        raise HTTPException(status_code=404, detail="Weekly report not found")

    if scope == "department":
        permissions = PermissionService.auto_grant_department_weekly_access(
            weekly_report=weekly,
            db=db,
        )
        message = f"Granted access to {len(permissions)} department members"
    elif scope == "organization":
        permissions = PermissionService.auto_grant_manager_access(
            weekly_report=weekly,
            db=db,
        )
        message = f"Granted access to {len(permissions)} managers"
    else:
        raise HTTPException(status_code=400, detail="Invalid scope")

    return {"message": message, "permissions_granted": len(permissions)}


# ============================================================================
# Example 8: File Download with Permission Check
# ============================================================================

@router.get("/attachments/{attachment_id}/download")
def download_file(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    context: dict = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    """
    Download a file with permission check
    Logs all downloads for audit trail
    """
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="File not found")

    # Check download permission
    if not PermissionService.can_download_file(current_user, attachment, db):
        # Log failed access attempt
        PermissionService.log_audit(
            user_id=current_user.id,
            action="download_file",
            resource_type="attachment",
            resource_id=attachment_id,
            status="failure",
            error_message="Permission denied",
            ip_address=context["ip_address"],
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to download this file"
        )

    # Log successful download
    PermissionService.log_audit(
        user_id=current_user.id,
        action="download_file",
        resource_type="attachment",
        resource_id=attachment_id,
        status="success",
        ip_address=context["ip_address"],
        db=db,
    )

    return {
        "file_id": attachment.id,
        "filename": attachment.original_filename,
        "size": attachment.file_size,
        "download_url": f"/files/{attachment.id}",
    }


# ============================================================================
# Example 9: Audit Trail Retrieval
# ============================================================================

@router.get("/audit-logs")
def get_audit_logs(
    resource_type: str = None,
    resource_id: str = None,
    current_user: User = Depends(get_current_admin_user),
    perm_repo: PermissionRepository = Depends(get_permission_repo),
):
    """
    Retrieve audit logs for compliance
    Only admins can access
    """
    if resource_type and resource_id:
        logs = perm_repo.get_audit_logs_by_resource(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=100,
        )
    else:
        logs = perm_repo.get_audit_logs_by_user(
            user_id=current_user.id,
            limit=100,
        )

    return {
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "status": log.status,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "total": len(logs),
    }


# ============================================================================
# Example 10: Permission History for Compliance
# ============================================================================

@router.get("/users/{user_id}/permission-history")
def get_user_permission_history(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    perm_repo: PermissionRepository = Depends(get_permission_repo),
):
    """
    Get all permission changes for a user
    Useful for compliance audits
    """
    history = perm_repo.get_user_permission_history(user_id, limit=100)

    return {
        "user_id": user_id,
        "changes": [
            {
                "id": change.id,
                "changed_by": change.changed_by_user_id,
                "resource_type": change.resource_type,
                "resource_id": change.resource_id,
                "old_level": change.old_permission_level,
                "new_level": change.new_permission_level,
                "reason": change.reason,
                "created_at": change.created_at,
            }
            for change in history
        ],
        "total": len(history),
    }


# ============================================================================
# Example 11: Bulk Permission Operations
# ============================================================================

@router.post("/weeklies/{weekly_id}/grant-bulk-access")
def grant_bulk_access(
    weekly_id: str,
    user_ids: list[str],
    permission_level: PermissionLevel = PermissionLevel.VIEWER,
    current_user: User = Depends(get_current_admin_user),
    perm_repo: PermissionRepository = Depends(get_permission_repo),
    db: Session = Depends(get_db),
):
    """
    Grant permission to multiple users at once
    More efficient than individual grants
    """
    weekly = db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
    if not weekly:
        raise HTTPException(status_code=404, detail="Weekly report not found")

    # Bulk grant
    permissions = perm_repo.bulk_grant_weekly_permission(
        weekly_id=weekly_id,
        user_ids=user_ids,
        permission_level=permission_level,
    )

    # Log bulk action
    PermissionService.log_audit(
        user_id=current_user.id,
        action="bulk_grant_permission",
        resource_type="weekly",
        resource_id=weekly_id,
        changes={
            "user_ids": user_ids,
            "permission_level": permission_level,
            "count": len(permissions),
        },
        db=db,
    )

    return {
        "message": f"Granted access to {len(permissions)} users",
        "permissions_granted": len(permissions),
    }


# ============================================================================
# Example 12: Revoke Permissions
# ============================================================================

@router.delete("/weeklies/{weekly_id}/revoke-access/{user_id}")
def revoke_access(
    weekly_id: str,
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    perm_repo: PermissionRepository = Depends(get_permission_repo),
    db: Session = Depends(get_db),
):
    """
    Revoke all permissions for a user on a resource
    """
    weekly = db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
    if not weekly:
        raise HTTPException(status_code=404, detail="Weekly report not found")

    # Revoke permissions
    perm_repo.revoke_all_permissions(
        resource_type="weekly",
        resource_id=weekly_id,
        user_id=user_id,
    )

    # Log revocation
    PermissionService.log_audit(
        user_id=current_user.id,
        action="revoke_permission",
        resource_type="weekly",
        resource_id=weekly_id,
        changes={"target_user_id": user_id},
        db=db,
    )

    return {"message": "Access revoked successfully"}
