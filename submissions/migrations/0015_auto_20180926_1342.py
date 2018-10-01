# Generated by Django 2.0.7 on 2018-09-26 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0014_auto_20180925_1709'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exercise',
            name='work_div',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Automaattinen tasajako'), (1, 'Henkilökunta valitsee työt manuaalisesti')], default=0),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='feedback',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='staff_grade',
            field=models.PositiveSmallIntegerField(),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Luonnos'), (1, 'Valmis')], null=True),
        ),
    ]