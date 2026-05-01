from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playerdata", "0001_initial"),
    ]

    operations = []


    superseded_operations = [
        migrations.AddField(
            model_name="playerseasonenrichment",
            name="red_cards",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="playerseasonenrichment",
            name="xg_buildup",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="playerseasonenrichment",
            name="xg_chain",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="playerseasonenrichment",
            name="yellow_cards",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
