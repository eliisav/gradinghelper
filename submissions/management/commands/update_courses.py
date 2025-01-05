"""
Management command to get new submissions from Plussa. This is ment to be
called frequently by crontab.
"""

import logging

from django.core.management.base import BaseCommand
from submissions.models import Course
from submissions.utils import update_course_details, get_exercises


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        courses = Course.objects.values_list("id", flat=True)

        for pk in courses:
            try:
                # Retrieve and update if query matching course exists
                course = Course.objects.get(id=pk, archived=False)
                update_course_details(course)
                get_exercises(course)
            except Course.DoesNotExist:
                continue
            except Exception as e:
                LOGGER.debug(e)
                continue
