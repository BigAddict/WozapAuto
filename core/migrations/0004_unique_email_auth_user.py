from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_userprofile_email_verification_sent_at_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique_idx "
                "ON auth_user (lower(email));"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS auth_user_email_unique_idx;"
            )
        ),
    ]


