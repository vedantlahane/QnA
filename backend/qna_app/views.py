from __future__ import annotations

import logging
from typing import Iterable

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from data_app.manager import get_answer_from_agent, process_file_for_agent

from .models import Conversation, Document, Message
from .serializers import (
    ChatRequestSerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    DocumentSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        payload = {
            "user": UserSerializer(user).data,
            "token": token.key,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        payload = {
            "user": UserSerializer(user).data,
            "token": token.key,
        }
        return Response(payload, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs) -> Response:
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Document.objects
            .filter(owner=self.request.user)
            .order_by("-created_at")
        )

    def perform_create(self, serializer: DocumentSerializer) -> None:
        uploaded_file = serializer.validated_data.get("file")
        if uploaded_file is None:
            raise ValidationError({"file": "No file provided."})

        document = serializer.save(owner=self.request.user)
        document.original_name = getattr(uploaded_file, "name", document.file.name)
        document.size = getattr(uploaded_file, "size", 0)
        document.content_type = getattr(uploaded_file, "content_type", "") or ""
        processing_error = ""
        processed = False

        try:
            processed = process_file_for_agent(document.file.path, document.pk)
        except Exception as exc:  # pragma: no cover - agent errors are logged
            processing_error = str(exc)
            logger.exception("Failed to process uploaded file", exc_info=exc)
        else:
            processing_error = "" if processed else "Unable to process file."

        document.processed = processed
        document.processing_error = processing_error
        document.save(update_fields=[
            "original_name",
            "size",
            "content_type",
            "processed",
            "processing_error",
            "updated_at",
        ])

    def perform_destroy(self, instance: Document) -> None:
        stored_name = instance.file.name if instance.file else None
        storage = instance.file.storage if instance.file else None
        conversation_ids = list(instance.conversations.values_list("id", flat=True))
        super().perform_destroy(instance)
        if storage and stored_name:
            try:  # pragma: no cover - filesystem dependent
                storage.delete(stored_name)
            except Exception:
                logger.warning("Unable to delete stored file %s", stored_name)
        if conversation_ids:
            Conversation.objects.filter(id__in=conversation_ids).update(updated_at=timezone.now())


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Conversation.objects
            .filter(owner=self.request.user)
            .prefetch_related("documents", "messages")
            .order_by("-updated_at")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationSerializer


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        conversation = self._get_or_create_conversation(request.user, data)
        message_text: str = data["message"].strip()
        if not message_text:
            raise ValidationError({"message": "Message cannot be empty."})

        self._attach_documents(conversation, data.get("document_ids", []), request.user)

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=message_text,
        )
        conversation.save(update_fields=["updated_at"])

        try:
            agent_response = get_answer_from_agent(
                message_text,
                thread_id=conversation.thread_id,
            )
        except Exception as exc:  # pragma: no cover - external dependency failures
            logger.exception("Agent invocation failed", exc_info=exc)
            agent_response = (
                "I'm sorry, something went wrong while generating a response. "
                "Please try again later."
            )

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=agent_response,
        )
        conversation.save(update_fields=["updated_at"])

        response_serializer = ConversationDetailSerializer(conversation, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def _get_or_create_conversation(self, user, data: dict) -> Conversation:
        conversation_id = data.get("conversation_id")
        title = data.get("title", "").strip()

        if conversation_id:
            conversation = get_object_or_404(Conversation, pk=conversation_id, owner=user)
            if title and conversation.title != title:
                conversation.title = title
                conversation.save(update_fields=["title", "updated_at"])
            return conversation

        inferred_title = title or data.get("message", "Conversation")[:80]
        conversation = Conversation.objects.create(
            owner=user,
            title=inferred_title.strip() or "Conversation",
        )
        return conversation

    def _attach_documents(
        self,
        conversation: Conversation,
        document_ids: Iterable[int],
        user,
    ) -> Iterable[Document]:
        if not document_ids:
            return conversation.documents.all()

        documents = list(
            Document.objects.filter(owner=user, id__in=document_ids).order_by("-created_at")
        )
        unprocessed = [doc.original_name for doc in documents if not doc.processed]
        if unprocessed:
            raise ValidationError(
                {
                    "document_ids": (
                        "Some documents are still processing: " + ", ".join(unprocessed)
                    )
                }
            )
        conversation.documents.add(*documents)
        conversation.save(update_fields=["updated_at"])
        return documents or conversation.documents.all()
