#!/bin/bash

# QWI PostgreSQL Setup Script
# This script sets up PostgreSQL database and runs migrations

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     QWI PostgreSQL Database Setup Script                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Please install PostgreSQL first."
    exit 1
fi

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Python virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "📦 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel > /dev/null
pip install -r requirements.txt > /dev/null
echo "✅ Dependencies installed"

# Load environment variables
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "📝 Please update .env with your actual values, especially:"
        echo "   - DATABASE_URL"
        echo "   - REDIS_URL"
        echo "   - SECRET_KEY"
        read -p "Continue with current .env? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Setup cancelled."
            exit 1
        fi
    fi
fi

# Source the environment file
export $(cat .env | grep -v '^#' | xargs)

# Extract database connection details from DATABASE_URL
# Format: postgresql://user:password@host:port/database
if [[ $DATABASE_URL =~ postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASSWORD="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
else
    echo "❌ Invalid DATABASE_URL format"
    exit 1
fi

echo "📊 Database Configuration:"
echo "   Host: $DB_HOST"
echo "   Port: $DB_PORT"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo ""

# Test PostgreSQL connection
echo "🔍 Testing PostgreSQL connection..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "\q" 2>/dev/null; then
    echo "✅ PostgreSQL connection successful"
else
    echo "❌ Cannot connect to PostgreSQL"
    echo "   Please verify DATABASE_URL in .env file"
    exit 1
fi

# Create database if it doesn't exist
echo "🗄️  Creating database (if not exists)..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres << EOF > /dev/null 2>&1
SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';
EOF

if [ $? -ne 0 ]; then
    PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
    echo "✅ Database created: $DB_NAME"
else
    echo "✅ Database already exists: $DB_NAME"
fi

# Create extensions
echo "🔌 Creating PostgreSQL extensions..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF > /dev/null 2>&1
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS uuid-ossp;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
EOF
echo "✅ Extensions created"

# Run Alembic migrations
echo "📡 Running database migrations..."
alembic upgrade head
if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed"
    exit 1
fi

# Initialize ACL rules
echo "🔐 Initializing ACL rules..."
python << 'PYTHON_EOF'
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, UTC

# Import models after database setup
from app.models.permissions import DepartmentRole
from app.core.database import Base

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Define ACL rules
    rules = [
        {
            "department": "Qualidade",
            "role": "Gerente Sr",
            "can_view_all_weekly": True,
            "can_edit_weekly": True,
            "can_share_activities": True,
            "can_share_files": True,
            "auto_share_files_with_department": True,
        },
        {
            "department": "Qualidade",
            "role": "Gerente PL",
            "can_view_all_weekly": True,
            "can_edit_weekly": True,
            "can_share_activities": True,
            "can_share_files": True,
            "auto_share_files_with_department": True,
        },
        {
            "department": "Qualidade",
            "role": "Gerente Jr",
            "can_view_all_weekly": True,
            "can_edit_weekly": False,
            "can_share_activities": True,
            "can_share_files": True,
            "auto_share_files_with_department": True,
        },
        {
            "department": "Qualidade",
            "role": "Chefe",
            "can_view_all_weekly": True,
            "can_edit_weekly": False,
            "can_share_activities": True,
            "can_share_files": True,
            "auto_share_files_with_department": True,
        },
        {
            "department": "Qualidade",
            "role": "Analista Sr",
            "can_view_all_weekly": False,
            "can_edit_weekly": False,
            "can_share_activities": True,
            "can_share_files": True,
            "auto_share_files_with_department": True,
        },
        {
            "department": "Qualidade",
            "role": "Analista PL",
            "can_view_all_weekly": False,
            "can_edit_weekly": False,
            "can_share_activities": True,
            "can_share_files": True,
            "auto_share_files_with_department": True,
        },
        {
            "department": "Qualidade",
            "role": "Analista Jr",
            "can_view_all_weekly": False,
            "can_edit_weekly": False,
            "can_share_activities": True,
            "can_share_files": True,
            "auto_share_files_with_department": True,
        },
    ]

    # Insert ACL rules
    added_count = 0
    for rule in rules:
        existing = db.query(DepartmentRole).filter(
            DepartmentRole.department == rule["department"],
            DepartmentRole.role == rule["role"],
        ).first()

        if not existing:
            db.add(DepartmentRole(**rule))
            added_count += 1

    db.commit()
    db.close()

    if added_count > 0:
        print(f"✅ Initialized {added_count} ACL rules")
    else:
        print("✅ ACL rules already initialized")

except Exception as e:
    print(f"⚠️  Warning: Could not initialize ACL rules: {e}")
    print("   You can initialize them later using the management script")

PYTHON_EOF

# Create uploads directory
mkdir -p uploads
chmod 755 uploads
echo "✅ Uploads directory created"

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✅ Setup Complete!                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Update .env with your production settings"
echo "2. Start the application:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Optional - Start Celery worker (in separate terminal):"
echo "   source venv/bin/activate"
echo "   celery -A app.services.celery_app worker --loglevel=info"
echo ""
echo "Database connection string:"
echo "   $DATABASE_URL"
echo ""
echo "For more information, see:"
echo "   - POSTGRES_MIGRATION_GUIDE.md"
echo "   - DEPLOYMENT_CHECKLIST.md"
echo ""
