"""
Receiver hooks to use oauth data provided by Aalto-LeTech/django-lti-login.
This is modified from the example app:
https://github.com/Aalto-LeTech/django-lti-login/blob/master/example/
"""

import logging
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import reverse
from django.dispatch import receiver
from django_lti_login.signals import lti_login_authenticated

from .utils import add_user_to_course


logger = logging.getLogger(__name__)


@receiver(lti_login_authenticated)
def store_last_login(sender, **kwargs):
    """
    Example thing to do before user is actually authenticated, but does exists.
    Django sets user.last_login after this, so it's last time to use it.
    """
    request = kwargs.get('request', None)
    user = kwargs.get('user', None)
    if request and user:
        request.session['last_login'] = str(user.last_login)


@receiver(user_logged_in)
def store_course_info(sender, **kwargs):
    """
    Get required course information after user is fully authenticated.
    """
    request = kwargs.get('request', None)
    user = kwargs.get('user', None)
    oauth = getattr(request, 'oauth', None)

    if request and user and oauth:
        required_fields = ["context_label", "context_title", "roles",
                           "custom_context_api", "custom_context_api_id",
                           "custom_user_api_token"]
        accepted_roles = ["Instructor", "TA,TeachingAssistant"]
        login_info = {}

        for field in required_fields:
            login_info[field] = getattr(oauth, field, None)

        if None in login_info.values():
            logger.error("LTI login request doesn't contain all required "
                         "fields for course membership update. User that "
                         "tried to login: {}".format(user))
            raise PermissionDenied("Not all required fields "
                                   "present in LTI login")

        if login_info["roles"] not in accepted_roles:
            raise PermissionDenied("Allowed only for teachers and TA's")

        logger.info("New authentication by {user} for {label} {name}.".format(
            user=user,
            label=login_info["context_label"],
            name=login_info["context_title"],
        ))

        # Add user to the course according to login information
        if not add_user_to_course(user, login_info):
            messages.error(request, f"Requested course not found. Only "
                                    f"teachers can create new courses.")

        # Redirect to notresponded page after login
        oauth.redirect_url = reverse('submissions:index')

        # List LTI params in debug
        if settings.DEBUG:
            logger.debug("LTI login accepted for user %s", user)
            for k, v in sorted(oauth.params):
                print("  \w param -- %s: %s", k, v)
