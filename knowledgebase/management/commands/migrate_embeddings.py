"""
Django management command to help with knowledge base system management.
This is a helper command - use 'update_kb_system' for complete migration.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import connection
from knowledgebase.models import KnowledgeBase, KnowledgeBaseSettings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Helper commands for knowledge base system management'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check current embedding status without making changes',
        )
        parser.add_argument(
            '--create-settings',
            action='store_true',
            help='Create default settings for all users',
        )

    def handle(self, *args, **options):
        if options['check']:
            self.check_embedding_status()
        elif options['create_settings']:
            self.create_default_settings()
        else:
            self.show_migration_help()

    def check_embedding_status(self):
        """Check the current status of embeddings in the database."""
        self.stdout.write('Checking embedding status...')
        
        # Check total chunks
        total_chunks = KnowledgeBase.objects.count()
        chunks_with_embeddings = KnowledgeBase.objects.filter(embedding__isnull=False).count()
        chunks_without_embeddings = total_chunks - chunks_with_embeddings
        
        self.stdout.write(f'Total chunks: {total_chunks}')
        self.stdout.write(f'Chunks with embeddings: {chunks_with_embeddings}')
        self.stdout.write(f'Chunks without embeddings: {chunks_without_embeddings}')
        
        # Check embedding dimensions if any exist
        if chunks_with_embeddings > 0:
            with connection.cursor() as cursor:
                # Use pgvector-specific function to get dimensions
                cursor.execute("""
                    SELECT vector_dims(embedding) as dimensions, COUNT(*) as count
                    FROM knowledgebase_knowledgebase 
                    WHERE embedding IS NOT NULL
                    GROUP BY vector_dims(embedding)
                    ORDER BY dimensions
                """)
                results = cursor.fetchall()
                
                self.stdout.write('\nEmbedding dimensions breakdown:')
                for dimensions, count in results:
                    self.stdout.write(f'  {dimensions} dimensions: {count} chunks')
        
        # Check users with settings
        users_with_settings = KnowledgeBaseSettings.objects.count()
        total_users = User.objects.count()
        
        self.stdout.write(f'\nUsers with knowledge base settings: {users_with_settings}/{total_users}')
        
        if chunks_with_embeddings > 0:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  You have existing embeddings that need to be regenerated!'
                )
            )
            self.stdout.write(
                'Run: python manage.py regenerate_embeddings --force'
            )

    def create_default_settings(self):
        """Create default settings for all users who don't have them."""
        self.stdout.write('Creating default settings for users...')
        
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
                self.stdout.write(f'Created settings for user: {user.username}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Created settings for {created_count} users')
        )

    def show_migration_help(self):
        """Show help for the migration process."""
        self.stdout.write('='*60)
        self.stdout.write('KNOWLEDGE BASE SYSTEM MANAGEMENT')
        self.stdout.write('='*60)
        self.stdout.write('')
        self.stdout.write('This command provides helper functions for knowledge base management.')
        self.stdout.write('For complete system updates, use the update_kb_system command.')
        self.stdout.write('')
        self.stdout.write('AVAILABLE COMMANDS:')
        self.stdout.write('')
        self.stdout.write('1. Complete system update (RECOMMENDED):')
        self.stdout.write('   python manage.py update_kb_system')
        self.stdout.write('')
        self.stdout.write('2. Check current status:')
        self.stdout.write('   python manage.py migrate_embeddings --check')
        self.stdout.write('')
        self.stdout.write('3. Create default settings:')
        self.stdout.write('   python manage.py migrate_embeddings --create-settings')
        self.stdout.write('')
        self.stdout.write('4. Regenerate embeddings:')
        self.stdout.write('   python manage.py regenerate_embeddings --force')
        self.stdout.write('')
        self.stdout.write('5. User reprocessing interface:')
        self.stdout.write('   /knowledgebase/reprocess/')
        self.stdout.write('')
        self.stdout.write('⚠️  IMPORTANT NOTES:')
        self.stdout.write('   - Use update_kb_system for complete migration')
        self.stdout.write('   - This will backup, clean, migrate, and restore automatically')
        self.stdout.write('   - All embeddings will be regenerated with 3072 dimensions')
        self.stdout.write('   - This may incur Google API costs for regeneration')
        self.stdout.write('')
        self.stdout.write('For complete migration, run: python manage.py update_kb_system --help')
