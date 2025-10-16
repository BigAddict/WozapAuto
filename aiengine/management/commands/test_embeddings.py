"""
Django management command to test embedding model initialization.
"""
from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test embedding model initialization'

    def handle(self, *args, **options):
        self.stdout.write('Testing embedding model initialization...')
        
        # Try different embedding models
        models_to_try = [
            'all-MiniLM-L6-v2',
            'paraphrase-MiniLM-L6-v2', 
            'all-MiniLM-L12-v2',
            'distilbert-base-nli-mean-tokens'
        ]
        
        for model_name in models_to_try:
            try:
                self.stdout.write(f'Trying to initialize: {model_name}')
                model = SentenceTransformer(model_name)
                
                # Test encoding
                test_text = "This is a test message for embedding generation."
                embedding = model.encode(test_text)
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {model_name} initialized successfully')
                )
                self.stdout.write(f'  - Embedding dimensions: {len(embedding)}')
                self.stdout.write(f'  - Sample embedding: {embedding[:5]}...')
                
                # Use this model
                break
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ {model_name} failed: {e}')
                )
                continue
        else:
            self.stdout.write(
                self.style.ERROR('All embedding models failed to initialize!')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('Embedding model test completed successfully!')
        )
