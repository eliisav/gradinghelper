# Generated by Django 2.0.7 on 2018-11-16 12:47

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0028_exercise_latest_release'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exercise',
            name='latest_release',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=[], size=None),
        ),
    ]
