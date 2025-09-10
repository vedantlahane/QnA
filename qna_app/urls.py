from django.urls import path
from . import views

app_name = 'qna_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),  # add if keeping Sign Up
    path('api/upload', views.upload_file, name='upload_file'),
    path('api/chat', views.chat, name='chat'),
]
