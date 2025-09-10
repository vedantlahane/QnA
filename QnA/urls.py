# QnA/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('qna_app.urls', 'qna_app'), namespace='qna_app')),
    path('auth/', include(('qna_app.auth_urls', 'qna_app_auth'), namespace='qna_app_auth')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
