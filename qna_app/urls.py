from django.urls import path
from . import views

urlpatterns = [
    # The home view will now render the entire SPA
    path('', views.home, name='home'),
    
    # Separate page routes for better navigation
    path('chat/', views.chat_page, name='chat'),
    path('upload/', views.upload_page, name='upload'),
    
    # These are new API endpoints for the front end to interact with
    path('api/upload/', views.upload_file, name='api_upload'),
    path('api/ask/', views.ask_question, name='api_ask'),
]
