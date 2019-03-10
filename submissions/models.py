from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField


class User(AbstractUser):
    def __str__(self):
        return self.email


class Course(models.Model):
    course_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    api_url = models.URLField()
    api_root = models.URLField(null=True, blank=True)
    teachers = models.ManyToManyField(User, related_name="responsibilities",
                                      blank=True)
    assistants = models.ManyToManyField(User, related_name="my_courses",
                                        blank=True)

    def save(self, *args, **kwargs):
        if not self.api_root:
            self.api_root = "/".join(str(self.api_url).split("/")[:-3]) + "/"
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name
        
    def is_teacher(self, user):
        return user in self.teachers.all()

    def is_staff(self, user):
        return self.is_teacher(user) or user in self.assistants.all()


def feedback_base_path(instance, filename):
    """
    Return a path to save feedback base file.
    :param instance: (Exercise) exercise model object
    :param filename: (str) name of uploaded file
    :return: (str) path to save uploaded file
    """
    course = f"course_{instance.course.course_id}"
    exercise = f"exercise_{instance.exercise_id}"
    return f"{course}/{exercise}/{filename}/"


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
    min_points = models.PositiveSmallIntegerField(default=1)
    # Tarvitaan vain, jos arvostelu tapahtuu osittain muilla työkaluilla
    max_points = models.PositiveSmallIntegerField(null=True, blank=True)
    add_penalty = models.BooleanField(default=True)
    add_auto_grade = models.BooleanField(default=True)
    feedback_base = models.FileField(null=True, blank=True,
                                     upload_to=feedback_base_path)
    in_grading = models.BooleanField(default=False)
    grading_ready = models.BooleanField(default=False)

    # Mahdollisuus valita tehtävien automaattinen jako assareille.
    # auto_div=False => assari valitsee itse tehtävät tarkastukseen.
    work_div = models.PositiveSmallIntegerField(choices=DIV_CHOICES,
                                                default=EVEN_DIV)
    graders = models.ManyToManyField(User, blank=True,
                                     related_name="my_gradings"
                                     )
    num_of_graders = models.PositiveSmallIntegerField(null=True, blank=True)
    latest_release = ArrayField(models.IntegerField(), default=list)

    # Tätä ei enää tarvita
    # consent_exercise = models.ForeignKey("self", on_delete=models.CASCADE,
    #                                      null=True, blank=True)

    class Meta:
        ordering = ["grading_ready", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
           "submissions:exercises", kwargs={"course_id": self.course.course_id}
        )

    def set_defaults(self):
        # self.consent_exercise = None  # Ei ole enää tarpeellinen
        self.min_points = 1
        self.max_points = None
        self.add_penalty = True
        self.add_auto_grade = True
        self.in_grading = False
        self.grading_ready = False
        self.work_div = self.EVEN_DIV
        self.graders.all = None
        self.num_of_graders = None


class Student(models.Model):
    email = models.EmailField(unique=True)
    student_id = models.IntegerField(default=None, null=True)
    aplus_user_id = models.IntegerField(unique=True, null=True)
    
    def __str__(self):
        if self.student_id:
            return f"{self.student_id} {self.email}"
        else:
            return self.email


class Feedback(models.Model):
    BASE = 0
    DRAFT = 1
    READY = 2
    
    STATUS_CHOICES = (
        (BASE, "Palautepohja"),
        (DRAFT, "Luonnos"),
        (READY, "Valmis"),
    )
    
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sub_id = models.IntegerField(unique=True)
    grading_time = models.DateTimeField(null=True)
    students = models.ManyToManyField(Student, related_name="my_feedbacks")
    grader = models.ForeignKey(User, on_delete=models.CASCADE,
                               null=True, blank=True)
    feedback = models.TextField()
    auto_grade = models.PositiveIntegerField(default=0)
    staff_grade = models.PositiveSmallIntegerField(default=0)
    penalty = models.DecimalField(default=0.0, max_digits=4, decimal_places=2)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
                                              default=BASE)
    released = models.BooleanField(default=False)

    class Meta:
        ordering = ["status", "released", "sub_id"]
        
    def __str__(self):
        return str(self.sub_id)

    def get_students(self):
        return self.students.all()
