from django.core.management.base import BaseCommand
from submissions.models import Exercise
from submissions.utils import update_submissions

import datetime


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open("files/logfiles/crontesti.txt", "a") as file:
            file.write(f"Trying to update {datetime.datetime.now()}\n")

        exercises = Exercise.objects.all().filter(in_grading=True)
        for exercise in exercises:
            update_submissions(exercise)
