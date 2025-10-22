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
