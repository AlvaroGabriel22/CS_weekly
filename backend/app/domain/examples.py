"""
Example Usage Patterns for the Domain Layer

This module demonstrates best practices for using the domain layer.
These examples can be used as reference patterns in application services.
"""

from datetime import datetime, timedelta
from app.domain import (
    # Value Objects
    UserId,
    ActivityId,
    WeeklyReportId,
    AttachmentId,
    Permission,
    Role,
    Sector,
    ActivityStatus,
    WeeklyStatus,
    AccessScope,
    Language,
    WritingProfile,
    WritingTone,
    ObjectivityLevel,
    TechnicalLevel,
    UserPreferences,
    FileMetadata,
    # Entities
    UserAggregate,
    ActivityAggregate,
    WeeklyReportAggregate,
    AttachmentAggregate,
    DepartmentAggregate,
    # Rules
    PermissionRules,
    # Events
    ActivityShared,
    ActivityCreated,
    WeeklyGenerated,
    PermissionGranted,
    # Exceptions
    PermissionDenied,
    UnauthorizedAccess,
)


# ============================================================================
# Example 1: Creating and Sharing an Activity
# ============================================================================

def example_create_and_share_activity():
    """Example: User creates activity and shares it with colleague"""

    # Create a user
    user = UserAggregate(
        user_id=UserId("user-123"),
        email="joao@company.com",
        employee_id="EMP001",
        name="João Silva",
        department="Qualidade",
        role=Role.ANALISTA_SR,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(
            writing_profile=WritingProfile(
                default_language=Language.PT,
                writing_tone=WritingTone.SPECIALIST,
            )
        ),
    )

    # Create another user to share with
    target_user = UserAggregate(
        user_id=UserId("user-456"),
        email="maria@company.com",
        employee_id="EMP002",
        name="Maria Santos",
        department="Qualidade",
        role=Role.ANALISTA_PL,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    # Create an activity
    activity = ActivityAggregate(
        activity_id=ActivityId("act-789"),
        user_id=user.user_id,
        title="Inspeção OQC",
        description="Inspeção de qualidade de saída",
        department="Qualidade",
        activity_date=datetime.now(),
        status=ActivityStatus.DRAFT,
        week_number=32,
        year=2024,
        include_in_weekly=True,
    )

    # Check if can share before sharing
    if PermissionRules.can_share_activity(user, activity, target_user):
        print("✓ User can share activity")

        # Share the activity
        activity.share_with(
            target_user_id=target_user.user_id,
            permission=Permission.VIEWER,
            by_user_id=user.user_id,
        )

        # Publish domain event (would go to event bus in real app)
        event = ActivityShared(
            activity_id=activity.activity_id,
            from_user_id=user.user_id,
            to_user_id=target_user.user_id,
            permission_level=Permission.VIEWER.value,
        )
        print(f"✓ Event published: {event}")

        # Verify target user can now view
        assert PermissionRules.can_view_activity(target_user, activity)
        print("✓ Target user can view activity")

        # Verify target user cannot edit
        assert not PermissionRules.can_edit_activity(target_user, activity)
        print("✓ Target user cannot edit activity")
    else:
        print("✗ User cannot share activity")


# ============================================================================
# Example 2: Weekly Report Generation and Sharing
# ============================================================================

def example_weekly_report_workflow():
    """Example: Generate weekly report and share with department"""

    # Create user
    user = UserAggregate(
        user_id=UserId("user-123"),
        email="joao@company.com",
        employee_id="EMP001",
        name="João Silva",
        department="Qualidade",
        role=Role.GERENTE_PL,
        sector=Sector.QM,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    # Create weekly report
    weekly = WeeklyReportAggregate(
        weekly_id=WeeklyReportId("weekly-111"),
        user_id=user.user_id,
        week_number=32,
        year=2024,
        status=WeeklyStatus.DRAFT,
        language=Language.PT,
    )

    print(f"✓ Created weekly report: {weekly.weekly_id}")

    # Transition to generating
    if weekly.can_transition_to(WeeklyStatus.GENERATING):
        weekly.transition_to(WeeklyStatus.GENERATING)
        print(f"✓ Transitioned to: {weekly.status.value}")

    # Simulate generation
    weekly.content = {"summary": "Generated content"}
    weekly.pptx_path = "/storage/reports/weekly-111.pptx"
    weekly.generated_at = datetime.now()

    # Complete generation
    if weekly.can_transition_to(WeeklyStatus.COMPLETED):
        weekly.transition_to(WeeklyStatus.COMPLETED)
        print(f"✓ Weekly report completed")

    # Grant permission to another user
    other_user = UserAggregate(
        user_id=UserId("user-456"),
        email="maria@company.com",
        employee_id="EMP002",
        name="Maria Santos",
        department="Qualidade",
        role=Role.GERENTE_JR,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    if PermissionRules.can_share_weekly(user, weekly, other_user):
        weekly.grant_permission(
            to_user_id=other_user.user_id,
            permission=Permission.VIEWER,
            access_scope=AccessScope.PERSONAL,
        )
        print(f"✓ Shared weekly with {other_user.name}")

        # Verify they can view
        assert PermissionRules.can_view_weekly(other_user, weekly)
        print("✓ Recipient can view weekly")


# ============================================================================
# Example 3: File Attachment Management
# ============================================================================

def example_file_sharing():
    """Example: Attach file to activity and share with department"""

    user = UserAggregate(
        user_id=UserId("user-123"),
        email="joao@company.com",
        employee_id="EMP001",
        name="João Silva",
        department="Qualidade",
        role=Role.ANALISTA_SR,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    activity = ActivityAggregate(
        activity_id=ActivityId("act-789"),
        user_id=user.user_id,
        title="Inspeção OQC",
        department="Qualidade",
        activity_date=datetime.now(),
        status=ActivityStatus.REGISTERED,
        week_number=32,
        year=2024,
    )

    # Create attachment
    attachment = AttachmentAggregate(
        attachment_id=AttachmentId("att-001"),
        activity_id=activity.activity_id,
        user_id=user.user_id,
        metadata=FileMetadata(
            filename="inspection_report_2024_32.pdf",
            original_filename="Relatório de Inspeção.pdf",
            file_path="/storage/files/inspection_report_2024_32.pdf",
            file_type="pdf",
            file_size=2048576,
            mime_type="application/pdf",
        ),
    )

    print(f"✓ Created attachment: {attachment.attachment_id}")

    # Add to activity
    activity.add_attachment(attachment.attachment_id)
    print(f"✓ Attached file to activity")

    # Share with colleague
    colleague = UserAggregate(
        user_id=UserId("user-456"),
        email="maria@company.com",
        employee_id="EMP002",
        name="Maria Santos",
        department="Qualidade",
        role=Role.ANALISTA_PL,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    if PermissionRules.can_share_attachment(user, attachment, colleague):
        attachment.share_with_user(
            target_user_id=colleague.user_id,
            permission=Permission.VIEWER,
            by_user_id=user.user_id,
        )
        print(f"✓ Shared file with {colleague.name}")

    # Share with entire department
    attachment.share_with_department(
        department_name="Qualidade",
        permission=Permission.VIEWER,
        by_user_id=user.user_id,
    )
    print(f"✓ Shared file with Qualidade department")

    # Record download
    attachment.record_download()
    print(f"✓ Download recorded (count: {attachment.download_count})")


# ============================================================================
# Example 4: Permission Checks and Filtering
# ============================================================================

def example_permission_filtering():
    """Example: Filter activities based on user permissions"""

    user = UserAggregate(
        user_id=UserId("user-123"),
        email="joao@company.com",
        employee_id="EMP001",
        name="João Silva",
        department="Qualidade",
        role=Role.ANALISTA_SR,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    # Create activities
    owned_activity = ActivityAggregate(
        activity_id=ActivityId("act-001"),
        user_id=user.user_id,  # User owns this
        title="My Activity",
        department="Qualidade",
        activity_date=datetime.now(),
        status=ActivityStatus.REGISTERED,
        week_number=32,
        year=2024,
    )

    shared_activity = ActivityAggregate(
        activity_id=ActivityId("act-002"),
        user_id=UserId("user-999"),  # Another user owns this
        title="Shared Activity",
        department="Qualidade",
        activity_date=datetime.now(),
        status=ActivityStatus.REGISTERED,
        week_number=32,
        year=2024,
    )
    # Share with our user
    shared_activity.share_with(
        target_user_id=user.user_id,
        permission=Permission.VIEWER,
        by_user_id=UserId("user-999"),
    )

    private_activity = ActivityAggregate(
        activity_id=ActivityId("act-003"),
        user_id=UserId("user-888"),  # Another user
        title="Private Activity",
        department="Qualidade",
        activity_date=datetime.now(),
        status=ActivityStatus.REGISTERED,
        week_number=32,
        year=2024,
    )
    # NOT shared with our user

    all_activities = [owned_activity, shared_activity, private_activity]

    # Get accessible activities
    accessible = PermissionRules.get_accessible_activities(user, all_activities)
    print(f"✓ User can access {len(accessible)} of {len(all_activities)} activities")
    assert len(accessible) == 2  # owned + shared

    # Filter by permission level
    editable = PermissionRules.filter_activities_by_permission(
        user, all_activities, permission=Permission.EDITOR
    )
    print(f"✓ User can edit {len(editable)} activities")
    assert len(editable) == 1  # only owned


# ============================================================================
# Example 5: Status Transitions and Validation
# ============================================================================

def example_activity_lifecycle():
    """Example: Activity lifecycle with status transitions"""

    user = UserAggregate(
        user_id=UserId("user-123"),
        email="joao@company.com",
        employee_id="EMP001",
        name="João Silva",
        department="Qualidade",
        role=Role.ANALISTA_SR,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    # Create activity in DRAFT status
    activity = ActivityAggregate(
        activity_id=ActivityId("act-001"),
        user_id=user.user_id,
        title="New Activity",
        department="Qualidade",
        activity_date=datetime.now(),
        status=ActivityStatus.DRAFT,
        week_number=32,
        year=2024,
    )

    print(f"✓ Created activity with status: {activity.status.value}")

    # Transition DRAFT -> REGISTERED
    if activity.can_transition_to(ActivityStatus.REGISTERED):
        activity.transition_to(ActivityStatus.REGISTERED)
        print(f"✓ Transitioned to: {activity.status.value}")
    else:
        print("✗ Cannot transition to REGISTERED")

    # Transition REGISTERED -> PROCESSED
    if activity.can_transition_to(ActivityStatus.PROCESSED):
        activity.transition_to(ActivityStatus.PROCESSED)
        print(f"✓ Transitioned to: {activity.status.value}")

    # Try invalid transition (PROCESSED -> DRAFT)
    if activity.can_transition_to(ActivityStatus.DRAFT):
        print("✗ Invalid transition allowed!")
    else:
        print("✓ Invalid transition prevented")


# ============================================================================
# Example 6: Error Handling
# ============================================================================

def example_error_handling():
    """Example: Proper error handling with domain exceptions"""

    user = UserAggregate(
        user_id=UserId("user-123"),
        email="joao@company.com",
        employee_id="EMP001",
        name="João Silva",
        department="Qualidade",
        role=Role.ANALISTA_JR,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    activity = ActivityAggregate(
        activity_id=ActivityId("act-001"),
        user_id=UserId("user-999"),  # Different user owns this
        title="Activity",
        department="Qualidade",
        activity_date=datetime.now(),
        status=ActivityStatus.DRAFT,
        week_number=32,
        year=2024,
    )

    # Try to view without permission
    try:
        activity.assert_can_view_by(user.user_id)
        print("✗ Should have raised UnauthorizedAccess")
    except UnauthorizedAccess as e:
        print(f"✓ Caught {e.error_code}: {e.message}")

    # Try to share with self
    try:
        activity.share_with(
            target_user_id=user.user_id,
            permission=Permission.VIEWER,
            by_user_id=user.user_id,
        )
        print("✗ Should have raised CannotShareWithSelf")
    except Exception as e:
        print(f"✓ Caught {type(e).__name__}: Cannot share with self")


# ============================================================================
# Example 7: Department Management
# ============================================================================

def example_department_operations():
    """Example: Department aggregate operations"""

    from app.domain import DepartmentId

    dept = DepartmentAggregate(
        department_id=DepartmentId("dept-qa"),
        name="Qualidade",
        description="Quality Assurance Department",
    )

    user1 = UserAggregate(
        user_id=UserId("user-001"),
        email="user1@company.com",
        employee_id="EMP001",
        name="User One",
        department="Qualidade",
        role=Role.ANALISTA_SR,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    user2 = UserAggregate(
        user_id=UserId("user-002"),
        email="user2@company.com",
        employee_id="EMP002",
        name="User Two",
        department="Qualidade",
        role=Role.ANALISTA_PL,
        sector=Sector.QA,
        is_active=True,
        is_admin=False,
        preferences=UserPreferences(writing_profile=WritingProfile()),
    )

    # Add users to department
    dept.add_user(user1.user_id)
    dept.add_user(user2.user_id)
    print(f"✓ Department has {dept.user_count()} users")

    # Share resource with department
    dept.share_resource("weekly-111", Permission.VIEWER)
    print("✓ Shared weekly report with department")

    # Remove user
    dept.remove_user(user1.user_id)
    print(f"✓ Removed user, department now has {dept.user_count()} users")


# ============================================================================
# Run Examples
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DOMAIN LAYER USAGE EXAMPLES")
    print("=" * 70)

    print("\n[1] Creating and Sharing an Activity")
    print("-" * 70)
    example_create_and_share_activity()

    print("\n[2] Weekly Report Generation and Sharing")
    print("-" * 70)
    example_weekly_report_workflow()

    print("\n[3] File Attachment Management")
    print("-" * 70)
    example_file_sharing()

    print("\n[4] Permission Checks and Filtering")
    print("-" * 70)
    example_permission_filtering()

    print("\n[5] Activity Lifecycle Transitions")
    print("-" * 70)
    example_activity_lifecycle()

    print("\n[6] Error Handling")
    print("-" * 70)
    example_error_handling()

    print("\n[7] Department Management")
    print("-" * 70)
    example_department_operations()

    print("\n" + "=" * 70)
    print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
    print("=" * 70)
