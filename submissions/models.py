from django.db import models
from django.utils import timezone


class Exercise(models.Model):
    course_id = models.PositiveIntegerField()
    exercise_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    consent_exercise = models.PositiveIntegerField(null=True, blank=True)
    min_points = models.PositiveSmallIntegerField(default=1)
    max_points = models.PositiveSmallIntegerField(null=True, blank=True)
    deadline = models.DateTimeField(default=timezone.now)


class Feedback(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sub_id = models.IntegerField(unique=True)
    sub_url = models.URLField()
    submitter = models.EmailField()  # Tarvitaanko? Näitä voi olla monta.
    grader = models.EmailField()
    feedback = models.TextField()
    points = models.PositiveSmallIntegerField(default=0)
    done = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["done"]
