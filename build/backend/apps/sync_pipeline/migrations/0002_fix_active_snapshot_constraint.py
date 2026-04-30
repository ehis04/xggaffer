# Generated manually to fix the constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sync_pipeline', '0001_initial'),
    ]

    operations = [
        # Drop the old table-level unique constraint
        migrations.RunSQL(
            sql='ALTER TABLE sync_pipeline_publishedsnapshot DROP CONSTRAINT IF EXISTS uniq_active_snapshot_per_surface',
            reverse_sql='',
        ),
        # The model now has a partial unique index via UniqueConstraint with condition
        # This is handled by Django's autodetector, but we need to ensure the old constraint is gone
    ]