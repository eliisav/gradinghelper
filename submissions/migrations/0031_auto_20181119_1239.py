# Generated by Django 2.0.7 on 2018-11-19 10:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0030_auto_20181116_1520'),
    ]

    operations = [
        migrations.RenameField(
            model_name='course',
            old_name='html_url',
            new_name='api_url',
        ),
    ]