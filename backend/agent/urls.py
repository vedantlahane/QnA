from django.urls import path

from .views import (
    chat_view,
    conversation_detail_view,
    conversations_view,
    document_detail_view,
    documents_view,
)

app_name = "agent"

urlpatterns = [
    path("chat/", chat_view, name="chat"),
    path("conversations/", conversations_view, name="conversation-list"),
    path("conversations/<int:conversation_id>/", conversation_detail_view, name="conversation-detail"),
    path("documents/", documents_view, name="document-list"),
    path("documents/<int:document_id>/", document_detail_view, name="document-detail"),
]
