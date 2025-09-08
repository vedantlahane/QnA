from django.contrib import admin
from .models import UploadedFile, Conversation

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'user', 'file_type', 'status', 'uploaded_at']
    list_filter = ['file_type', 'status', 'uploaded_at']
    search_fields = ['original_filename', 'user__username']
    readonly_fields = ['file_id', 'uploaded_at', 'processed_at']

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_id', 'created_at', 'user_rating']
    list_filter = ['created_at', 'user_rating']
    search_fields = ['user__username', 'user_message', 'agent_response']
    readonly_fields = ['created_at']
