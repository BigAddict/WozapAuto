"""
Django management command to test embedding model initialization with caching.
"""
from django.core.management.base import BaseCommand
import logging
import time

from aiengine.model_cache import model_cache

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test embedding model initialization with global caching'

    def handle(self, *args, **options):
        self.stdout.write('Testing embedding model initialization with caching...')
        
        # Test model loading with timing
        start_time = time.time()
        
        try:
            self.stdout.write('Loading model from cache...')
            model = model_cache.get_model()
            
            load_time = time.time() - start_time
            self.stdout.write(
                self.style.SUCCESS(f'✓ Model loaded successfully in {load_time:.2f} seconds')
            )
            self.stdout.write(f'  - Model name: {model_cache.get_model_name()}')
            self.stdout.write(f'  - Embedding dimensions: {model_cache.get_embedding_dimensions()}')
            self.stdout.write(f'  - Model is cached: {model_cache.is_loaded()}')
            
            # Test encoding
            test_text = "This is a test message for embedding generation."
            encoding_start = time.time()
            embedding = model.encode(test_text)
            encoding_time = time.time() - encoding_start
            
            self.stdout.write(f'  - Encoding time: {encoding_time:.3f} seconds')
            self.stdout.write(f'  - Embedding dimensions: {len(embedding)}')
            self.stdout.write(f'  - Sample embedding: {embedding[:5]}...')
            
            # Test cache performance (second call should be instant)
            self.stdout.write('\nTesting cache performance...')
            cache_start = time.time()
            cached_model = model_cache.get_model()
            cache_time = time.time() - cache_start
            
            self.stdout.write(f'  - Cache access time: {cache_time:.4f} seconds')
            self.stdout.write(f'  - Same model instance: {model is cached_model}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Model loading failed: {e}')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('Embedding model test with caching completed successfully!')
        )
