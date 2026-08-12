"""Domain-level exceptions representing business rule violations"""


class DomainException(Exception):
    """Base exception for all domain-level errors"""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__


# ============================================================================
# Permission and Access Exceptions
# ============================================================================

class PermissionDenied(DomainException):
    """User does not have permission to perform the action"""

    def __init__(self, user_id: str, action: str, resource: str):
        message = f"User {user_id} is not permitted to {action} {resource}"
        super().__init__(message, "PERMISSION_DENIED")
        self.user_id = user_id
        self.action = action
        self.resource = resource


class UnauthorizedAccess(DomainException):
    """User is not authorized to access this resource"""

    def __init__(self, user_id: str, resource_id: str, resource_type: str):
        message = f"User {user_id} has no access to {resource_type} {resource_id}"
        super().__init__(message, "UNAUTHORIZED_ACCESS")
        self.user_id = user_id
        self.resource_id = resource_id
        self.resource_type = resource_type


class CannotShareWithSelf(DomainException):
    """Cannot share a resource with the same user"""

    def __init__(self, user_id: str, resource_id: str):
        message = f"Cannot share resource {resource_id} with self (user {user_id})"
        super().__init__(message, "CANNOT_SHARE_WITH_SELF")
        self.user_id = user_id
        self.resource_id = resource_id


class InsufficientPermissions(DomainException):
    """User has insufficient permission level for the action"""

    def __init__(self, user_id: str, current_level: str, required_level: str):
        message = f"User {user_id} has {current_level} but needs {required_level}"
        super().__init__(message, "INSUFFICIENT_PERMISSIONS")
        self.user_id = user_id
        self.current_level = current_level
        self.required_level = required_level


class PermissionExpired(DomainException):
    """Permission has expired"""

    def __init__(self, permission_id: str):
        message = f"Permission {permission_id} has expired"
        super().__init__(message, "PERMISSION_EXPIRED")
        self.permission_id = permission_id


# ============================================================================
# User and Identity Exceptions
# ============================================================================

class UserNotActive(DomainException):
    """User account is not active"""

    def __init__(self, user_id: str):
        message = f"User {user_id} is not active"
        super().__init__(message, "USER_NOT_ACTIVE")
        self.user_id = user_id


class UserAlreadyExists(DomainException):
    """User with this identifier already exists"""

    def __init__(self, user_id: str, identifier: str):
        message = f"User {identifier} already exists as {user_id}"
        super().__init__(message, "USER_ALREADY_EXISTS")
        self.user_id = user_id
        self.identifier = identifier


class UserNotFound(DomainException):
    """User does not exist"""

    def __init__(self, user_id: str):
        message = f"User {user_id} not found"
        super().__init__(message, "USER_NOT_FOUND")
        self.user_id = user_id


class InvalidEmail(DomainException):
    """Email address is invalid"""

    def __init__(self, email: str):
        message = f"Email {email} is invalid"
        super().__init__(message, "INVALID_EMAIL")
        self.email = email


class InvalidRole(DomainException):
    """User role is invalid"""

    def __init__(self, role: str, available_roles: list[str]):
        message = f"Role {role} is not valid. Available: {', '.join(available_roles)}"
        super().__init__(message, "INVALID_ROLE")
        self.role = role
        self.available_roles = available_roles


# ============================================================================
# Activity Exceptions
# ============================================================================

class ActivityNotFound(DomainException):
    """Activity does not exist"""

    def __init__(self, activity_id: str):
        message = f"Activity {activity_id} not found"
        super().__init__(message, "ACTIVITY_NOT_FOUND")
        self.activity_id = activity_id


class CannotModifyActivity(DomainException):
    """Activity cannot be modified in current state"""

    def __init__(self, activity_id: str, reason: str):
        message = f"Cannot modify activity {activity_id}: {reason}"
        super().__init__(message, "CANNOT_MODIFY_ACTIVITY")
        self.activity_id = activity_id
        self.reason = reason


class InvalidActivityStatus(DomainException):
    """Activity status transition is invalid"""

    def __init__(self, activity_id: str, current_status: str, target_status: str):
        message = f"Cannot transition activity {activity_id} from {current_status} to {target_status}"
        super().__init__(message, "INVALID_ACTIVITY_STATUS")
        self.activity_id = activity_id
        self.current_status = current_status
        self.target_status = target_status


class ActivityAlreadyShared(DomainException):
    """Activity is already shared with this user"""

    def __init__(self, activity_id: str, with_user_id: str):
        message = f"Activity {activity_id} is already shared with {with_user_id}"
        super().__init__(message, "ACTIVITY_ALREADY_SHARED")
        self.activity_id = activity_id
        self.with_user_id = with_user_id


# ============================================================================
# Weekly Report Exceptions
# ============================================================================

class WeeklyReportNotFound(DomainException):
    """Weekly report does not exist"""

    def __init__(self, weekly_id: str):
        message = f"Weekly report {weekly_id} not found"
        super().__init__(message, "WEEKLY_REPORT_NOT_FOUND")
        self.weekly_id = weekly_id


class WeeklyAlreadyExists(DomainException):
    """Weekly report for this week/year already exists for the user"""

    def __init__(self, user_id: str, week_number: int, year: int):
        message = f"Weekly report for user {user_id} already exists for week {week_number}/{year}"
        super().__init__(message, "WEEKLY_ALREADY_EXISTS")
        self.user_id = user_id
        self.week_number = week_number
        self.year = year


class CannotGenerateWeekly(DomainException):
    """Weekly report cannot be generated"""

    def __init__(self, weekly_id: str, reason: str):
        message = f"Cannot generate weekly report {weekly_id}: {reason}"
        super().__init__(message, "CANNOT_GENERATE_WEEKLY")
        self.weekly_id = weekly_id
        self.reason = reason


class InvalidWeeklyStatus(DomainException):
    """Weekly status transition is invalid"""

    def __init__(self, weekly_id: str, current_status: str, target_status: str):
        message = f"Cannot transition weekly {weekly_id} from {current_status} to {target_status}"
        super().__init__(message, "INVALID_WEEKLY_STATUS")
        self.weekly_id = weekly_id
        self.current_status = current_status
        self.target_status = target_status


# ============================================================================
# Attachment and File Exceptions
# ============================================================================

class AttachmentNotFound(DomainException):
    """Attachment does not exist"""

    def __init__(self, attachment_id: str):
        message = f"Attachment {attachment_id} not found"
        super().__init__(message, "ATTACHMENT_NOT_FOUND")
        self.attachment_id = attachment_id


class InvalidFileSize(DomainException):
    """File size is invalid"""

    def __init__(self, file_size: int, max_size: int):
        message = f"File size {file_size} exceeds maximum {max_size}"
        super().__init__(message, "INVALID_FILE_SIZE")
        self.file_size = file_size
        self.max_size = max_size


class InvalidFileType(DomainException):
    """File type is not allowed"""

    def __init__(self, file_type: str, allowed_types: list[str]):
        message = f"File type {file_type} not allowed. Allowed: {', '.join(allowed_types)}"
        super().__init__(message, "INVALID_FILE_TYPE")
        self.file_type = file_type
        self.allowed_types = allowed_types


class FileAlreadyShared(DomainException):
    """File is already shared with the target"""

    def __init__(self, attachment_id: str, target: str):
        message = f"File {attachment_id} is already shared with {target}"
        super().__init__(message, "FILE_ALREADY_SHARED")
        self.attachment_id = attachment_id
        self.target = target


# ============================================================================
# Department Exceptions
# ============================================================================

class DepartmentNotFound(DomainException):
    """Department does not exist"""

    def __init__(self, department_id: str):
        message = f"Department {department_id} not found"
        super().__init__(message, "DEPARTMENT_NOT_FOUND")
        self.department_id = department_id


class InvalidDepartment(DomainException):
    """Department is invalid"""

    def __init__(self, department_name: str):
        message = f"Department {department_name} is invalid"
        super().__init__(message, "INVALID_DEPARTMENT")
        self.department_name = department_name


class UserNotInDepartment(DomainException):
    """User is not a member of the department"""

    def __init__(self, user_id: str, department_name: str):
        message = f"User {user_id} is not a member of {department_name}"
        super().__init__(message, "USER_NOT_IN_DEPARTMENT")
        self.user_id = user_id
        self.department_name = department_name


# ============================================================================
# Validation Exceptions
# ============================================================================

class InvalidDateRange(DomainException):
    """Date range is invalid"""

    def __init__(self, start_date: str, end_date: str, reason: str):
        message = f"Invalid date range {start_date} to {end_date}: {reason}"
        super().__init__(message, "INVALID_DATE_RANGE")
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason


class InvalidWeekRange(DomainException):
    """Week range is invalid"""

    def __init__(self, week_number: int, year: int, reason: str):
        message = f"Invalid week W{week_number:02d}/{year}: {reason}"
        super().__init__(message, "INVALID_WEEK_RANGE")
        self.week_number = week_number
        self.year = year
        self.reason = reason


class BusinessRuleViolation(DomainException):
    """A business rule has been violated"""

    def __init__(self, rule_name: str, message: str):
        full_message = f"Business rule '{rule_name}' violated: {message}"
        super().__init__(full_message, "BUSINESS_RULE_VIOLATION")
        self.rule_name = rule_name
