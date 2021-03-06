# Generated by Django 2.0.7 on 2019-06-20 07:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0042_auto_20190310_0202'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='api_token',
            field=models.CharField(default='dcbf2252108dc02655a4a656ec888f808eb89d8e', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='course',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='exercise',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='student',
            name='student_id',
            field=models.CharField(default=None, max_length=255, null=True, unique=True),
        ),
    ]
