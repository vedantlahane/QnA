from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from qna_app import views

app_name = 'qna_app_auth'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page=reverse_lazy('qna_app:index')
    ), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html',
        success_url=reverse_lazy('qna_app_auth:password_change_done')
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    path('register/', views.register, name='register'),
]
