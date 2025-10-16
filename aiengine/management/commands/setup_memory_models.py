"""
Django management command to set up memory models and create migrations.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


class Command(BaseCommand):
    help = 'Set up memory models and create migrations'

    def handle(self, *args, **options):
        self.stdout.write('Setting up memory models...')
        
        # Create migrations for the new models
        self.stdout.write('Creating migrations...')
        call_command('makemigrations', 'aiengine')
        
        # Apply migrations
        self.stdout.write('Applying migrations...')
        call_command('migrate', 'aiengine')
        
        # Check if pgvector extension is available
        with connection.cursor() as cursor:
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                self.stdout.write(
                    self.style.SUCCESS('pgvector extension is available')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'pgvector extension error: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Memory models setup completed!')
        )
