# Generated by Django 2.0.7 on 2019-09-05 19:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0049_auto_20190905_0314'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='email',
            field=models.EmailField(max_length=254),
        ),
    ]