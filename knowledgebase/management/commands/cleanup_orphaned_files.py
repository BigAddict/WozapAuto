"""
Django management command to cleanup orphaned knowledge base files.
This removes files that exist on disk but have no corresponding database records.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import default_storage
from knowledgebase.models import KnowledgeBase
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleanup orphaned knowledge base files (files without database records)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write("Starting orphaned file cleanup...")
        
        # Get all file paths from database
        db_file_paths = set()
        for kb_record in KnowledgeBase.objects.all():
            if kb_record.file_path:
                db_file_paths.add(str(kb_record.file_path))
        
        self.stdout.write(f"Found {len(db_file_paths)} files referenced in database")
        
        # Find all files in the knowledge base directory
        kb_dir = os.path.join(settings.MEDIA_ROOT, 'knowledge_base')
        orphaned_files = []
        
        if os.path.exists(kb_dir):
            for root, dirs, files in os.walk(kb_dir):
                for file in files:
                    # Get relative path from MEDIA_ROOT
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, settings.MEDIA_ROOT)
                    
                    # Check if this file is referenced in database
                    if rel_path not in db_file_paths:
                        orphaned_files.append(full_path)
                        if verbose:
                            self.stdout.write(f"  Orphaned: {rel_path}")
        
        if not orphaned_files:
            self.stdout.write("No orphaned files found.")
            return
        
        self.stdout.write(f"Found {len(orphaned_files)} orphaned files:")
        
        total_size = 0
        for file_path in orphaned_files:
            try:
                file_size = os.path.getsize(file_path)
                total_size += file_size
                rel_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                self.stdout.write(f"  {rel_path} ({file_size} bytes)")
            except OSError:
                self.stdout.write(f"  {file_path} (size unknown)")
        
        self.stdout.write(f"Total size: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"Dry run complete. Would delete {len(orphaned_files)} files.")
            )
            return
        
        # Actually delete the files
        deleted_count = 0
        failed_count = 0
        
        for file_path in orphaned_files:
            try:
                os.remove(file_path)
                deleted_count += 1
                rel_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                self.stdout.write(f"Deleted: {rel_path}")
            except OSError as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Failed to delete {file_path}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup complete. Deleted {deleted_count} files, "
                f"failed to delete {failed_count} files."
            )
        )
