from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Course, User

admin.site.register(Course)
admin.site.register(User, UserAdmin)
