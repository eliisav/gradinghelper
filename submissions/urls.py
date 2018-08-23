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
    path('auth/', include('django_lti_login.urls')), # XXX: for django-lti-login
    path('auth/login/', auth_login, {'template_name': 'login.html'}, name='login'),
    path('auth/logout/', auth_logout, {'template_name': 'logged_out.html'}, name='logout'),
    path('', views.IndexView.as_view(), name='index'),
    path('courses/', views.CourseListView.as_view(), name='courses'),
    path('grading/', views.GradingListView.as_view(), name='grading'),
    path('courses/<int:course_id>/exercises/', views.ExerciseListView.as_view(), name='exercises'),
    path('courses/<int:course_id>/exercises/update/', views.UpdateExerciseListRedirectView.as_view(), name='update'),
    path('courses/<int:course_id>/exercises/<int:exercise_id>/trace_on/', views.EnableExerciseTraceRedirectView.as_view(), name='trace_on'),
    path('courses/<int:course_id>/exercises/<int:exercise_id>/trace_off/', views.DisableExerciseTraceRedirectView.as_view(), name='trace_off'),
    path('exercises/<int:exercise_id>/submissions/', views.SubmissionsView.as_view(), name='submissions'),
    path('exercises/<int:exercise_id>/submissions/<int:sub_id>/', views.FeedbackView.as_view(), name='feedback'),
    path('exercises/<int:exercise_id>/submissions/release/', views.ReleaseFeedbacksRedirectView.as_view(), name='release'),
    path('exercises/<int:exercise_id>/submissions/graderchange/', views.ChangeGraderRedirectView.as_view(), name='graderchange')
]

