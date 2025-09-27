from __future__ import annotations

from typing import Any

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from .models import Conversation, Document, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password", "first_name", "last_name")

    def create(self, validated_data: dict[str, Any]):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        username = attrs.get("username")
        password = attrs.get("password")
        user = authenticate(username=username, password=password)
        if not user:
            msg = "Unable to log in with provided credentials."
            raise serializers.ValidationError(msg, code="authorization")
        attrs["user"] = user
        return attrs


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "original_name",
            "file",
            "file_url",
            "size",
            "content_type",
            "processed",
            "processing_error",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "original_name",
            "file_url",
            "size",
            "content_type",
            "processed",
            "processing_error",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_url(self, obj: Document) -> str | None:
        request = self.context.get("request")
        if request is None:
            return obj.file.url if obj.file else None
        return request.build_absolute_uri(obj.file.url) if obj.file else None


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "created_at")
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "title", "documents", "created_at", "updated_at")
        read_only_fields = fields


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ("messages",)


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    conversation_id = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False, allow_blank=True)
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )

    def validate_title(self, value: str) -> str:
        return value.strip()

    def validated_title_or_default(self) -> str:
        title = self.validated_data.get("title") or "New Conversation"
        cleaned = title.strip()
        return cleaned or "New Conversation"
