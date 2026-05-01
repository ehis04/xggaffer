# Generated manually on 2026-04-30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_user_email_verified'),
    ]

    operations = [
        migrations.CreateModel(
            name='FollowRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('P', 'Pending'), ('A', 'Accepted'), ('D', 'Declined')], default='P', max_length=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('follower', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_follow_requests', to='users.userprofile')),
                ('following', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_follow_requests', to='users.userprofile')),
            ],
            options={
                'verbose_name': 'Follow Request',
                'verbose_name_plural': 'Follow Requests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='followrequest',
            index=models.Index(fields=['following', 'status', '-created_at'], name='users_follo_followi_f5df43_idx'),
        ),
        migrations.AddIndex(
            model_name='followrequest',
            index=models.Index(fields=['follower', 'status', '-created_at'], name='users_follo_followe_0d246a_idx'),
        ),
        migrations.AddConstraint(
            model_name='followrequest',
            constraint=models.UniqueConstraint(fields=('follower', 'following'), name='unique_follow_request'),
        ),
        migrations.AddConstraint(
            model_name='followrequest',
            constraint=models.CheckConstraint(condition=models.Q(('follower', models.F('following')), _negated=True), name='prevent_self_follow_request'),
        ),
    ]
