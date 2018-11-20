from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.exceptions import PermissionDenied
from django.shortcuts import reverse
from django.dispatch import receiver
from django_lti_login.signals import lti_login_authenticated

from .utils import add_user_to_course


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
    Example things to do after user is fully authenticated.
    You can still raise PermissionDenied here.
    """
    request = kwargs.get('request', None)
    session = request.session
    user = kwargs.get('user', None)
    oauth = getattr(request, 'oauth', None)

    if request and user and oauth:
        course_label = getattr(oauth, 'context_label', None) # IT-101
        course_name = getattr(oauth, 'context_title', None) # Basics on IT
        user_role = getattr(oauth, 'roles', None)
        api_url = getattr(oauth, 'custom_context_api', None)
        api_id = getattr(oauth, 'custom_context_api_id', None)

        if api_id is None or api_url is None or user_role is None:
            # Invalid lti login due to missing information
            print("LTI login request doesn't contain all required "
                  "fields (context_id, context_label, context_title) "
                  "for course membership update. "
                  "User that tried to login: {}".format(user))
            raise PermissionDenied("Not all required fields "
                                   "present in LTI login")

        print("New authentication by {user} for {label} {name}.".format(
            user=user,
            label=course_label,
            name=course_name,
        ))

        session['course_id'] = api_id
        session['course_label'] = course_label
        session['course_name'] = course_name
        session['course_url'] = api_url
        session['user_role'] = user_role

        # Liitetään käyttäjä kirjautumistietojen mukaiseen kurssiin.
        add_user_to_course(user, user_role, course_label, course_name,
                           api_url, api_id)

        # Redirect to notresponded page after login
        oauth.redirect_url = reverse('submissions:index')

        # List LTI params in debug
        if settings.DEBUG:
            print("LTI login accepted for user %s", user)
            for k, v in sorted(oauth.params):
                print("  \w param -- %s: %s", k, v)
