# Generated manually to add unique constraint for Agent model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aiengine', '0012_remove_knowledgebase_tags_remove_knowledgebase_user_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='agent',
            constraint=models.UniqueConstraint(
                condition=models.Q(('user__isnull', False)),
                fields=('user',),
                name='unique_agent_per_user'
            ),
        ),
    ]
