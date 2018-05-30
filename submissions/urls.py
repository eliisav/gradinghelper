from django.urls import path

from . import views

app_name = 'submissions'

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:sub_id>/', views.get_sub_info, name='sub_info'),
]

