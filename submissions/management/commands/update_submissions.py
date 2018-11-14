from django.core.management.base import BaseCommand
from submissions.models import Exercise
from submissions.utils import update_submissions


class Command(BaseCommand):
    def handle(self, *args, **options):
        exercises = Exercise.objects.all().filter(
            in_grading=True
        ).filter(
            grading_ready=False
        )
        for exercise in exercises:
            update_submissions(exercise)
