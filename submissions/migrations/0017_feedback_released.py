# Generated by Django 2.0.7 on 2018-08-09 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0016_auto_20180808_1631'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedback',
            name='released',
            field=models.BooleanField(default=False),
        ),
    ]