from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0005_aiconversationlog_connectionactivitylog_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationlog',
            name='is_read',
            field=models.BooleanField(default=False, help_text='Whether the in-app notification has been read'),
        ),
        migrations.AddField(
            model_name='notificationlog',
            name='read_at',
            field=models.DateTimeField(blank=True, help_text='When the notification was read in-app', null=True),
        ),
    ]

