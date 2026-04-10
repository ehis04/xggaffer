
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('predictions', '0002_matchfeature'),
    ]

    operations = [
        migrations.CreateModel(
            name='CurrentEloRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('team', models.CharField(max_length=100, unique=True)),
                ('league', models.CharField(max_length=50)),
                ('elo', models.FloatField()),
                ('last_match_date', models.DateField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-elo'],
            },
        ),
        migrations.CreateModel(
            name='EloRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('team', models.CharField(max_length=100)),
                ('league', models.CharField(max_length=50)),
                ('season', models.CharField(max_length=10)),
                ('date', models.DateField()),
                ('match_id', models.CharField(max_length=50)),
                ('elo_before', models.FloatField()),
                ('elo_after', models.FloatField()),
            ],
            options={
                'ordering': ['date'],
            },
        ),
        migrations.DeleteModel(
            name='MatchFeature',
        ),
        migrations.AddIndex(
            model_name='elorating',
            index=models.Index(fields=['team', 'date'], name='predictions_team_df3fa5_idx'),
        ),
        migrations.AddIndex(
            model_name='elorating',
            index=models.Index(fields=['league', 'season'], name='predictions_league_d585af_idx'),
        ),
        migrations.AddIndex(
            model_name='elorating',
            index=models.Index(fields=['team', '-date'], name='predictions_team_6e0689_idx'),
        ),
    ]
