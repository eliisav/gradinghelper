from django.urls import path

from . import views

app_name = 'submissions'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('<int:course_id>/exercises/', views.ExerciseListView.as_view(), name='exercises'),
    path('<int:course_id>/exercises/update/', views.update_exercise_view, name='update'),
    path('<int:course_id>/exercises/<int:exercise_id>/trace/', views.enable_exercise_trace, name='trace'),
    path('<int:course_id>/exercises/<int:exercise_id>/submissions/', views.SubmissionsView.as_view(), name='submissions'),
    path('<int:course_id>/exercises/<int:exercise_id>/submissions/<int:sub_id>/', views.get_feedback, name='feedback'),
    
]

