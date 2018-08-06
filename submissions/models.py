from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Course(models.Model):
    course_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    teachers = models.ManyToManyField (User, related_name="my_courses", blank=True)
    
    def __str__(self):
        return self.name


class Exercise(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exercise_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    consent_exercise = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    min_points = models.PositiveSmallIntegerField(default=1)
    max_points = models.PositiveSmallIntegerField(null=True, blank=True)  # Tarvitaanko tätä?
    deadline = models.DateTimeField(default=timezone.now)
    trace = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name


class Student(models.Model):
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return self.email


class Feedback(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sub_id = models.IntegerField(unique=True)
    sub_url = models.URLField()
    students = models.ManyToManyField(Student, related_name="my_feedbacks")
    grader = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    feedback = models.TextField()
    points = models.PositiveSmallIntegerField(default=0)
    done = models.BooleanField(default=False)

    class Meta:
        ordering = ["done"]
        
    def __str__(self):
        return str(self.sub_id)

