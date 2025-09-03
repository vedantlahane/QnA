from django.urls import path
from . import views

urlpatterns = [
    # The home view will now render the entire SPA
    path('', views.home, name='home'),
    
    # These are new API endpoints for the front end to interact with
    path('api/upload/', views.upload_file, name='api_upload'),
    path('api/ask/', views.ask_question, name='api_ask'),
]
