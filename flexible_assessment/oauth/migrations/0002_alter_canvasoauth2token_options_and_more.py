# Generated by Django 4.0.4 on 2022-06-09 17:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('oauth', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='canvasoauth2token',
            options={},
        ),
        migrations.AlterField(
            model_name='canvasoauth2token',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='oauth2_token',
                to=settings.AUTH_USER_MODEL),
        ),
    ]
