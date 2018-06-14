from django.urls import path

from . import views

app_name = 'submissions'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('<int:course_id>/', views.ExerciseListView.as_view(), name='exercises'),
    path('<int:course_id>/<int:exercise_id>/create/', views.create_exercise, name='create'),
    path('<int:course_id>/<int:exercise_id>/', views.SubmissionsView.as_view(), name='submissions'),
    path('<int:course_id>/<int:exercise_id>/<int:sub_id>/', views.get_feedback, name='feedback'),
    
]

