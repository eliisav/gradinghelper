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
        exercises = Exercise.objects.values_list("id", flat=True)

        for pk in exercises:
            try:
                # Retrieve and update if query matching exercise exists
                obj = Exercise.objects.get(
                    id=pk,
                    in_grading=True,
                    stop_polling=False
                )
                update_submissions(obj)
            except Exercise.DoesNotExist:
                continue
            except Exception as e:
                LOGGER.debug(e)
                continue
