# Generated by Django 2.0.7 on 2018-09-13 08:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0007_remove_feedback_sub_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='exercise',
            name='auto_div',
        ),
        migrations.AddField(
            model_name='exercise',
            name='work_div',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Automaattinen tasajako'), (1, 'Henkilökunta valitsee työt manuaalisesti.')], default=0, verbose_name='Työnjako'),
        ),
    ]
