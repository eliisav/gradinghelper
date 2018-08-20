from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    def __str__(self):
        return self.email


class Course(models.Model):
    course_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    html_url = models.URLField()
    teachers = models.ManyToManyField (User, related_name="responsibilities", blank=True)
    assistants = models.ManyToManyField (User, related_name="my_courses", blank=True)
    
    def __str__(self):
        return self.name
        
    def is_teacher(self, user):
        return user in self.teachers.all()
        

class Exercise(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exercise_id = models.PositiveIntegerField(unique=True)
    module_id = models.PositiveIntegerField()
    name = models.CharField(max_length=200)
    consent_exercise = models.ForeignKey("self", on_delete=models.CASCADE, 
                                         null=True, blank=True)
    min_points = models.PositiveSmallIntegerField(default=1)
    feedback_base = models.FileField(null=True, blank=True)
    trace = models.BooleanField(default=False)
    
    # Tarvitaanko näitä?
    #max_points = models.PositiveSmallIntegerField(null=True, blank=True)  
    #deadline = models.DateTimeField(default=timezone.now)
    
    
    def __str__(self):
        return self.name
        
    """
    Yritys rajoittaa lomakkeen valintalaatikossa näkyviä tehtäviä.
    Tarkoitus näyttää vain samaan kurssiin kuuluvat tehtävät.
    Ei kuitenkaan onnistunut näin.
    
    Tämän rivin piti olla vierasavaimen argumenttina:
    limit_choices_to=self.limit_exercises
    
    def limit_exercises(self):
        return {'course.course_id': self.course.course_id}
        
    """


class Student(models.Model):
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return self.email


class Feedback(models.Model):
    DRAFT = 0
    READY = 1
    
    STATUS_CHOICES = (
        (DRAFT, "Luonnos"),
        (READY, "Valmis"),
    )
    
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sub_id = models.IntegerField(unique=True)
    sub_url = models.URLField()
    students = models.ManyToManyField(Student, related_name="my_feedbacks")
    grader = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    feedback = models.TextField(verbose_name="palaute")
    points = models.PositiveSmallIntegerField(default=0, verbose_name="pisteet")
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, null=True,
                                              verbose_name="palautteen tila")
    released = models.BooleanField(default=False)

    class Meta:
        ordering = ["status"]
        
    def __str__(self):
        return str(self.sub_id)

