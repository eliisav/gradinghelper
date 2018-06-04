from django.db import models


class Exercise(models.Model):
    exercise_id = models.CharField(max_length=4, unique=True)
    name = models.CharField(max_length=200)


class Feedback(models.Model):
    #exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sub_id = models.CharField(max_length=20, unique=True)
    sub_url = models.URLField()
    submitter = models.EmailField()
    grader = models.EmailField()
    feedback = models.TextField()
    points = models.IntegerField(default=0)
    done = models.BooleanField(default=False)
