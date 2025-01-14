from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Course, User, BaseCourse, Exercise, Student, Feedback

admin.site.register(Course)
admin.site.register(User, UserAdmin)
admin.site.register(BaseCourse)
admin.site.register(Exercise)
admin.site.register(Student)
admin.site.register(Feedback)
