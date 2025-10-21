"""
Signal handlers for knowledge base operations.
"""
import os
import logging
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings
from django.core.files.storage import default_storage

from .models import KnowledgeBase

logger = logging.getLogger(__name__)

@receiver(post_delete, sender=KnowledgeBase)
def delete_knowledge_base_file(sender, instance, **kwargs):
    """
    Delete the associated file when a KnowledgeBase record is deleted.
    This ensures files are cleaned up even when records are deleted through
    Django admin or other means.
    """
    if instance.file_path:
        try:
            # Try multiple approaches to ensure file deletion
            file_deleted = False
            
            # Method 1: Use Django's default storage
            if default_storage.exists(instance.file_path):
                default_storage.delete(instance.file_path)
                file_deleted = True
                logger.info(f"Deleted file using default_storage: {instance.file_path}")
            
            # Method 2: Direct file system deletion as backup
            if not file_deleted:
                # Try absolute path
                full_path = os.path.join(settings.MEDIA_ROOT, str(instance.file_path))
                if os.path.exists(full_path):
                    os.remove(full_path)
                    file_deleted = True
                    logger.info(f"Deleted file using direct path: {full_path}")
                
                # Try relative path from MEDIA_ROOT
                elif os.path.exists(str(instance.file_path)):
                    os.remove(str(instance.file_path))
                    file_deleted = True
                    logger.info(f"Deleted file using relative path: {instance.file_path}")
            
            if not file_deleted:
                logger.warning(f"File not found for deletion: {instance.file_path}")
            else:
                logger.info(f"Successfully deleted file: {instance.file_path}")
                
        except Exception as e:
            logger.error(f"Failed to delete file {instance.file_path}: {e}")
            # Don't fail the entire operation if file deletion fails
