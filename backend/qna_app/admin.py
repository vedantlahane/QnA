from django.contrib import admin
from .models import UploadedFile, Conversation, Message

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_name', 'file_type', 'created_at')
    search_fields = ('original_name', 'file_type')

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'thread_id', 'created_at')
    search_fields = ('thread_id',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('conversation__thread_id', 'content')
