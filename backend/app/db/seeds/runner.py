"""Seed data runner - executes all seed generators"""
from sqlalchemy.orm import Session
from app.db.seeds.users import seed_users
from app.db.seeds.activities import seed_activities, seed_varied_activities
from app.models import User, Activity


def run_all_seeds(session: Session) -> dict:
    """Run all seed data generators"""
    print("🌱 Starting seed data generation...")

    # Clear existing data (careful in production!)
    print("  ⚠️  Clearing existing data...")
    session.query(Activity).delete()
    session.query(User).delete()
    session.commit()

    # Seed users
    print("  👤 Seeding users...")
    users = seed_users(session)
    print(f"    ✓ Created {len(users)} users")

    # Seed activities for each user
    print("  📋 Seeding activities...")
    total_activities = 0
    for user in users:
        # Create standard activities
        activities = seed_activities(session, user.id, count=7)
        total_activities += len(activities)

        # Create varied activities for some users
        if user.employee_id in ['EMP-001', 'EMP-002']:
            varied = seed_varied_activities(session, user.id)
            total_activities += len(varied)

    print(f"    ✓ Created {total_activities} activities")

    print("✅ Seed data generation complete!\n")

    return {
        'users_created': len(users),
        'activities_created': total_activities,
    }


if __name__ == '__main__':
    from app.core.database import SessionLocal, engine, Base

    # Create tables
    print("Creating database schema...")
    Base.metadata.create_all(bind=engine)
    print("✓ Schema created\n")

    # Run seeds
    session = SessionLocal()
    try:
        results = run_all_seeds(session)
        print(f"📊 Results: {results}")
    finally:
        session.close()
