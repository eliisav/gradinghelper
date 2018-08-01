from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Course(models.Model):
    course_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    teachers = models.ManyToManyField (User, related_name="my_courses")
    
    def __str__(self):
        return self.name


class Exercise(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exercise_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    consent_exercise = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    min_points = models.PositiveSmallIntegerField(default=1)
    max_points = models.PositiveSmallIntegerField(null=True, blank=True)
    deadline = models.DateTimeField(default=timezone.now)
    trace = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name


class Feedback(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sub_id = models.IntegerField(unique=True)
    sub_url = models.URLField()
    student = models.EmailField()  # Tarvitaanko? Näitä voi olla monta.
    grader = models.EmailField()
    feedback = models.TextField()
    points = models.PositiveSmallIntegerField(default=0)
    done = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["done"]
