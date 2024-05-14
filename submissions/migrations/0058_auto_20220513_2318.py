# Generated by Django 2.2.28 on 2022-05-13 20:18

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0057_auto_20201211_1952'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='exercise',
            options={'ordering': ['grading_ready', 'chapter_num', 'name']},
        ),
        migrations.AddField(
            model_name='exercise',
            name='chapter_num',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=list, size=None),
        ),
    ]
