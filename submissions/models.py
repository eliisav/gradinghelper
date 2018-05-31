from django.db import models


class Submission(models.Model):
    sub_id = models.CharField(max_length=20)
    student_id = models.CharField(max_length=6)
    student_email = models.CharField(max_length=50)
    sub_url = models.CharField(max_length=200)


class Grader(models.Model):
    email = models.CharField(max_length=50)


class Feedback(models.Model):
    sub_id = models.CharField(max_length=20, unique=True)
    assistant = models.CharField(max_length=6)
    feedback = models.TextField()
    points = models.IntegerField(default=0)
