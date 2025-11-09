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
            # Get the file path as a string (FieldFile objects need .name attribute)
            # Handle both FieldFile objects and string paths
            if hasattr(instance.file_path, 'name'):
                file_path_str = instance.file_path.name
            elif hasattr(instance.file_path, 'path'):
                file_path_str = instance.file_path.path
            else:
                file_path_str = str(instance.file_path)
            
            # Ensure we have a string, not a FieldFile object
            if not isinstance(file_path_str, str):
                file_path_str = str(file_path_str)
            
            file_deleted = False
            
            # Method 1: Use Django's default storage (works with FieldFile or string path)
            try:
                if default_storage.exists(file_path_str):
                    default_storage.delete(file_path_str)
                    file_deleted = True
                    logger.info(f"Deleted file using default_storage: {file_path_str}")
            except Exception as e:
                logger.debug(f"default_storage deletion failed, trying direct path: {e}")
            
            # Method 2: Direct file system deletion as backup
            if not file_deleted:
                # Try absolute path
                full_path = os.path.join(settings.MEDIA_ROOT, file_path_str)
                if os.path.exists(full_path):
                    os.remove(full_path)
                    file_deleted = True
                    logger.info(f"Deleted file using direct path: {full_path}")
                
                # Try relative path from MEDIA_ROOT
                elif os.path.exists(file_path_str):
                    os.remove(file_path_str)
                    file_deleted = True
                    logger.info(f"Deleted file using relative path: {file_path_str}")
            
            if not file_deleted:
                logger.warning(f"File not found for deletion: {file_path_str}")
            else:
                logger.info(f"Successfully deleted file: {file_path_str}")
                
        except Exception as e:
            logger.error(f"Failed to delete file {instance.file_path}: {e}")
            # Don't fail the entire operation if file deletion fails
