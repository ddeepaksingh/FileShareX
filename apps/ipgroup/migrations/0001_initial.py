import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='IPGroup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ip_address', models.GenericIPAddressField(db_index=True, unique=True)),
                ('storage_quota', models.BigIntegerField(default=524288000)),
                ('storage_used', models.BigIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('is_blocked', models.BooleanField(default=False)),
                ('upload_count_today', models.IntegerField(default=0)),
                ('last_upload', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_activity', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'ip_groups'},
        ),
        migrations.CreateModel(
            name='AnonymousUploader',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('cookie_id', models.CharField(db_index=True, max_length=64, unique=True)),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_seen', models.DateTimeField(auto_now=True)),
                ('ip_group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='uploaders',
                    to='ipgroup.ipgroup',
                )),
            ],
            options={'db_table': 'anonymous_uploaders'},
        ),
        migrations.AddIndex(
            model_name='ipgroup',
            index=models.Index(fields=['ip_address'], name='ip_groups_ip_addr_idx'),
        ),
        migrations.AddIndex(
            model_name='ipgroup',
            index=models.Index(fields=['is_active', 'is_blocked'], name='ip_groups_active_idx'),
        ),
    ]
