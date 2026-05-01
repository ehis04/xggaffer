
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('predictions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatchFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('match_id', models.CharField(max_length=50, unique=True)),
                ('season', models.CharField(max_length=10)),
                ('league', models.CharField(max_length=50)),
                ('date', models.DateField(blank=True, null=True)),
                ('home_team', models.CharField(max_length=100)),
                ('away_team', models.CharField(max_length=100)),
                ('features', models.JSONField()),
                ('computed_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'indexes': [models.Index(fields=['league', 'season'], name='predictions_league_c0657a_idx'), models.Index(fields=['date'], name='predictions_date_19aca5_idx')],
            },
        ),
    ]
