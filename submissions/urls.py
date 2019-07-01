from django.urls import path, include
from django.contrib.auth import views as auth

from . import views

app_name = 'submissions'


if hasattr(auth, 'LoginView'):
    auth_login = auth.LoginView.as_view()
    auth_logout = auth.LogoutView.as_view()
else:
    auth_login = auth.login
    auth_logout = auth.logout


urlpatterns = [
    path('auth/', include('django_lti_login.urls')),  # XXX: django-lti-login

    path('auth/login/', auth_login, {'template_name': 'login.html'},
         name='login'),

    path('auth/logout/', auth_logout, {'template_name': 'logged_out.html'},
         name='logout'),

    path('', views.IndexView.as_view(), name='index'),

    path('courses/', views.CourseListView.as_view(), name='courses'),

    path('courses/<int:course_id>/exercises/',
         views.ExerciseListView.as_view(), name='exercises'),

    path('courses/<int:course_id>/exercises/update/',
         views.GetExercisesRedirectView.as_view(),
         name='get_exercises'),

    path('courses/<int:course_id>/exercises/grading_on/',
         views.EnableExerciseGradingRedirectView.as_view(), name='grading_on'),

    path('courses/<int:course_id>/exercises/<int:exercise_id>/update/',
         views.UpdateExerciseInGradingView.as_view(),
         name='update_exercise'),

    path('courses/<int:course_id>/exercises/<int:exercise_id>/grading_off/',
         views.DisableExerciseGradingRedirectView.as_view(),
         name='grading_off'),

    path('courses/<int:course_id>/exercises/<int:exercise_id>/handle_error/',
         views.HandleExerciseErrorRedirectView.as_view(),
         name='handle_error'),

    path('exercises/<int:exercise_id>/submissions/update/',
         views.UpdateSubmissionsRedirectView.as_view(),
         name='update_submissions'),

    path('exercises/<int:exercise_id>/submissions/grading',
         views.GradingListView.as_view(), name='grading'),

    path('exercises/<int:exercise_id>/submissions/all/',
         views.SubmissionsFormView.as_view(), name='submissions'),

    path('exercises/<int:exercise_id>/submissions/<int:sub_id>/',
         views.FeedbackView.as_view(), name='feedback'),

    path('exercises/<int:exercise_id>/submissions/release/',
         views.ReleaseFeedbacksRedirectView.as_view(), name='release'),

    path('exercises/<int:exercise_id>/submissions/batch_assess/',
         views.BatchAssessRedirectView.as_view(), name='batch_assess'),

    path('exercises/<int:exercise_id>/submissions/setgrader/',
         views.SetGraderRedirectView.as_view(), name='set_grader'),

    path('exercises/<int:exercise_id>/submissions/json/',
         views.CreateJsonFromFeedbacksView.as_view(), name='json'),

    path('exercises/<int:exercise_id>/submissions/undo_release/',
         views.UndoLatestReleaseRedirectView.as_view(), name='undo'),

    path('exercises/<int:exercise_id>/submissions/csv/',
         views.DownloadCsvView.as_view(), name='csv'),
]
