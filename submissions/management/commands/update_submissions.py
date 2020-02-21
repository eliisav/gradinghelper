"""
Management command to get new submissions from Plussa. This is ment to be
called frequently by crontab.
"""

import logging

from django.core.management.base import BaseCommand
from submissions.models import Exercise
from submissions.utils import update_submissions


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        exercises = Exercise.objects.all().filter(
            in_grading=True
        ).filter(
            grading_ready=False
        ).filter(
            error_state=None
        )
        for exercise in exercises:
            try:
                update_submissions(exercise)
            except Exception as e:
                LOGGER.debug(e)
                continue
