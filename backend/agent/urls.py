from django.urls import path

from .views import (
    chat_view,
    conversation_detail_view,
    conversations_view,
    current_user,
    document_detail_view,
    documents_view,
    login_user,
    logout_user,
    confirm_password_reset,
    request_password_reset,
    register_user,
    database_connection_view,
    test_database_connection_view,
    database_schema_view,
    execute_sql_query_view,
    sql_query_suggestions_view,
)

app_name = "agent"

urlpatterns = [
    path("chat/", chat_view, name="chat"),
    path("conversations/", conversations_view, name="conversation-list"),
    path("conversations/<int:conversation_id>/", conversation_detail_view, name="conversation-detail"),
    path("documents/", documents_view, name="document-list"),
    path("documents/<int:document_id>/", document_detail_view, name="document-detail"),
    path("auth/register/", register_user, name="register"),
    path("auth/login/", login_user, name="login"),
    path("auth/logout/", logout_user, name="logout"),
    path("auth/me/", current_user, name="current-user"),
    path("auth/password/reset/", request_password_reset, name="password-reset-request"),
    path("auth/password/reset/confirm/", confirm_password_reset, name="password-reset-confirm"),
    path("database/connection/", database_connection_view, name="database-connection"),
    path("database/connection/test/", test_database_connection_view, name="database-connection-test"),
    path("database/query/", execute_sql_query_view, name="database-query"),
    path("database/query/suggestions/", sql_query_suggestions_view, name="database-query-suggestions"),
    path("database/schema/", database_schema_view, name="database-schema"),
]
