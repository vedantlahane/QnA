import json
from typing import Any, Dict, List, Optional

from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .graph.agent_backend import generate_response
from .models import Conversation, Message


def _trim_text(value: str, limit: int) -> str:
	cleaned = " ".join(value.split())
	if len(cleaned) <= limit:
		return cleaned
	return cleaned[:limit].rstrip() + "..."


def _serialise_message(instance: Message) -> Dict[str, Any]:
	return {
		"id": str(instance.pk),
		"sender": instance.role,
		"content": instance.content,
		"timestamp": instance.created_at.isoformat(),
	}


def _format_updated_at(conversation: Conversation) -> str:
	return conversation.updated_at.strftime("%b %d, %Y")


def _conversation_summary(conversation: Conversation) -> str:
	assistant_reply = Message.objects.filter(conversation=conversation, role="assistant").order_by("-created_at").first()
	latest_message = Message.objects.filter(conversation=conversation).order_by("-created_at").first()
	source = assistant_reply.content if assistant_reply else (latest_message.content if latest_message else "")
	if not source:
		return ""
	return _trim_text(source, 160)


def _default_title(conversation: Conversation) -> str:
	first_user_message = Message.objects.filter(conversation=conversation, role="user").order_by("created_at").first()
	source = first_user_message.content if first_user_message else "New chat"
	return _trim_text(source, 60) or "New chat"


def _apply_conversation_metadata(conversation: Conversation, explicit_title: Optional[str]) -> None:
	updates: Dict[str, str] = {}

	if isinstance(explicit_title, str) and explicit_title.strip():
		desired_title = _trim_text(explicit_title.strip(), 255)
		if desired_title != conversation.title:
			updates["title"] = desired_title
	elif not conversation.title:
		generated_title = _default_title(conversation)
		if generated_title != conversation.title:
			updates["title"] = generated_title

	generated_summary = _conversation_summary(conversation)
	if generated_summary != conversation.summary:
		updates["summary"] = generated_summary

	if updates:
		for field, value in updates.items():
			setattr(conversation, field, value)
		conversation.save(update_fields=list(updates.keys()))


def _serialise_conversation(conversation: Conversation, include_messages: bool = False) -> Dict[str, Any]:
	data: Dict[str, Any] = {
		"id": str(conversation.pk),
		"title": conversation.title or "New chat",
		"summary": conversation.summary or "",
		"updatedAt": _format_updated_at(conversation),
		"updatedAtISO": conversation.updated_at.isoformat(),
	"messageCount": Message.objects.filter(conversation=conversation).count(),
	}
	if include_messages:
		message_qs = Message.objects.filter(conversation=conversation).order_by("created_at")
		data["messages"] = [_serialise_message(message) for message in message_qs]
	return data


@csrf_exempt
@require_http_methods(["POST"])
def chat_view(request: HttpRequest) -> JsonResponse:
	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON payload."}, status=400)

	message = payload.get("message") if isinstance(payload, dict) else None
	if not isinstance(message, str) or not message.strip():
		return JsonResponse({"error": "A non-empty 'message' field is required."}, status=400)

	user_content = message.strip()
	conversation_id = payload.get("conversation_id") if isinstance(payload, dict) else None
	explicit_title = payload.get("title") if isinstance(payload, dict) else None

	if conversation_id:
		conversation = get_object_or_404(Conversation, pk=conversation_id)
	else:
		conversation = Conversation.objects.create()

	previous_qs = Message.objects.filter(conversation=conversation).order_by("created_at")
	previous_messages = [{"role": msg.role, "content": msg.content} for msg in previous_qs]

	Message.objects.create(conversation=conversation, role="user", content=user_content)

	reply = generate_response(user_content, previous_messages)

	Message.objects.create(conversation=conversation, role="assistant", content=reply)

	_apply_conversation_metadata(conversation, explicit_title)

	conversation.refresh_from_db()

	response_payload = _serialise_conversation(conversation, include_messages=True)

	return JsonResponse(response_payload)


@require_http_methods(["GET"])
def conversations_view(request: HttpRequest) -> JsonResponse:
	conversations = Conversation.objects.all()
	data = [_serialise_conversation(conversation) for conversation in conversations]
	return JsonResponse({"conversations": data})


@require_http_methods(["GET"])
def conversation_detail_view(request: HttpRequest, conversation_id: int) -> JsonResponse:
	conversation = get_object_or_404(Conversation, pk=conversation_id)
	return JsonResponse(_serialise_conversation(conversation, include_messages=True))


