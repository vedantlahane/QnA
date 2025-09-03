# qna_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Add this line
    path('upload/', views.upload, name='upload'),
    path('chat/', views.chat, name='chat'),
]