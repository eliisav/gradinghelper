from django.urls import path

from . import views

app_name = 'submissions'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('create/', views.ExerciseCreate.as_view(), name='create'),
    path('<int:exercise_id>/', views.get_submissions, name='get_subs'),
    path('<slug>/submissions', views.ExerciseView.as_view(), name='submissions'),
    path('<int:exercise_id>/submissions/<int:sub_id>/', views.get_feedback, name='feedback'),
    
]

