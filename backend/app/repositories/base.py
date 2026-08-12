"""Base Repository with generic CRUD operations"""
from typing import Generic, TypeVar, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from app.core.database import Base

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """Generic repository for CRUD operations"""

    def __init__(self, session: Session, model: type[T]):
        self.session = session
        self.model = model

    def create(self, obj_in: Dict[str, Any]) -> T:
        """Create a new record"""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def read(self, id: str) -> Optional[T]:
        """Get record by ID"""
        return self.session.query(self.model).filter(self.model.id == id).first()

    def read_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all records with pagination"""
        return (
            self.session.query(self.model)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(self, id: str, obj_in: Dict[str, Any]) -> Optional[T]:
        """Update a record"""
        db_obj = self.read(id)
        if not db_obj:
            return None

        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def delete(self, id: str) -> bool:
        """Hard delete a record"""
        db_obj = self.read(id)
        if not db_obj:
            return False

        self.session.delete(db_obj)
        self.session.commit()
        return True

    def soft_delete(self, id: str) -> bool:
        """Soft delete using is_active flag"""
        db_obj = self.read(id)
        if not db_obj:
            return False

        if hasattr(db_obj, 'is_active'):
            db_obj.is_active = False
            self.session.commit()
            return True

        return False

    def exists(self, **filters) -> bool:
        """Check if record exists with filters"""
        query = self.session.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        return query.first() is not None

    def count(self, **filters) -> int:
        """Count records with optional filters"""
        query = self.session.query(func.count(self.model.id))
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        return query.scalar() or 0

    def get_by_filters(self, **filters) -> List[T]:
        """Get records by multiple filters"""
        query = self.session.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        return query.all()

    def get_by_filter(self, **filters) -> Optional[T]:
        """Get single record by filters"""
        query = self.session.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        return query.first()

    def get_paginated(
        self,
        skip: int = 0,
        limit: int = 50,
        order_by: Optional[str] = None,
        descending: bool = True,
        **filters
    ) -> tuple[List[T], int]:
        """Get paginated records with filters and ordering"""
        query = self.session.query(self.model)

        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        # Count total
        total = query.count()

        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            if descending:
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(order_column)

        # Apply pagination
        items = query.offset(skip).limit(limit).all()

        return items, total

    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[T]:
        """Create multiple records"""
        db_objects = [self.model(**obj) for obj in objects]
        self.session.add_all(db_objects)
        self.session.commit()
        return db_objects

    def bulk_update(self, updates: List[tuple[str, Dict[str, Any]]]) -> int:
        """Update multiple records: [(id, update_dict), ...]"""
        count = 0
        for obj_id, update_data in updates:
            if self.update(obj_id, update_data):
                count += 1
        return count

    def bulk_delete(self, ids: List[str]) -> int:
        """Delete multiple records"""
        count = 0
        for obj_id in ids:
            if self.delete(obj_id):
                count += 1
        return count

    def bulk_soft_delete(self, ids: List[str]) -> int:
        """Soft delete multiple records"""
        count = 0
        for obj_id in ids:
            if self.soft_delete(obj_id):
                count += 1
        return count
