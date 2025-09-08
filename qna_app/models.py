# qna_app/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os

class UploadedFile(models.Model):
    """Model to track uploaded files and their processing status."""

    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF Document'),
        ('csv', 'CSV Data'),
        ('sql', 'SQL Database'),
        ('db', 'SQLite Database'),
        ('sqlite', 'SQLite Database'),
        ('sqlite3', 'SQLite Database'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    file_size = models.BigIntegerField(help_text="File size in bytes")

    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processing_error = models.TextField(blank=True, null=True)

    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    # Agent integration
    file_id = models.PositiveIntegerField(unique=True, help_text="Unique ID for agent processing")
    is_active = models.BooleanField(default=True, help_text="Whether file is available to agent")

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['file_id']),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.user.username})"

    @property
    def file_extension(self):
        """Get file extension."""
        return os.path.splitext(self.original_filename)[1].lower()

    def get_file_size_display(self):
        """Human readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def mark_processing(self):
        """Mark file as processing."""
        self.status = 'processing'
        self.save(update_fields=['status'])

    def mark_completed(self):
        """Mark file as completed."""
        self.status = 'completed'
        self.processed_at = timezone.now()
        self.processing_error = None
        self.save(update_fields=['status', 'processed_at', 'processing_error'])

    def mark_failed(self, error_message):
        """Mark file as failed with error message."""
        self.status = 'failed'
        self.processed_at = timezone.now()
        self.processing_error = error_message
        self.save(update_fields=['status', 'processed_at', 'processing_error'])


class Conversation(models.Model):
    """Model to store chat conversations."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    session_id = models.CharField(max_length=100, db_index=True)

    # Message content
    user_message = models.TextField()
    agent_response = models.TextField()

    # Metadata
    response_time_ms = models.PositiveIntegerField(null=True, blank=True, help_text="Response time in milliseconds")
    tools_used = models.JSONField(default=list, blank=True, help_text="List of tools used in response")
    files_referenced = models.ManyToManyField(UploadedFile, blank=True, help_text="Files referenced in conversation")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    # Quality tracking
    user_rating = models.IntegerField(
        null=True, blank=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="User rating 1-5"
    )
    user_feedback = models.TextField(blank=True, help_text="User feedback")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'session_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Conversation {self.id} - {self.user.username}"

    @property
    def response_time_seconds(self):
        """Get response time in seconds."""
        if self.response_time_ms:
            return self.response_time_ms / 1000
        return None

    def get_short_user_message(self, length=50):
        """Get truncated user message."""
        if len(self.user_message) <= length:
            return self.user_message
        return self.user_message[:length] + "..."
