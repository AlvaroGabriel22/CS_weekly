"""File Service - Business logic for file uploads and management"""
import os
import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.models import Attachment, ImageUsage
from app.repositories import AttachmentRepository
from app.core.exceptions import QWIException


class FileService:
    """Service for file upload and management"""

    # File constraints
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    ALLOWED_DOCUMENT_TYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
    ALLOWED_PRESENTATION_TYPES = {
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    }
    ALL_ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOCUMENT_TYPES | ALLOWED_PRESENTATION_TYPES

    UPLOAD_DIR = 'backend/uploads'

    def __init__(self, db: Session):
        self.db = db
        self.repo = AttachmentRepository(db)
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

    def upload_file(
        self,
        activity_id: str,
        file_content: bytes,
        original_filename: str,
        mime_type: str,
    ) -> Attachment:
        """Upload file with validation"""

        # Validate MIME type
        if mime_type not in self.ALL_ALLOWED_TYPES:
            raise QWIException(f'File type not allowed: {mime_type}')

        # Validate file size
        file_size = len(file_content)
        if file_size > self.MAX_FILE_SIZE:
            raise QWIException(f'File size exceeds {self.MAX_FILE_SIZE} bytes')

        # Determine file type
        if mime_type in self.ALLOWED_IMAGE_TYPES:
            file_type = 'image'
        elif mime_type in self.ALLOWED_DOCUMENT_TYPES:
            file_type = 'document'
        elif mime_type in self.ALLOWED_PRESENTATION_TYPES:
            file_type = 'presentation'
        else:
            raise QWIException('Unsupported file type')

        # Generate safe filename
        filename = self._generate_filename(original_filename)
        file_path = os.path.join(self.UPLOAD_DIR, filename)

        # Save file
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
        except IOError as e:
            raise QWIException(f'Failed to save file: {str(e)}')

        # Create attachment record
        attachment = self.repo.create({
            'activity_id': activity_id,
            'filename': filename,
            'original_filename': original_filename,
            'file_path': file_path,
            'file_type': file_type,
            'file_size': file_size,
            'mime_type': mime_type,
            'image_usage': ImageUsage.STORE_ONLY if file_type == 'image' else None,
        })

        return attachment

    def delete_file(self, attachment_id: str) -> bool:
        """Delete file and attachment record"""

        attachment = self.repo.read(attachment_id)
        if not attachment:
            return False

        # Delete physical file
        if os.path.exists(attachment.file_path):
            try:
                os.remove(attachment.file_path)
            except OSError:
                pass  # Continue even if file deletion fails

        # Delete record
        return self.repo.delete(attachment_id)

    def get_file_content(self, attachment_id: str) -> Optional[bytes]:
        """Get file content for download"""

        attachment = self.repo.read(attachment_id)
        if not attachment:
            return None

        try:
            with open(attachment.file_path, 'rb') as f:
                return f.read()
        except IOError:
            return None

    def get_attachment(self, attachment_id: str) -> Optional[Attachment]:
        """Get attachment metadata"""
        return self.repo.read(attachment_id)

    def get_activity_files(self, activity_id: str) -> List[Attachment]:
        """Get all files for activity"""
        return self.repo.get_by_activity(activity_id)

    def get_activity_images(self, activity_id: str) -> List[Attachment]:
        """Get image files for activity"""
        return self.repo.get_images(activity_id)

    def update_image_usage(
        self,
        attachment_id: str,
        usage: ImageUsage,
    ) -> Optional[Attachment]:
        """Update how image is used in reports"""

        attachment = self.repo.read(attachment_id)
        if not attachment:
            raise QWIException('Attachment not found')

        if attachment.file_type != 'image':
            raise QWIException('Only images can have usage settings')

        return self.repo.update(attachment_id, {'image_usage': usage})

    def update_caption(
        self,
        attachment_id: str,
        caption: str,
    ) -> Optional[Attachment]:
        """Update manual caption for image"""

        attachment = self.repo.read(attachment_id)
        if not attachment:
            raise QWIException('Attachment not found')

        return self.repo.update(attachment_id, {'manual_caption': caption})

    def get_storage_usage(self, activity_id: str) -> int:
        """Get total file size for activity"""
        return self.repo.get_total_size_for_activity(activity_id)

    def cleanup_old_files(self, days: int = 30) -> int:
        """Cleanup unprocessed files older than N days"""
        old_files = self.repo.get_old_unprocessed(days=days)

        count = 0
        for attachment in old_files:
            if self.delete_file(attachment.id):
                count += 1

        return count

    @staticmethod
    def _generate_filename(original: str) -> str:
        """Generate safe filename with UUID"""
        name, ext = os.path.splitext(original)
        # Sanitize extension
        ext = ''.join(c for c in ext if c.isalnum() or c == '.').lower()
        if not ext:
            ext = '.bin'

        return f"{uuid.uuid4()}{ext}"
