"""Seed data generators for activities"""
from datetime import datetime, timedelta, UTC
from app.models import Activity, ActivityStatus
from app.core.dates import calculate_week_number


def create_test_activities(user_id: str, start_date: datetime | None = None) -> list[dict]:
    """Generate test activity data for a user"""
    if start_date is None:
        start_date = datetime.now(UTC)

    # Create activities for the current week
    activities = []
    for i in range(7):  # One activity per day
        activity_date = start_date + timedelta(days=i)
        week_num, year = calculate_week_number(activity_date)

        activity = {
            'user_id': user_id,
            'title': f'Test Activity {i+1}',
            'description': f'Description for test activity {i+1}',
            'project': f'Project-{i+1}',
            'category': 'Testing',
            'department': 'Qualidade',
            'activity_date': activity_date,
            'tags': ['test', f'day-{i+1}'],
            'notes': f'Test notes for activity {i+1}',
            'include_in_weekly': True,
            'status': ActivityStatus.REGISTERED,
            'week_number': week_num,
            'year': year,
        }
        activities.append(activity)

    return activities


def seed_activities(session, user_id: str, count: int = 7) -> list[Activity]:
    """Create and persist test activities"""
    activities = []
    activity_data_list = create_test_activities(user_id)[:count]

    for activity_data in activity_data_list:
        activity = Activity(**activity_data)
        session.add(activity)
        activities.append(activity)

    session.commit()
    return activities


def create_varied_activities(user_id: str) -> list[dict]:
    """Generate diverse test activities with different statuses"""
    base_date = datetime.now(UTC)
    activities = []

    statuses = [
        ActivityStatus.DRAFT,
        ActivityStatus.REGISTERED,
        ActivityStatus.PROCESSED,
        ActivityStatus.USED_IN_REPORT,
    ]

    projects = ['Project A', 'Project B', 'Project C', 'Project D']
    categories = ['Bug Fix', 'Feature', 'Testing', 'Documentation', 'Performance']

    for i, status in enumerate(statuses):
        for j, category in enumerate(categories):
            activity_date = base_date + timedelta(days=(i * 5) + j)
            week_num, year = calculate_week_number(activity_date)

            activity = {
                'user_id': user_id,
                'title': f'{category} in {projects[i % len(projects)]}',
                'description': f'Activity {i}-{j}: {category} work',
                'project': projects[i % len(projects)],
                'category': category,
                'department': 'Qualidade',
                'activity_date': activity_date,
                'tags': [category.lower(), projects[i % len(projects)].lower()],
                'notes': f'Test notes for {category}',
                'include_in_weekly': status != ActivityStatus.DRAFT,
                'status': status,
                'week_number': week_num,
                'year': year,
            }
            activities.append(activity)

    return activities


def seed_varied_activities(session, user_id: str) -> list[Activity]:
    """Create and persist diverse test activities"""
    activities = []
    activity_data_list = create_varied_activities(user_id)

    for activity_data in activity_data_list:
        activity = Activity(**activity_data)
        session.add(activity)
        activities.append(activity)

    session.commit()
    return activities
