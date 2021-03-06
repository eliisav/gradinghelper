# Generated by Django 2.0.7 on 2018-08-16 13:41

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course_id', models.PositiveIntegerField(unique=True)),
                ('name', models.CharField(max_length=200)),
                ('teachers', models.ManyToManyField(blank=True, related_name='my_courses', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Exercise',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exercise_id', models.PositiveIntegerField(unique=True)),
                ('module_id', models.PositiveIntegerField()),
                ('name', models.CharField(max_length=200)),
                ('min_points', models.PositiveSmallIntegerField(default=1)),
                ('feedback_base', models.FileField(blank=True, null=True, upload_to='')),
                ('trace', models.BooleanField(default=False)),
                ('consent_exercise', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='submissions.Exercise')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='submissions.Course')),
            ],
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sub_id', models.IntegerField(unique=True)),
                ('sub_url', models.URLField()),
                ('feedback', models.TextField(verbose_name='palaute')),
                ('points', models.PositiveSmallIntegerField(default=0, verbose_name='pisteet')),
                ('status', models.PositiveSmallIntegerField(choices=[(0, 'Luonnos'), (1, 'Valmis')], null=True, verbose_name='palautteen tila')),
                ('released', models.BooleanField(default=False)),
                ('exercise', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='submissions.Exercise')),
                ('grader', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['status'],
            },
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='feedback',
            name='students',
            field=models.ManyToManyField(related_name='my_feedbacks', to='submissions.Student'),
        ),
    ]
