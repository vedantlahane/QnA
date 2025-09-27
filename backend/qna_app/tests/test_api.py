from __future__ import annotations

import shutil
import tempfile
from unittest import mock

from django.urls import reverse
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase


temp_media_root = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=temp_media_root)
class QnAApiTests(APITestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(temp_media_root, ignore_errors=True)

    def _register_user(self) -> str:
        payload = {
            "username": "alice",
            "email": "alice@example.com",
            "password": "Password123!",
            "first_name": "Alice",
            "last_name": "Tester",
        }
        response = self.client.post(reverse("qna_app:auth-register"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["token"]

    def test_register_login_and_profile(self) -> None:
        token = self._register_user()

        login_payload = {"username": "alice", "password": "Password123!"}
        login_response = self.client.post(reverse("qna_app:auth-login"), login_payload, format="json")
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("token", login_response.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        profile_response = self.client.get(reverse("qna_app:auth-me"))
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["username"], "alice")

    def test_logout_revokes_token(self) -> None:
        token = self._register_user()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        logout_response = self.client.post(reverse("qna_app:auth-logout"))
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)

        profile_response = self.client.get(reverse("qna_app:auth-me"))
        self.assertEqual(profile_response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("qna_app.views.get_answer_from_agent", return_value="Hello from the agent!")
    @mock.patch("qna_app.views.process_file_for_agent", return_value=True)
    def test_file_upload_and_chat_flow(self, mocked_process_file, mocked_agent) -> None:
        token = self._register_user()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        pdf_content = b"Fake PDF content"
        upload = SimpleUploadedFile("test.pdf", pdf_content, content_type="application/pdf")

        upload_response = self.client.post(
            reverse("qna_app:files-list"),
            {"file": upload},
            format="multipart",
        )
        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        document_id = upload_response.data["id"]
        self.assertTrue(upload_response.data["processed"])
        mocked_process_file.assert_called_once()

        chat_payload = {
            "message": "Summarize the document",
            "document_ids": [document_id],
        }
        chat_response = self.client.post(reverse("qna_app:chat"), chat_payload, format="json")
        self.assertEqual(chat_response.status_code, status.HTTP_200_OK)

        self.assertGreaterEqual(len(chat_response.data.get("messages", [])), 2)
        assistant_messages = [m for m in chat_response.data["messages"] if m["role"] == "assistant"]
        self.assertTrue(assistant_messages)
        self.assertEqual(assistant_messages[-1]["content"], "Hello from the agent!")
        mocked_agent.assert_called_once()

        list_documents = self.client.get(reverse("qna_app:files-list"))
        self.assertEqual(list_documents.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_documents.data), 1)
        self.assertTrue(list_documents.data[0]["processed"])

        conversations_response = self.client.get(reverse("qna_app:conversations-list"))
        self.assertEqual(conversations_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(conversations_response.data), 1)

        conversation_id = chat_response.data["id"]
        conversation_detail = self.client.get(
            reverse("qna_app:conversations-detail", args=[conversation_id])
        )
        self.assertEqual(conversation_detail.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(conversation_detail.data.get("messages", [])), 2)

        delete_response = self.client.delete(reverse("qna_app:files-detail", args=[document_id]))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        list_after_delete = self.client.get(reverse("qna_app:files-list"))
        self.assertEqual(list_after_delete.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_after_delete.data), 0)
