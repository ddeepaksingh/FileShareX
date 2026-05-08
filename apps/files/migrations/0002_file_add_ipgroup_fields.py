import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0001_initial'),
        ('ipgroup', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Make File.owner nullable to support anonymous IP-group uploads
        migrations.AlterField(
            model_name='file',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='files',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # Track which IP group owns the file
        migrations.AddField(
            model_name='file',
            name='ip_group',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='files',
                to='ipgroup.ipgroup',
            ),
        ),

        # Track the specific anonymous uploader (cookie-based)
        migrations.AddField(
            model_name='file',
            name='anonymous_uploader',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='files',
                to='ipgroup.anonymousuploader',
            ),
        ),

        # Expiry timestamp (used by IP group files)
        migrations.AddField(
            model_name='file',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # Indexes for the new fields
        migrations.AddIndex(
            model_name='file',
            index=models.Index(fields=['ip_group'], name='files_ip_group_idx'),
        ),
        migrations.AddIndex(
            model_name='file',
            index=models.Index(fields=['expires_at'], name='files_expires_at_idx'),
        ),
    ]
