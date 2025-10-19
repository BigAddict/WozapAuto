# Generated manually to add settings and update embedding dimensions

import pgvector.django.vector
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('knowledgebase', '0002_update_embedding_dimensions'),
    ]

    operations = [
        # Create KnowledgeBaseSettings table
        migrations.CreateModel(
            name='KnowledgeBaseSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('embedding_dimensions', models.IntegerField(default=3072, help_text='Embedding vector dimensions. Gemini supports 128-3072. Higher = better quality but more storage. Recommended: 768, 1536, or 3072')),
                ('similarity_threshold', models.FloatField(default=0.5, help_text='Minimum similarity score (0.0-1.0) for retrieval. Lower = more results but less precise. Recommended: 0.5-0.7')),
                ('top_k_results', models.IntegerField(default=5, help_text='Number of top similar chunks to retrieve from database')),
                ('max_chunks_in_context', models.IntegerField(default=3, help_text='Maximum number of knowledge base chunks to include in AI context')),
                ('chunk_size', models.IntegerField(default=1000, help_text='Number of characters per document chunk. Larger = more context but less precise retrieval')),
                ('chunk_overlap', models.IntegerField(default=200, help_text='Character overlap between chunks to preserve context across boundaries')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_base_settings', to='auth.user')),
            ],
            options={
                'verbose_name': 'Knowledge Base Settings',
                'verbose_name_plural': 'Knowledge Base Settings',
            },
        ),
        
        # Update embedding dimensions from 768 to 3072
        # Note: This migration assumes the KnowledgeBase table is empty (handled by update_kb_system command)
        migrations.AlterField(
            model_name='knowledgebase',
            name='embedding',
            field=pgvector.django.vector.VectorField(dimensions=3072),
        ),
    ]
