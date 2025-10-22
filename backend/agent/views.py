import json
from typing import Any, Dict, Iterable, List, Optional, Sequence

from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .graph.agent_backend import generate_response
from .graph.pdf_tool import build_pdf_search_tool
from .models import Conversation, Message, MessageAttachment, UploadedDocument


def _trim_text(value: str, limit: int) -> str:
	cleaned = " ".join(value.split())
	if len(cleaned) <= limit:
		return cleaned
	return cleaned[:limit].rstrip() + "..."


def _serialise_document(document: UploadedDocument, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
	url = document.file.url if document.file else ""
	if request and url:
		url = request.build_absolute_uri(url)
	return {
		"id": str(document.pk),
		"name": document.original_name,
		"url": url,
		"size": document.size,
		"uploadedAt": document.created_at.isoformat(),
	}


def _serialise_message(instance: Message, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
	attachments_manager = getattr(instance, "attachments", None)
	if attachments_manager is not None:
		attachment_iterable = attachments_manager.select_related("document")
	else:
		attachment_iterable = MessageAttachment.objects.filter(message=instance).select_related("document")

	attachments = [
		_serialise_document(attachment.document, request)
		for attachment in attachment_iterable
	]
	return {
		"id": str(instance.pk),
		"sender": instance.role,
		"content": instance.content,
		"timestamp": instance.created_at.isoformat(),
		"attachments": attachments,
	}


def _format_updated_at(conversation: Conversation) -> str:
	return conversation.updated_at.strftime("%b %d, %Y")


def _conversation_summary(conversation: Conversation) -> str:
	assistant_reply = (
		Message.objects.filter(conversation=conversation, role="assistant")
		.order_by("-created_at")
		.first()
	)
	latest_message = (
		Message.objects.filter(conversation=conversation)
		.order_by("-created_at")
		.first()
	)
	source = assistant_reply.content if assistant_reply else (latest_message.content if latest_message else "")
	if not source:
		return ""
	return _trim_text(source, 160)


def _default_title(conversation: Conversation) -> str:
	first_user_message = (
		Message.objects.filter(conversation=conversation, role="user")
		.order_by("created_at")
		.first()
	)
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


def _serialise_conversation(
	conversation: Conversation,
	*,
	include_messages: bool = False,
	request: Optional[HttpRequest] = None,
) -> Dict[str, Any]:
	message_count = Message.objects.filter(conversation=conversation).count()
	data: Dict[str, Any] = {
		"id": str(conversation.pk),
		"title": conversation.title or "New chat",
		"summary": conversation.summary or "",
		"updatedAt": _format_updated_at(conversation),
		"updatedAtISO": conversation.updated_at.isoformat(),
		"messageCount": message_count,
	}
	if include_messages:
		message_qs = (
			Message.objects.filter(conversation=conversation)
			.order_by("created_at")
			.prefetch_related("attachments__document")
		)
		data["messages"] = [
			_serialise_message(message, request)
			for message in message_qs
		]
	return data


def _normalise_document_ids(raw_ids: Any) -> List[int]:
	if not isinstance(raw_ids, Sequence):
		return []
	normalised: List[int] = []
	for value in raw_ids:
		if isinstance(value, int):
			normalised.append(value)
		elif isinstance(value, str) and value.isdigit():
			normalised.append(int(value))
	return normalised


def _attach_documents_to_message(message: Message, document_ids: Iterable[int]) -> None:
	documents = list(UploadedDocument.objects.filter(pk__in=document_ids))
	if not documents:
		return
	MessageAttachment.objects.bulk_create(
		[
			MessageAttachment(message=message, document=document)
			for document in documents
		]
	)


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
	document_ids = _normalise_document_ids(payload.get("document_ids"))

	if conversation_id:
		conversation = get_object_or_404(Conversation, pk=conversation_id)
	else:
		conversation = Conversation.objects.create()

	previous_qs = Message.objects.filter(conversation=conversation).order_by("created_at")
	previous_messages = [{"role": msg.role, "content": msg.content} for msg in previous_qs]

	user_message = Message.objects.create(conversation=conversation, role="user", content=user_content)
	if document_ids:
		_attach_documents_to_message(user_message, document_ids)

	reply = generate_response(user_content, previous_messages)

	Message.objects.create(conversation=conversation, role="assistant", content=reply)

	_apply_conversation_metadata(conversation, explicit_title)

	conversation.refresh_from_db()

	response_payload = _serialise_conversation(conversation, include_messages=True, request=request)

	return JsonResponse(response_payload)


@require_http_methods(["GET"])
def conversations_view(request: HttpRequest) -> JsonResponse:
	conversations = Conversation.objects.all()
	data = [_serialise_conversation(conversation) for conversation in conversations]
	return JsonResponse({"conversations": data})


@require_http_methods(["GET"])
def conversation_detail_view(request: HttpRequest, conversation_id: int) -> JsonResponse:
	conversation = get_object_or_404(Conversation, pk=conversation_id)
	return JsonResponse(_serialise_conversation(conversation, include_messages=True, request=request))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def documents_view(request: HttpRequest) -> JsonResponse:
	if request.method == "GET":
		documents = UploadedDocument.objects.all()
		data = [_serialise_document(document, request) for document in documents]
		return JsonResponse({"documents": data})

	uploaded_file: Optional[UploadedFile] = request.FILES.get("file")
	if uploaded_file is None:
		return JsonResponse({"error": "No file provided."}, status=400)

	if not uploaded_file.name.lower().endswith(".pdf"):
		return JsonResponse({"error": "Only PDF files are supported."}, status=400)

	document = UploadedDocument.objects.create(
		file=uploaded_file,
		original_name=uploaded_file.name,
		size=getattr(uploaded_file, "size", 0) or 0,
	)

	try:
		build_pdf_search_tool(force_rebuild=True)
	except Exception as exc:  # pragma: no cover - fail gracefully when embeddings unavailable
		print(f"Warning: unable to rebuild PDF search index ({exc})")

	return JsonResponse(_serialise_document(document, request), status=201)


@csrf_exempt
@require_http_methods(["DELETE"])
def document_detail_view(request: HttpRequest, document_id: int) -> JsonResponse:
	document = get_object_or_404(UploadedDocument, pk=document_id)
	links_manager = getattr(document, "message_links", None)
	if links_manager is not None:
		links_manager.all().delete()
	else:
		MessageAttachment.objects.filter(document=document).delete()
	file_field = document.file
	document.delete()
	if file_field:
		file_field.delete(save=False)

	try:
		build_pdf_search_tool(force_rebuild=True)
	except Exception as exc:  # pragma: no cover - fail gracefully when embeddings unavailable
		print(f"Warning: unable to rebuild PDF search index ({exc})")

	return JsonResponse({"status": "deleted"})


