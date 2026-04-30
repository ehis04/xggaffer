from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('predictions', '0009_odds_accuracy_stats_market_metrics'),
    ]

    operations = [
        migrations.AddField(
            model_name='oddsaccuracystats',
            name='market_correct_count',
            field=models.IntegerField(default=0),
        ),
    ]
