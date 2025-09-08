# qna_app/urls.py

from django.urls import path
from . import views

app_name = 'qna_app'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('upload/', views.upload, name='upload'),
    path('history/', views.conversation_history, name='conversation_history'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    
    # File management
    path('delete-file/<int:file_id>/', views.delete_file, name='delete_file'),
    
    # Conversation management
    path('rate-conversation/<int:conversation_id>/', views.rate_conversation, name='rate_conversation'),
    
    # API endpoints
    path('api/chat/', views.api_chat, name='api_chat'),
    path('api/file-status/<int:file_id>/', views.api_file_status, name='api_file_status'),
    path('api/system-status/', views.api_system_status, name='api_system_status'),
]
