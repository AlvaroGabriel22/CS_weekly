"""Custom Pydantic validators"""
from pydantic import field_validator, EmailStr
from datetime import datetime


class EmailValidator:
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError('Invalid email')
        return v.lower().strip()


class PasswordValidator:
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class TitleValidator:
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip() or len(v) > 500:
            raise ValueError('Title must be 1-500 characters')
        return v.strip()


class DateValidator:
    @field_validator('activity_date')
    @classmethod
    def validate_date(cls, v: datetime) -> datetime:
        if v > datetime.now():
            raise ValueError('Date cannot be in future')
        return v


class TagsValidator:
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: list) -> list:
        if len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        return list(set(v))  # Deduplicate
