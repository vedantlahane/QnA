from django.db import models


class Conversation(models.Model):
	title = models.CharField(max_length=255, blank=True)
	summary = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-updated_at"]

	def __str__(self) -> str:  # pragma: no cover - debug helper
		return self.title or f"Conversation {self.pk}"


class Message(models.Model):
	ROLE_CHOICES = [
		("user", "User"),
		("assistant", "Assistant"),
	]

	conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
	role = models.CharField(max_length=20, choices=ROLE_CHOICES)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["created_at"]

	def __str__(self) -> str:  # pragma: no cover - debug helper
		return f"{self.role}: {self.content[:30]}"


class UploadedDocument(models.Model):
	file = models.FileField(upload_to="uploaded_docs/")
	original_name = models.CharField(max_length=255)
	size = models.PositiveBigIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self) -> str:  # pragma: no cover - debug helper
		return self.original_name


class MessageAttachment(models.Model):
	message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
	document = models.ForeignKey(UploadedDocument, on_delete=models.CASCADE, related_name="message_links")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["created_at"]

	def __str__(self) -> str:  # pragma: no cover - debug helper
		document_pk = getattr(self.document, "pk", None)
		message_pk = getattr(self.message, "pk", None)
		return f"Attachment {document_pk} -> {message_pk}"
