# Generated by Django 2.0.2 on 2018-06-06 11:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Exercise',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exercise_id', models.CharField(max_length=6, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('consent_exercise', models.CharField(max_length=6)),
                ('min_points', models.PositiveSmallIntegerField(default=1)),
                ('max_points', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('deadline', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sub_id', models.CharField(max_length=20, unique=True)),
                ('sub_url', models.URLField()),
                ('submitter', models.EmailField(max_length=254)),
                ('grader', models.EmailField(max_length=254)),
                ('feedback', models.TextField()),
                ('points', models.PositiveSmallIntegerField(default=0)),
                ('done', models.BooleanField(default=False)),
                ('exercise', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='submissions.Exercise')),
            ],
        ),
    ]
