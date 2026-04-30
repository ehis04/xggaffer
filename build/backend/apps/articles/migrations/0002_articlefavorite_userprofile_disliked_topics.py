from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('article', models.ForeignKey(on_delete=models.CASCADE, related_name='favorited_by', to='articles.article')),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='article_favorites', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('user', 'article')},
            },
        ),
        migrations.AddIndex(
            model_name='articlefavorite',
            index=models.Index(fields=['user', '-created_at'], name='articles_ar_user_id_37f4c2_idx'),
        ),
        migrations.AddIndex(
            model_name='articlefavorite',
            index=models.Index(fields=['article'], name='articles_ar_article_51fcfc_idx'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='disliked_topics',
            field=models.ManyToManyField(blank=True, related_name='disliked_by_users', to='articles.topic'),
        ),
    ]
