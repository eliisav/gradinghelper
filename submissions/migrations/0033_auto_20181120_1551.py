# Generated by Django 2.0.7 on 2018-11-20 13:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0032_auto_20181120_1550'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='feedback',
            options={'ordering': ['status', 'released', 'sub_time']},
        ),
    ]
