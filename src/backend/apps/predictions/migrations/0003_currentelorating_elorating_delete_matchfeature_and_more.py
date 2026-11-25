
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('predictions', '0002_matchfeature'),
    ]

    # CurrentEloRating, EloRating, and their indexes are already part of the
    # current 0001_initial migration. Recreating them here prevents a clean
    # database from migrating. MatchFeature was introduced by 0002 and still
    # needs to be removed from both migration state and the database.
    operations = [
        migrations.DeleteModel(
            name='MatchFeature',
        ),
    ]
