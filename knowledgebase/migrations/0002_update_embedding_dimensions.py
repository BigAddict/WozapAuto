# Generated manually to update embedding dimensions

import pgvector.django.vector
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledgebase', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='knowledgebase',
            name='embedding',
            field=pgvector.django.vector.VectorField(dimensions=768),
        ),
    ]
