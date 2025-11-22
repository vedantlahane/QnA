from django.test import TestCase
from django.urls import reverse


class HealthEndpointTests(TestCase):
	def test_health_endpoint_returns_ok(self) -> None:
		response = self.client.get(reverse("agent:health"))
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload.get("status"), "ok")
		self.assertIn("checks", payload)
		db_check = payload["checks"].get("database", {})
		self.assertEqual(db_check.get("status"), "ok")


class ChatOperationalErrorHandlingTests(TestCase):
	def setUp(self) -> None:
		from django.contrib.auth import get_user_model

		User = get_user_model()
		self.user = User.objects.create_user(username="testuser", email="test@example.com", password="pw")

	def test_chat_view_handles_db_operational_error(self):
		from unittest.mock import patch
		from contextlib import contextmanager
		from django.db.utils import OperationalError

		self.client.login(username="testuser", password="pw")

		@contextmanager
		def fail_connection(_):
			raise OperationalError("Simulated DB failure")
			yield

		with patch("agent.views.use_sql_connection", fail_connection):
			response = self.client.post(
				"/api/chat/",
				data={"message": "Hi"},
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 500)
		payload = response.json()
		self.assertIn("error", payload)

# Create your tests here.
