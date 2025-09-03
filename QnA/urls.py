from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("qna_app.urls")),
]

# Serve media files during development
"""
this is to serve media file during development meaning when DEBUG is True in settings.py, otherwise media files won't be served

"""
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
