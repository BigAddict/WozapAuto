# Generated manually to remove image fields from ConversationMessage (from reverted migration)
# Generated on 2025-11-12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('aiengine', '0021_remove_webhookdata_image_fields'),
    ]

    operations = [
        # Remove image fields from ConversationMessage
        migrations.RunSQL(
            sql=[
                "ALTER TABLE aiengine_conversationmessage DROP COLUMN IF EXISTS has_image;",
                "ALTER TABLE aiengine_conversationmessage DROP COLUMN IF EXISTS image_caption;",
                "ALTER TABLE aiengine_conversationmessage DROP COLUMN IF EXISTS image_url;",
            ],
            reverse_sql=[
                # Reverse migration would add them back, but we don't want that
                # So we leave reverse_sql empty or as a no-op
            ],
        ),
    ]

