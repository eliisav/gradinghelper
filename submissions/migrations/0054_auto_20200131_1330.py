# Generated by Django 2.0.7 on 2020-01-31 11:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0053_auto_20200128_1609'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exercise',
            name='work_div',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Automated equal division'), (1, 'Allow staff pick submissions manually')], default=0),
        ),
    ]