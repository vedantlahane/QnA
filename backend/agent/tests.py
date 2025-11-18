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

# Create your tests here.
