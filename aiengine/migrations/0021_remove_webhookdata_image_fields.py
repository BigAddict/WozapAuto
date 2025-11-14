# Generated manually to remove image fields from reverted migration
# Generated on 2025-11-12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('aiengine', '0020_agent_business'),
    ]

    operations = [
        # Use RunSQL to remove columns that exist in DB but not in migration state
        # Remove image fields from WebhookData (from reverted migration)
        migrations.RunSQL(
            sql=[
                "ALTER TABLE aiengine_webhookdata DROP COLUMN IF EXISTS has_image;",
                "ALTER TABLE aiengine_webhookdata DROP COLUMN IF EXISTS image_caption;",
                "ALTER TABLE aiengine_webhookdata DROP COLUMN IF EXISTS image_url;",
            ],
            reverse_sql=[
                # Reverse migration would add them back, but we don't want that
                # So we leave reverse_sql empty or as a no-op
            ],
        ),
    ]

