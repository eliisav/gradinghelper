# Generated by Django 2.0.7 on 2019-02-21 13:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0039_auto_20190221_1504'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='api_root',
            field=models.URLField(blank=True, null=True),
        ),
    ]
