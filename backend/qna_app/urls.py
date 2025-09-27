from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChatView,
    ConversationViewSet,
    DocumentViewSet,
    LoginView,
    LogoutView,
    ProfileView,
    RegisterView,
)

app_name = "qna_app"

router = DefaultRouter()
router.register(r"files", DocumentViewSet, basename="files")
router.register(r"conversations", ConversationViewSet, basename="conversations")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", ProfileView.as_view(), name="auth-me"),
    path("chat/", ChatView.as_view(), name="chat"),
    path("", include(router.urls)),
]
