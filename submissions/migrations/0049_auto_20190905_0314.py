# Generated by Django 2.0.7 on 2019-09-05 00:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0048_auto_20190905_0144'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='course_id',
            field=models.PositiveIntegerField(),
        ),
    ]
