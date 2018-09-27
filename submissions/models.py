from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    def __str__(self):
        return self.email


class Course(models.Model):
    course_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    html_url = models.URLField()
    teachers = models.ManyToManyField(User, related_name="responsibilities",
                                      blank=True)
    assistants = models.ManyToManyField(User, related_name="my_courses",
                                        blank=True)
    
    def __str__(self):
        return self.name
        
    def is_teacher(self, user):
        return user in self.teachers.all()
        

class Exercise(models.Model):
    EVEN_DIV = 0
    NO_DIV = 1

    DIV_CHOICES = (
        (EVEN_DIV, "Automaattinen tasajako"),
        (NO_DIV, "Henkilökunta valitsee työt manuaalisesti"),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exercise_id = models.PositiveIntegerField(unique=True)
    module_id = models.PositiveIntegerField()
    name = models.CharField(max_length=200)
    consent_exercise = models.ForeignKey("self", on_delete=models.CASCADE,
                                         null=True, blank=True)
    min_points = models.PositiveSmallIntegerField(default=1)
    feedback_base = models.FileField(null=True, blank=True, upload_to="files/")
    in_grading = models.BooleanField(default=False)

    # TODO: Tarvittaisiinko tämmöinen, ettei suotta loputtomiin haeta
    # palautuksia tehtävään, joka on jo arvosteltu?
    # grading_ready = models.BooleanField(default=False)

    # TODO: Tarvitaanko kuitenkin joku max-pisteet rästiprojekteja varten?
    # max_points = models.PositiveSmallIntegerField(null=True, blank=True)

    # Mahdollisuus valita tehtävien automaattinen jako assareille.
    # auto_div=False => assari valitsee itse tehtävät tarkastukseen.
    work_div = models.PositiveSmallIntegerField(choices=DIV_CHOICES,
                                                default=EVEN_DIV)

    def set_defaults(self):
        self.consent_exercise = None
        self.min_points = 1
        self.in_grading = False
        self.work_div = self.EVEN_DIV

    def get_absolute_url(self):
        return reverse(
           "submissions:exercises", kwargs={"course_id": self.course.course_id}
        )

    def __str__(self):
        return self.name


class Student(models.Model):
    email = models.EmailField(unique=True)
    student_id = models.IntegerField(default=None, null=True)
    
    def __str__(self):
        if self.student_id:
            return f"{self.student_id} {self.email}"
        else:
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
    students = models.ManyToManyField(Student, related_name="my_feedbacks")
    grader = models.ForeignKey(User, on_delete=models.CASCADE,
                               null=True, blank=True)
    feedback = models.TextField()
    auto_grade = models.PositiveIntegerField(default=0)
    staff_grade = models.PositiveSmallIntegerField(null=True)
    penalty = models.DecimalField(default=1.0, max_digits=4, decimal_places=2)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
                                              null=True)
    released = models.BooleanField(default=False)

    class Meta:
        ordering = ["status"]
        
    def __str__(self):
        return str(self.sub_id)
