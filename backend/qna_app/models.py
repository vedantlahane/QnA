from django.db import models

class UploadedFile(models.Model):
    """Metadata for each uploaded file processed by the agent."""
    original_name = models.CharField(max_length=255)
    stored_path = models.CharField(max_length=1024)
    file_type = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}: {self.original_name} ({self.file_type})"

class Conversation(models.Model):
    """Conversation thread persisted using the agent's thread_id."""
    thread_id = models.CharField(max_length=128, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation {self.thread_id}"

class Message(models.Model):
    """A single chat message belonging to a conversation."""
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.content[:40]}..."
