from django.urls import path
from . import views

app_name = 'qna_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('chat/', views.chat_page, name='chat_page'),
    path('upload/', views.upload_page, name='upload_page'),
    path('api/upload', views.upload_file, name='upload_file'),
    path('api/chat', views.chat, name='chat'),
]
