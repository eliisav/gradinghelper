# Generated by Django 2.0.7 on 2018-09-25 11:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0010_auto_20180914_1336'),
    ]

    operations = [
        migrations.RenameField(
            model_name='feedback',
            old_name='points',
            new_name='staff_grade',
        ),
    ]
