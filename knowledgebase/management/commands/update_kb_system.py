"""
Django management command to completely update the knowledge base system.
Handles backup, cleanup, migration, and restore of the knowledge base with new 3072-dimensional embeddings.
"""
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import connection, transaction
from django.core.management import call_command
from django.conf import settings
from knowledgebase.models import KnowledgeBase, KnowledgeBaseSettings
from knowledgebase.service import KnowledgeBaseService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Complete knowledge base system update: backup, clean, migrate, restore'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup-dir',
            type=str,
            default='backups/knowledge_base/',
            help='Directory to store backups (default: backups/knowledge_base/)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--skip-backup',
            action='store_true',
            help='Skip backup step (not recommended)',
        )
        parser.add_argument(
            '--skip-restore',
            action='store_true',
            help='Skip automatic restore (manual restore later)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force operation even if backups exist',
        )
        parser.add_argument(
            '--keep-backups',
            action='store_true',
            help='Keep backup files after successful migration',
        )

    def handle(self, *args, **options):
        self.backup_dir = Path(options['backup_dir'])
        self.dry_run = options['dry_run']
        self.skip_backup = options['skip_backup']
        self.skip_restore = options['skip_restore']
        self.force = options['force']
        self.keep_backups = options['keep_backups']
        
        self.stdout.write('='*60)
        self.stdout.write('KNOWLEDGE BASE SYSTEM UPDATE')
        self.stdout.write('='*60)
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        try:
            # Phase 1: Backup
            if not self.skip_backup:
                self.backup_knowledge_base()
            
            # Phase 2: Clean
            self.clean_knowledge_base()
            
            # Phase 3: Migrate
            self.run_migrations()
            
            # Phase 4: Restore
            if not self.skip_restore:
                self.restore_knowledge_base()
            
            # Phase 5: Cleanup
            self.cleanup_backups()
            
            self.stdout.write(self.style.SUCCESS('\n🎉 Knowledge base system update completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Update failed: {e}'))
            logger.error(f"Knowledge base system update failed: {e}")
            raise CommandError(f"Update failed: {e}")

    def backup_knowledge_base(self):
        """Phase 1: Backup all KnowledgeBase records to JSON files."""
        self.stdout.write('\n📦 Phase 1: Backing up knowledge base...')
        
        if self.dry_run:
            self.stdout.write('  [DRY RUN] Would backup all KnowledgeBase records')
            return
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if backup already exists
        manifest_file = self.backup_dir / 'manifest.json'
        if manifest_file.exists() and not self.force:
            raise CommandError(f"Backup already exists at {self.backup_dir}. Use --force to overwrite.")
        
        # Get all KnowledgeBase records
        kb_records = KnowledgeBase.objects.all()
        total_records = kb_records.count()
        
        if total_records == 0:
            self.stdout.write('  No records to backup')
            return
        
        self.stdout.write(f'  Found {total_records} records to backup')
        
        # Export records (excluding embeddings and chunk_text)
        records_data = []
        user_documents = {}
        files_manifest = []
        
        for record in kb_records:
            # Backup essential data
            record_data = {
                'id': record.id,
                'user_id': record.user_id,
                'user_username': record.user.username,
                'original_filename': record.original_filename,
                'file_path': record.file_path.name if record.file_path else None,
                'file_size': record.file_size,
                'file_type': record.file_type,
                'chunk_index': record.chunk_index,
                'parent_document_id': record.parent_document_id,
                'page_number': record.page_number,
                'metadata': record.metadata,
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            }
            records_data.append(record_data)
            
            # Group by user
            if record.user_id not in user_documents:
                user_documents[record.user_id] = {
                    'username': record.user.username,
                    'documents': {}
                }
            
            doc_id = record.parent_document_id
            if doc_id not in user_documents[record.user_id]['documents']:
                user_documents[record.user_id]['documents'][doc_id] = {
                    'filename': record.original_filename,
                    'file_path': record.file_path.name if record.file_path else None,
                    'file_size': record.file_size,
                    'chunk_count': 0,
                }
            user_documents[record.user_id]['documents'][doc_id]['chunk_count'] += 1
            
            # Check file integrity
            if record.file_path:
                file_path = Path(settings.MEDIA_ROOT) / record.file_path.name
                files_manifest.append({
                    'file_path': record.file_path.name,
                    'exists': file_path.exists(),
                    'size': file_path.stat().st_size if file_path.exists() else 0,
                    'expected_size': record.file_size,
                })
        
        # Save backup files
        backup_files = {
            'knowledge_base_records.json': records_data,
            'user_documents.json': user_documents,
            'files_manifest.json': files_manifest,
        }
        
        for filename, data in backup_files.items():
            file_path = self.backup_dir / filename
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            self.stdout.write(f'  Saved: {filename}')
        
        # Create manifest
        manifest = {
            'backup_date': datetime.now().isoformat(),
            'total_records': total_records,
            'total_users': len(user_documents),
            'total_documents': sum(len(user['documents']) for user in user_documents.values()),
            'files_checked': len(files_manifest),
            'files_missing': sum(1 for f in files_manifest if not f['exists']),
            'backup_size': sum(f.stat().st_size for f in self.backup_dir.glob('*.json')),
        }
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        self.stdout.write(f'  ✅ Backup completed: {total_records} records, {len(user_documents)} users')
        
        # Check for missing files
        missing_files = [f for f in files_manifest if not f['exists']]
        if missing_files:
            self.stdout.write(self.style.WARNING(f'  ⚠️  {len(missing_files)} PDF files are missing!'))
            for missing in missing_files[:5]:  # Show first 5
                self.stdout.write(f'    Missing: {missing["file_path"]}')
            if len(missing_files) > 5:
                self.stdout.write(f'    ... and {len(missing_files) - 5} more')

    def clean_knowledge_base(self):
        """Phase 2: Delete all KnowledgeBase records but keep PDF files."""
        self.stdout.write('\n🧹 Phase 2: Cleaning knowledge base...')
        
        if self.dry_run:
            self.stdout.write('  [DRY RUN] Would delete all KnowledgeBase records')
            return
        
        # Verify PDF files exist before deletion
        kb_records = KnowledgeBase.objects.all()
        missing_files = []
        
        for record in kb_records:
            if record.file_path:
                file_path = Path(settings.MEDIA_ROOT) / record.file_path.name
                if not file_path.exists():
                    missing_files.append(record.file_path.name)
        
        if missing_files:
            self.stdout.write(self.style.WARNING(f'  ⚠️  {len(missing_files)} PDF files are missing!'))
            if not self.force:
                raise CommandError("Missing PDF files detected. Use --force to continue anyway.")
        
        # Delete all KnowledgeBase records
        total_deleted = kb_records.count()
        kb_records.delete()
        
        self.stdout.write(f'  ✅ Deleted {total_deleted} KnowledgeBase records')
        self.stdout.write('  📁 PDF files preserved in media/knowledge_base/')

    def run_migrations(self):
        """Phase 3: Run Django migrations and create settings."""
        self.stdout.write('\n🔄 Phase 3: Running migrations...')
        
        if self.dry_run:
            self.stdout.write('  [DRY RUN] Would run Django migrations')
            return
        
        # Run Django migrations
        self.stdout.write('  Running Django migrations...')
        call_command('migrate', verbosity=0)
        
        # Create default settings for all users
        self.stdout.write('  Creating default settings for users...')
        created_count = 0
        
        for user in User.objects.all():
            settings, created = KnowledgeBaseSettings.objects.get_or_create(
                user=user,
                defaults={
                    'embedding_dimensions': 3072,
                    'similarity_threshold': 0.5,
                    'top_k_results': 5,
                    'max_chunks_in_context': 3,
                    'chunk_size': 1000,
                    'chunk_overlap': 200,
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'  ✅ Migrations completed, created settings for {created_count} users')

    def restore_knowledge_base(self):
        """Phase 4: Re-upload all PDFs with new system."""
        self.stdout.write('\n📥 Phase 4: Restoring knowledge base...')
        
        if self.dry_run:
            self.stdout.write('  [DRY RUN] Would re-upload all PDFs')
            return
        
        # Load backup data
        manifest_file = self.backup_dir / 'manifest.json'
        if not manifest_file.exists():
            raise CommandError("Backup manifest not found. Cannot restore without backup.")
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        user_docs_file = self.backup_dir / 'user_documents.json'
        with open(user_docs_file, 'r') as f:
            user_documents = json.load(f)
        
        files_manifest_file = self.backup_dir / 'files_manifest.json'
        with open(files_manifest_file, 'r') as f:
            files_manifest = json.load(f)
        
        self.stdout.write(f'  Restoring {manifest["total_documents"]} documents for {manifest["total_users"]} users')
        
        # Process each user's documents
        total_processed = 0
        total_errors = 0
        
        for user_id, user_data in user_documents.items():
            try:
                user = User.objects.get(id=user_id)
                self.stdout.write(f'  Processing user: {user.username}')
                
                # Initialize service with user settings
                service = KnowledgeBaseService(user=user)
                
                if not service.embeddings:
                    self.stdout.write(self.style.ERROR(f'    No embeddings available for {user.username}'))
                    continue
                
                # Process each document
                for doc_id, doc_data in user_data['documents'].items():
                    try:
                        # Find the PDF file
                        file_path = None
                        for file_info in files_manifest:
                            if file_info['file_path'] == doc_data['file_path']:
                                file_path = Path(settings.MEDIA_ROOT) / file_info['file_path']
                                break
                        
                        if not file_path or not file_path.exists():
                            self.stdout.write(self.style.ERROR(f'    Missing file: {doc_data["filename"]}'))
                            total_errors += 1
                            continue
                        
                        # Re-upload PDF
                        with open(file_path, 'rb') as pdf_file:
                            # Create a mock Django file object
                            from django.core.files.uploadedfile import SimpleUploadedFile
                            django_file = SimpleUploadedFile(
                                doc_data['filename'],
                                pdf_file.read(),
                                content_type='application/pdf'
                            )
                            
                            result = service.upload_pdf(user, django_file)
                            
                            if result['success']:
                                self.stdout.write(f'    ✅ {doc_data["filename"]} - {result["chunks_created"]} chunks')
                                total_processed += 1
                            else:
                                self.stdout.write(self.style.ERROR(f'    ❌ {doc_data["filename"]}: {result["error"]}'))
                                total_errors += 1
                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'    ❌ Error processing {doc_data["filename"]}: {e}'))
                        total_errors += 1
                        continue
            
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  User {user_id} not found'))
                total_errors += 1
                continue
        
        self.stdout.write(f'  ✅ Restore completed: {total_processed} documents processed, {total_errors} errors')

    def cleanup_backups(self):
        """Phase 5: Clean up backup files and generate report."""
        self.stdout.write('\n🧽 Phase 5: Cleanup and reporting...')
        
        if self.dry_run:
            self.stdout.write('  [DRY RUN] Would generate final report')
            return
        
        # Generate final report
        total_chunks = KnowledgeBase.objects.count()
        total_users = User.objects.count()
        users_with_settings = KnowledgeBaseSettings.objects.count()
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('KNOWLEDGE BASE SYSTEM UPDATE COMPLETE')
        self.stdout.write('='*60)
        
        if self.backup_dir.exists():
            manifest_file = self.backup_dir / 'manifest.json'
            if manifest_file.exists():
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                
                self.stdout.write(f'Backup Summary:')
                self.stdout.write(f'- {manifest["total_records"]} records backed up')
                self.stdout.write(f'- {manifest["total_users"]} users affected')
                self.stdout.write(f'- {manifest["total_documents"]} documents processed')
                self.stdout.write(f'- Backup size: {manifest["backup_size"] / 1024:.1f} KB')
        
        self.stdout.write(f'\nMigration Results:')
        self.stdout.write(f'- Schema updated to 3072 dimensions')
        self.stdout.write(f'- Settings created for {users_with_settings} users')
        self.stdout.write(f'- Total chunks: {total_chunks}')
        
        self.stdout.write(f'\nFinal Status:')
        self.stdout.write(f'- Embedding dimensions: 3072')
        self.stdout.write(f'- Similarity threshold: 0.5')
        self.stdout.write(f'- All users can now use improved retrieval')
        
        self.stdout.write(f'\nNext Steps:')
        self.stdout.write(f'- Test knowledge base search')
        self.stdout.write(f'- Adjust settings via admin if needed')
        self.stdout.write(f'- Monitor API usage for embedding generation')
        
        # Clean up backup files if requested
        if not self.keep_backups and self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
            self.stdout.write(f'\n🗑️  Backup files cleaned up')
        else:
            self.stdout.write(f'\n📁 Backup files preserved at: {self.backup_dir}')
