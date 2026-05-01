# Generated manually on 2026-04-30

import django.db.models.deletion
from django.db import migrations, models


def notification_targets():
    return (
        models.Q(('app_label', 'community'), ('model', 'post'))
        | models.Q(('app_label', 'community'), ('model', 'comment'))
        | models.Q(('app_label', 'users'), ('model', 'follow'))
        | models.Q(('app_label', 'users'), ('model', 'followrequest'))
    )


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0004_rename_community_b_is_acti_c70ce9_idx_community_b_is_acti_e0c5b0_idx_and_more'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('users', '0004_followrequest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='content_type',
            field=models.ForeignKey(
                limit_choices_to=notification_targets,
                on_delete=django.db.models.deletion.CASCADE,
                to='contenttypes.contenttype',
            ),
        ),
    ]
