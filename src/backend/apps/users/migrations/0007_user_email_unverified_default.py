from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0006_merge_20260501_1656")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
    ]
