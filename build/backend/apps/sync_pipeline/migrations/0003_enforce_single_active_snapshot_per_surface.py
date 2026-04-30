from django.db import migrations, models
from django.db.models import Count
from django.db.models import Q
from django.utils import timezone


def collapse_duplicate_active_snapshots(apps, schema_editor):
    PublishedSnapshot = apps.get_model('sync_pipeline', 'PublishedSnapshot')
    now = timezone.now()

    duplicate_surfaces = (
        PublishedSnapshot.objects
        .filter(is_active=True)
        .values('surface')
        .annotate(active_count=Count('id'))
        .filter(active_count__gt=1)
    )

    for row in duplicate_surfaces:
        surface = row['surface']
        active_rows = list(
            PublishedSnapshot.objects
            .filter(surface=surface, is_active=True)
            .order_by('-published_at', '-built_at', '-id')
        )

        keeper = active_rows[0]
        stale_ids = [item.id for item in active_rows[1:]]
        if not stale_ids:
            continue

        PublishedSnapshot.objects.filter(id__in=stale_ids).update(
            is_active=False,
            status='invalidated',
            invalidated_at=now,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('sync_pipeline', '0002_alter_sourcehealth_provider_alter_syncrun_provider'),
    ]

    operations = [
        migrations.RunPython(
            collapse_duplicate_active_snapshots,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name='publishedsnapshot',
            constraint=models.UniqueConstraint(
                fields=('surface',),
                condition=Q(is_active=True),
                name='uniq_active_snapshot_per_surface',
            ),
        ),
    ]
