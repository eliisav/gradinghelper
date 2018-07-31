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
    path('<int:course_id>/exercises/', views.ExerciseListView.as_view(), name='exercises'),
    path('<int:course_id>/exercises/update/', views.update_exercise_view, name='update'),
    path('<int:course_id>/exercises/<int:exercise_id>/trace/', views.enable_exercise_trace, name='trace'),
    path('<int:course_id>/exercises/<int:exercise_id>/submissions/', views.SubmissionsView.as_view(), name='submissions'),
    path('<int:course_id>/exercises/<int:exercise_id>/submissions/<int:sub_id>/', views.get_feedback, name='feedback'),
    
]

