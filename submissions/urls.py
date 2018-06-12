from django.urls import path

from . import views

app_name = 'submissions'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('create/', views.ExerciseCreate.as_view(), name='create'),
    path('<int:exercise_id>/', views.SubmissionsView.as_view(), name='submissions'),
    path('<int:exercise_id>/<int:sub_id>/', views.get_feedback, name='feedback'),
    
]

