from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
import os


class BigAutoIDModel(models.Model):
    id = models.BigAutoField(primary_key=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    def __str__(self):
        return self.email


class BaseCourse(BigAutoIDModel):
    label = models.CharField(max_length=255)
    lms_instance_id = models.CharField(max_length=255)
   
    teachers = models.ManyToManyField(User, related_name="courses_teacher",
                                      blank=True)
    assistants = models.ManyToManyField(User, related_name="courses_assistant",
                                        blank=True)
                                        
    class Meta:
        unique_together = ["label", "lms_instance_id"]


class Course(BigAutoIDModel):
    base_course = models.ForeignKey(BaseCourse, on_delete=models.CASCADE)
    course_id = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    api_root = models.URLField(null=True, blank=True)
    api_token = models.CharField(max_length=255)
    api_url = models.URLField(unique=True)
    data_url = models.URLField()
    exercise_url = models.URLField()

    class Meta:
        ordering = ["name", "course_id"]

    def save(self, *args, **kwargs):
        if not self.api_root:
            self.api_root = "/".join(str(self.api_url).split("/")[:-3]) + "/"
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name
        
    def is_teacher(self, user):
        return user.is_superuser or self.base_course.teachers.filter(
            id=user.id
        ).exists()

    def is_staff(self, user):
        return self.is_teacher(user) or self.base_course.assistants.filter(
            id=user.id
        ).exists()


def feedback_base_path(instance, filename):
    """
    Return a path to save feedback base file.
    :param instance: (Exercise) exercise model object
    :param filename: (str) name of uploaded file
    :return: (str) path to save uploaded file
    """
    course = f"course_{instance.course.id}_{instance.course.course_id}"
    exercise = f"exercise_{instance.exercise_id}"
    return os.path.join(course, exercise, filename)


class Exercise(BigAutoIDModel):
    EVEN_DIV = 0
    NO_DIV = 1

    DIV_CHOICES = (
        (EVEN_DIV, "Automated equal division"),
        (NO_DIV, "Allow staff pick submissions manually"),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exercise_id = models.BigIntegerField(unique=True)
    module = models.URLField()
    chapter_num = ArrayField(models.IntegerField(), default=list)
    name = models.CharField(max_length=255)
    api_url = models.URLField()
    min_points = models.PositiveSmallIntegerField(default=1)

    # Possible maximum points from automated tests.
    # Needed only if some part of grading is done outside of this service.
    max_points = models.PositiveSmallIntegerField(null=True, blank=True)
    total_max_points = models.PositiveSmallIntegerField(null=True)
    add_penalty = models.BooleanField(default=True)
    add_auto_grade = models.BooleanField(default=True)
    feedback_base_fi = models.FileField(null=True, blank=True,
                                        upload_to=feedback_base_path)
    feedback_base_en = models.FileField(null=True, blank=True,
                                        upload_to=feedback_base_path)
    in_grading = models.BooleanField(default=False)
    stop_polling = models.BooleanField(default=False)
    error_state = models.CharField(max_length=255, default=None, null=True)

    # Mahdollisuus valita tehtävien automaattinen jako assareille.
    # auto_div=False => assari valitsee itse tehtävät tarkastukseen.
    work_div = models.PositiveSmallIntegerField(choices=DIV_CHOICES,
                                                default=EVEN_DIV)
    graders = models.ManyToManyField(User, blank=True,
                                     related_name="my_gradings")
    graders_en = models.ManyToManyField(User, blank=True,
                                        related_name="my_gradings_en")
    num_of_graders = models.PositiveSmallIntegerField(null=True, blank=True)
    latest_release = ArrayField(models.BigIntegerField(), default=list)

    class Meta:
        ordering = ["stop_polling", "chapter_num", "name"]

    def __str__(self):
        return self.name

    def set_defaults(self):
        # self.consent_exercise = None  # Ei ole enää tarpeellinen
        self.min_points = 1
        self.max_points = None
        self.add_penalty = True
        self.add_auto_grade = True
        self.in_grading = False
        self.stop_polling = False
        self.work_div = self.EVEN_DIV
        self.graders.all = None
        self.num_of_graders = None


class Student(BigAutoIDModel):
    aplus_user_id = models.CharField(max_length=255)
    lms_instance_id = models.CharField(max_length=255)
    email = models.EmailField()
    student_id = models.CharField(max_length=255, unique=True,
                                  default=None, null=True)

    class Meta:
        unique_together = ["aplus_user_id", "lms_instance_id"]

    def __str__(self):
        if self.student_id:
            return f"{self.student_id} {self.email}"
        else:
            return self.email


class Feedback(BigAutoIDModel):
    BASE = 0
    DRAFT = 1
    READY = 2
    
    STATUS_CHOICES = (
        (BASE, "Template"),
        (DRAFT, "Draft"),
        (READY, "Ready"),
    )
    
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sub_id = models.BigIntegerField(unique=True)
    grading_time = models.DateTimeField(null=True)
    grader_lang_en = models.BooleanField(default=False)
    students = models.ManyToManyField(Student, related_name="my_feedbacks")
    grader = models.ForeignKey(User, on_delete=models.CASCADE,
                               null=True, blank=True)
    feedback = models.TextField(blank=True)
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
