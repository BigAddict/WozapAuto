"""
Django management command to regenerate embeddings for knowledge base documents.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from knowledgebase.models import KnowledgeBase, KnowledgeBaseSettings
from knowledgebase.service import KnowledgeBaseService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Regenerate embeddings for knowledge base documents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Regenerate for specific user (username)',
        )
        parser.add_argument(
            '--document-id',
            type=str,
            help='Regenerate specific document by parent_document_id',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be regenerated without doing it',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Process N chunks at a time (default: 10)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate even if embeddings exist',
        )

    def handle(self, *args, **options):
        user_filter = options['user']
        document_id = options['document_id']
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        force = options['force']

        self.stdout.write('Starting embedding regeneration...')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Build queryset
        queryset = KnowledgeBase.objects.all()
        
        if user_filter:
            try:
                user = User.objects.get(username=user_filter)
                queryset = queryset.filter(user=user)
                self.stdout.write(f'Filtering for user: {user.username}')
            except User.DoesNotExist:
                raise CommandError(f'User "{user_filter}" does not exist')
        
        if document_id:
            queryset = queryset.filter(parent_document_id=document_id)
            self.stdout.write(f'Filtering for document: {document_id}')

        # Filter out chunks that already have embeddings (unless force is used)
        if not force:
            queryset = queryset.filter(embedding__isnull=True)
            self.stdout.write('Only processing chunks without embeddings (use --force to regenerate all)')

        total_chunks = queryset.count()
        self.stdout.write(f'Found {total_chunks} chunks to process')

        if total_chunks == 0:
            self.stdout.write(self.style.SUCCESS('No chunks need regeneration'))
            return

        # Group by user for settings loading
        users_to_process = set(queryset.values_list('user', flat=True))
        self.stdout.write(f'Processing for {len(users_to_process)} users')

        processed_count = 0
        error_count = 0
        skipped_count = 0

        # Process in batches by user
        for user_id in users_to_process:
            try:
                user = User.objects.get(id=user_id)
                self.stdout.write(f'\nProcessing user: {user.username}')
                
                # Initialize service with user settings
                service = KnowledgeBaseService(user=user)
                
                if not service.embeddings:
                    self.stdout.write(
                        self.style.ERROR(f'No embeddings available for user {user.username}')
                    )
                    continue
                
                # Get user's chunks
                user_chunks = queryset.filter(user=user)
                user_chunk_count = user_chunks.count()
                self.stdout.write(f'  Processing {user_chunk_count} chunks for {user.username}')
                
                # Process in batches
                for i in range(0, user_chunk_count, batch_size):
                    batch = user_chunks[i:i + batch_size]
                    
                    if dry_run:
                        self.stdout.write(f'  [DRY RUN] Would process batch {i//batch_size + 1}: {len(batch)} chunks')
                        processed_count += len(batch)
                        continue
                    
                    # Process batch
                    with transaction.atomic():
                        for chunk in batch:
                            try:
                                # Generate new embedding
                                embedding_vector = service.embeddings.embed_query(chunk.chunk_text)
                                
                                # Update chunk
                                chunk.embedding = embedding_vector
                                chunk.save(update_fields=['embedding'])
                                
                                processed_count += 1
                                
                                if processed_count % 10 == 0:
                                    self.stdout.write(f'  Processed {processed_count}/{total_chunks} chunks...')
                                    
                            except Exception as e:
                                error_count += 1
                                logger.error(f'Error processing chunk {chunk.id}: {e}')
                                self.stdout.write(
                                    self.style.ERROR(f'  Error processing chunk {chunk.id}: {e}')
                                )
                                continue
                
                self.stdout.write(
                    self.style.SUCCESS(f'  Completed user {user.username}')
                )
                
            except Exception as e:
                error_count += 1
                logger.error(f'Error processing user {user_id}: {e}')
                self.stdout.write(
                    self.style.ERROR(f'Error processing user {user_id}: {e}')
                )
                continue

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('REGENERATION SUMMARY')
        self.stdout.write('='*50)
        
        if dry_run:
            self.stdout.write(f'[DRY RUN] Would have processed: {processed_count} chunks')
        else:
            self.stdout.write(f'Successfully processed: {processed_count} chunks')
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Errors encountered: {error_count}'))
        
        if skipped_count > 0:
            self.stdout.write(f'Skipped: {skipped_count} chunks')
        
        if not dry_run and processed_count > 0:
            self.stdout.write(
                self.style.SUCCESS('Embedding regeneration completed successfully!')
            )
        elif dry_run:
            self.stdout.write(
                self.style.WARNING('Dry run completed. Use without --dry-run to apply changes.')
            )
