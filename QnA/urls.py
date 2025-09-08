# QnA/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from qna_app import views as qna_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('qna_app.urls')),
    
    # Authentication URLs
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/profile/', qna_views.profile, name='profile'),
    
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='qna_app:index'
    ), name='logout'),
    
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html',
        success_url='/password_change/done/'
    ), name='password_change'),
    
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
