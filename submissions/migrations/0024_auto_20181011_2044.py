# Generated by Django 2.0.7 on 2018-10-11 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0023_auto_20181010_1505'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feedback',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Palautepohja'), (1, 'Luonnos'), (2, 'Valmis')], default=0),
        ),
    ]