# Generated by Django 2.0.7 on 2018-11-21 12:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0034_auto_20181121_1101'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='feedback',
            options={'ordering': ['status', 'released', 'sub_id']},
        ),
    ]
