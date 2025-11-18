import json
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from django.contrib.auth import authenticate, get_user_model, login as auth_login, logout as auth_logout
from django.core.files.uploadedfile import UploadedFile
from django.db import connections, transaction
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from langchain_community.document_loaders import PyPDFLoader


@require_http_methods(["GET"])
def health_view(request: HttpRequest) -> JsonResponse:
	db_status = "ok"
	db_error: Optional[str] = None
	try:
		with connections["default"].cursor() as cursor:
			cursor.execute("SELECT 1")
	except Exception as exc:  # pragma: no cover - exact exception depends on backend drivers
		db_status = "error"
		db_error = str(exc)
	status_code = 200 if db_status == "ok" else 503
	return JsonResponse(
		{
			"status": "ok" if db_status == "ok" else "degraded",
			"timestamp": timezone.now().isoformat(),
			"checks": {
				"database": {
					"status": db_status,
					"error": db_error,
				}
			},
		},
		status=status_code,
	)

from .graph.agent_backend import generate_response
from .graph.pdf_tool import build_pdf_search_tool
from .graph.sql_tool import (
	AVAILABLE_DATABASE_MODES,
	SQLConnectionDetails,
	clear_sql_toolkit_cache,
	describe_sql_schema,
	execute_raw_sql_query,
	get_environment_connection,
	generate_sql_suggestions,
	resolve_connection_details,
	test_sql_connection,
	use_sql_connection,
)
from .graph.tavily_search_tool import get_tavily_search_tool
from .models import (
	Conversation,
	DatabaseConnection,
	Message,
	MessageAttachment,
	PasswordResetToken,
	UploadedDocument,
)
RESET_TOKEN_TTL = timedelta(hours=1)


UserModel = get_user_model()


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


def _serialise_user(user: Any) -> Dict[str, Any]:
	full_name = user.get_full_name().strip()
	return {
		"id": user.pk,
		"email": user.email,
		"name": full_name or user.username,
	}


def _ensure_authenticated(request: HttpRequest) -> Optional[JsonResponse]:
	if not request.user.is_authenticated:
		return JsonResponse({"error": "Authentication required."}, status=401)
	return None


def _generate_reset_token() -> str:
	return secrets.token_urlsafe(32)


def _serialise_message(instance: Message, request: Optional[HttpRequest] = None) -> Dict[str, Any]:
	attachments_manager = getattr(instance, "attachments", None)
	if attachments_manager is not None:
		attachment_iterable = attachments_manager.select_related("document")
	else:
		attachment_iterable = MessageAttachment.objects.filter(message=instance).select_related("document")

	attachments: List[Dict[str, Any]] = []
	current_user_id: Optional[int] = None
	if request and hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
		current_user_id = getattr(request.user, "pk", None)

	for attachment in attachment_iterable:
		document = attachment.document
		document_user_id = getattr(document, "user_id", None)
		if current_user_id is not None and document_user_id not in (None, current_user_id):
			continue
		attachments.append(_serialise_document(document, request))
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


def _clean_email(value: Any) -> Optional[str]:
	if not isinstance(value, str):
		return None
	email = value.strip().lower()
	return email or None


def _clean_name(value: Any) -> str:
	if not isinstance(value, str):
		return ""
	return value.strip()


def _set_user_name(user: Any, raw_name: str) -> None:
	name = raw_name.strip()
	if not name:
		return
	parts = name.split(None, 1)
	user.first_name = parts[0]
	if len(parts) > 1:
		user.last_name = parts[1]
	user.save(update_fields=["first_name", "last_name"] if len(parts) > 1 else ["first_name"])


@csrf_exempt
@require_http_methods(["POST"])
def register_user(request: HttpRequest) -> JsonResponse:
	try:
		payload = json.loads(request.body or b"{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON payload."}, status=400)

	email = _clean_email(payload.get("email"))
	password = payload.get("password")
	name = _clean_name(payload.get("name"))

	if not email or not isinstance(password, str) or len(password) < 8:
		return JsonResponse({"error": "Provide a valid email and a password with at least 8 characters."}, status=400)

	if UserModel.objects.filter(username=email).exists():
		return JsonResponse({"error": "An account with this email already exists."}, status=400)

	user = UserModel.objects.create_user(username=email, email=email, password=password)
	if name:
		_set_user_name(user, name)

	auth_login(request, user)
	return JsonResponse({"user": _serialise_user(user)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login_user(request: HttpRequest) -> JsonResponse:
	try:
		payload = json.loads(request.body or b"{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON payload."}, status=400)

	email = _clean_email(payload.get("email"))
	password = payload.get("password")

	if not email or not isinstance(password, str):
		return JsonResponse({"error": "Email and password are required."}, status=400)

	user = authenticate(request, username=email, password=password)
	if user is None:
		return JsonResponse({"error": "Invalid credentials."}, status=401)

	auth_login(request, user)
	return JsonResponse({"user": _serialise_user(user)})


@csrf_exempt
@require_http_methods(["POST"])
def logout_user(request: HttpRequest) -> JsonResponse:
	auth_logout(request)
	return JsonResponse({"status": "signed_out"})


@require_http_methods(["GET"])
def current_user(request: HttpRequest) -> JsonResponse:
	if request.user.is_authenticated:
		return JsonResponse({"user": _serialise_user(request.user)})
	return JsonResponse({"user": None})


@csrf_exempt
@require_http_methods(["POST"])
def request_password_reset(request: HttpRequest) -> JsonResponse:
	try:
		payload = json.loads(request.body or b"{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON payload."}, status=400)

	email = _clean_email(payload.get("email"))
	if not email:
		return JsonResponse({"error": "Email is required."}, status=400)

	user = UserModel.objects.filter(username=email).first()
	reset_token_value: Optional[str] = None

	if user is not None:
		PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
		reset_token_value = _generate_reset_token()
		PasswordResetToken.objects.create(
			user=user,
			token=reset_token_value,
			expires_at=timezone.now() + RESET_TOKEN_TTL,
		)

	return JsonResponse(
		{
			"message": "If an account exists for that email, you'll receive password reset instructions shortly.",
			"resetToken": reset_token_value,
		}
	)


@csrf_exempt
@require_http_methods(["POST"])
def confirm_password_reset(request: HttpRequest) -> JsonResponse:
	try:
		payload = json.loads(request.body or b"{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON payload."}, status=400)

	token_value = payload.get("token")
	new_password = payload.get("password")

	if not isinstance(token_value, str) or not token_value.strip():
		return JsonResponse({"error": "A valid reset token is required."}, status=400)

	if not isinstance(new_password, str) or len(new_password) < 8:
		return JsonResponse({"error": "Password must be at least 8 characters."}, status=400)

	try:
		reset_record = PasswordResetToken.objects.select_related("user").get(token=token_value.strip())
	except PasswordResetToken.DoesNotExist:
		return JsonResponse({"error": "Invalid or expired reset token."}, status=400)

	if reset_record.used or reset_record.expires_at <= timezone.now():
		if not reset_record.used:
			reset_record.used = True
			reset_record.save(update_fields=["used"])
		return JsonResponse({"error": "Invalid or expired reset token."}, status=400)

	user = reset_record.user

	with transaction.atomic():
		user.set_password(new_password)
		user.save(update_fields=["password"])
		reset_record.used = True
		reset_record.save(update_fields=["used"])
		PasswordResetToken.objects.filter(user=user, used=False).exclude(pk=reset_record.pk).update(used=True)

	auth_login(request, user)
	return JsonResponse({"user": _serialise_user(user)})


_TAVILY_KEYWORDS = {
	"weather",
	"temperature",
	"forecast",
	"today",
	"current",
	"news",
	"latest",
	"update",
	"happening",
	"now",
	"stock",
	"price",
	"market",
	"headline",
	"score",
	"match",
	"traffic",
	"event",
}


def _should_query_tavily(message: str) -> bool:
	lower_message = message.lower()
	return any(keyword in lower_message for keyword in _TAVILY_KEYWORDS)


def _format_tavily_results(payload: Any) -> Optional[str]:
	if payload is None:
		return None
	if isinstance(payload, str):
		return payload.strip() or None
	if not isinstance(payload, dict):
		return str(payload)
	lines: List[str] = []
	answer = payload.get("answer")
	if isinstance(answer, str) and answer.strip():
		lines.append(f"Direct answer: {answer.strip()}")
	results = payload.get("results")
	if isinstance(results, list):
		for item in results[:3]:
			if not isinstance(item, dict):
				continue
			title = item.get("title") or item.get("url") or "Result"
			snippet = item.get("content") or item.get("snippet") or "No summary available."
			url = item.get("url")
			formatted = f"- {title}: {snippet}"
			if url:
				formatted += f" (Source: {url})"
			lines.append(formatted)
	if not lines:
		return None
	return "\n".join(lines)


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


def _get_user_database_connection(user: Any) -> Optional[DatabaseConnection]:
	if user is None or not hasattr(user, "database_connection"):
		return None
	try:
		return user.database_connection
	except DatabaseConnection.DoesNotExist:
		return None



def _database_connection_payload(user: Any) -> Optional[Dict[str, Any]]:
	instance = _get_user_database_connection(user)
	if instance:
		details = _resolve_user_database_details(user)
		if details:
			return _serialise_database_connection(instance=instance, details=details, source="user")
	return None


def _environment_connection_payload() -> Optional[Dict[str, Any]]:
	env_details = get_environment_connection()
	if env_details is None:
		return None
	return _serialise_database_connection(instance=None, details=env_details, source="environment")


def _parse_database_payload(payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
	mode = payload.get("mode")
	if not isinstance(mode, str) or not mode.strip():
		raise ValueError("Database mode is required.")
	display_name = payload.get("displayName")
	if isinstance(display_name, str):
		display_name = display_name.strip()
	else:
		display_name = None
	sqlite_path = payload.get("sqlitePath")
	if isinstance(sqlite_path, str):
		sqlite_path = sqlite_path.strip()
	else:
		sqlite_path = None
	connection_string = payload.get("connectionString")
	if isinstance(connection_string, str):
		connection_string = connection_string.strip()
	else:
		connection_string = None
	return {
		"mode": mode.strip(),
		"display_name": display_name,
		"sqlite_path": sqlite_path,
		"connection_string": connection_string,
	}


@csrf_exempt
@require_http_methods(["GET", "POST", "DELETE"])
def database_connection_view(request: HttpRequest) -> JsonResponse:
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

	if request.method == "GET":
		payload = _database_connection_payload(request.user)
		env_payload = _environment_connection_payload()
		return JsonResponse(
			{
				"connection": payload,
				"availableModes": list(AVAILABLE_DATABASE_MODES),
				"environmentFallback": env_payload,
			}
		)

	if request.method == "DELETE":
		instance = _get_user_database_connection(request.user)
		identifier = _connection_identifier(instance)
		if instance:
			instance.delete()
		if identifier:
			clear_sql_toolkit_cache(identifier)
		else:
			clear_sql_toolkit_cache()
		env_payload = _environment_connection_payload()
		return JsonResponse(
			{
				"status": "reset",
				"connection": None,
				"availableModes": list(AVAILABLE_DATABASE_MODES),
				"environmentFallback": env_payload,
			}
		)

	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON payload."}, status=400)

	try:
		parsed = _parse_database_payload(payload)
	except ValueError as exc:
		return JsonResponse({"error": str(exc)}, status=400)

	mode = parsed["mode"]
	display_name = parsed["display_name"]
	sqlite_path = parsed["sqlite_path"]
	connection_string = parsed["connection_string"]
	should_test = bool(payload.get("testConnection"))

	try:
		connection_details = resolve_connection_details(
			mode or "",
			sqlite_path=sqlite_path,
			connection_url=connection_string,
			display_name=display_name,
		)
		if should_test:
			test_sql_connection(connection_details)
	except ValueError as exc:
		return JsonResponse({"error": str(exc)}, status=400)
	except Exception as exc:
		return JsonResponse({"error": f"Unable to connect: {exc}"}, status=400)

	clean_display = display_name or ""
	clean_sqlite_path = sqlite_path or (connection_details.sqlite_path or "")
	clean_connection_url = (
		connection_details.uri if connection_details.mode == DatabaseConnection.MODE_URL else ""
	)

	DatabaseConnection.objects.update_or_create(
		user=request.user,
		defaults={
			"mode": connection_details.mode,
			"sqlite_path": clean_sqlite_path,
			"connection_url": clean_connection_url,
			"display_name": clean_display,
		},
	)

	clear_sql_toolkit_cache()

	instance = _get_user_database_connection(request.user)
	response_details = _resolve_user_database_details(request.user) or connection_details
	response_payload = _serialise_database_connection(
		instance=instance,
		details=response_details,
		source="user",
	)

	return JsonResponse(
		{
			"connection": response_payload,
			"availableModes": list(AVAILABLE_DATABASE_MODES),
			"tested": should_test,
			"environmentFallback": _environment_connection_payload(),
		}
	)


@csrf_exempt
@require_http_methods(["POST"])
def test_database_connection_view(request: HttpRequest) -> JsonResponse:
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON payload."}, status=400)

	try:
		parsed = _parse_database_payload(payload)
		mode_value = parsed["mode"] or ""
		connection_details = resolve_connection_details(
			mode_value,
			sqlite_path=parsed["sqlite_path"],
			connection_url=parsed["connection_string"],
			display_name=parsed["display_name"],
		)
		test_sql_connection(connection_details)
	except ValueError as exc:
		return JsonResponse({"ok": False, "message": str(exc)}, status=400)
	except Exception as exc:
		return JsonResponse({"ok": False, "message": f"Unable to connect: {exc}"}, status=400)

	return JsonResponse(
		{
			"ok": True,
			"message": "Connection successful.",
			"resolvedSqlitePath": connection_details.sqlite_path,
		}
	)


@csrf_exempt
@require_http_methods(["POST"])
def execute_sql_query_view(request: HttpRequest) -> JsonResponse:
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON payload."}, status=400)

	query = payload.get("query")
	if not isinstance(query, str) or not query.strip():
		return JsonResponse({"error": "A SQL query is required."}, status=400)

	limit_value = payload.get("limit")
	limit = 200
	if limit_value is not None:
		try:
			limit = int(limit_value)
		except (TypeError, ValueError):
			return JsonResponse({"error": "The 'limit' field must be an integer."}, status=400)
		if limit <= 0:
			return JsonResponse({"error": "The 'limit' field must be greater than zero."}, status=400)
		if limit > 1000:
			limit = 1000

	connection_details = _resolve_user_database_details(request.user)
	if connection_details is None:
		connection_details = get_environment_connection()
	if connection_details is None:
		return JsonResponse({"error": "No database connection is configured."}, status=400)

	try:
		response_payload = execute_raw_sql_query(connection_details, query, limit=limit)
	except ValueError as exc:
		return JsonResponse({"error": str(exc)}, status=400)
	except Exception as exc:
		return JsonResponse({"error": f"Unable to execute query: {exc}"}, status=400)

	response_payload.update(
		{
			"connection": {
				"label": connection_details.label,
				"mode": connection_details.mode,
			},
		}
	)
	return JsonResponse(response_payload)


@csrf_exempt
@require_http_methods(["POST"])
def sql_query_suggestions_view(request: HttpRequest) -> JsonResponse:
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON payload."}, status=400)

	query = payload.get("query")
	if not isinstance(query, str) or not query.strip():
		return JsonResponse({"error": "A SQL query is required."}, status=400)

	include_schema = bool(payload.get("includeSchema", False))
	max_suggestions_value = payload.get("maxSuggestions")
	max_suggestions = 3
	if max_suggestions_value is not None:
		try:
			max_suggestions = int(max_suggestions_value)
		except (TypeError, ValueError):
			return JsonResponse({"error": "The 'maxSuggestions' field must be an integer."}, status=400)
		if max_suggestions <= 0:
			return JsonResponse({"error": "The 'maxSuggestions' field must be greater than zero."}, status=400)
		max_suggestions = min(max_suggestions, 5)

	connection_details = _resolve_user_database_details(request.user)
	if connection_details is None:
		connection_details = get_environment_connection()
	if connection_details is None:
		return JsonResponse({"error": "No database connection is configured."}, status=400)

	schema_snapshot = None
	schema_error: Optional[str] = None
	if include_schema:
		try:
			schema_snapshot = describe_sql_schema(connection_details)
		except Exception as exc:
			schema_error = f"Unable to load schema details: {exc}"

	try:
		suggestion_payload = generate_sql_suggestions(
			connection_details,
			query,
			schema_snapshot=schema_snapshot,
			max_suggestions=max_suggestions,
		)
	except ValueError as exc:
		return JsonResponse({"error": str(exc)}, status=400)
	except EnvironmentError as exc:
		return JsonResponse({"error": str(exc)}, status=400)
	except Exception as exc:
		return JsonResponse({"error": f"Unable to generate suggestions: {exc}"}, status=500)

	response_payload: Dict[str, Any] = {
		"originalQuery": query.strip(),
		"analysis": suggestion_payload.get("analysis"),
		"suggestions": suggestion_payload.get("suggestions", []),
		"connection": {
			"label": connection_details.label,
			"mode": connection_details.mode,
		},
		"generatedAt": timezone.now().isoformat(),
		"schemaIncluded": bool(schema_snapshot),
	}
	if schema_error:
		response_payload["schemaError"] = schema_error

	return JsonResponse(response_payload)


@require_http_methods(["GET"])
def database_schema_view(request: HttpRequest) -> JsonResponse:
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

	connection_details = _resolve_user_database_details(request.user)
	if connection_details is None:
		connection_details = get_environment_connection()
	if connection_details is None:
		return JsonResponse({"error": "No database connection is configured."}, status=400)

	try:
		schema_payload = describe_sql_schema(connection_details)
	except Exception as exc:
		return JsonResponse({"error": f"Unable to load schema: {exc}"}, status=400)

	schema_payload.update(
		{
			"connection": {
				"label": connection_details.label,
				"mode": connection_details.mode,
			},
			"generatedAt": timezone.now().isoformat(),
		}
	)
	return JsonResponse(schema_payload)

def _resolve_user_database_details(user: Any) -> Optional[SQLConnectionDetails]:
	instance = _get_user_database_connection(user)
	if instance is None:
		return None
	try:
		return resolve_connection_details(
			instance.mode,
			sqlite_path=instance.sqlite_path or None,
			connection_url=instance.connection_url or None,
			display_name=instance.display_name or None,
		)
	except ValueError as exc:
		print(f"Invalid database configuration for user {getattr(user, 'pk', 'unknown')}: {exc}")
		return None


def _serialise_database_connection(
	*,
	instance: Optional[DatabaseConnection],
	details: SQLConnectionDetails,
	source: str,
) -> Dict[str, Any]:
	display_name = (instance.display_name or "").strip() if instance else ""
	if not display_name:
		display_name = details.label
	payload: Dict[str, Any] = {
		"mode": details.mode,
		"displayName": display_name,
		"label": details.label,
		"source": source,
		"isDefault": source != "user",
		"resolvedSqlitePath": details.sqlite_path,
	}
	if details.mode == DatabaseConnection.MODE_SQLITE:
		payload["sqlitePath"] = instance.sqlite_path if instance else details.sqlite_path
		payload["connectionString"] = None
	else:
		payload["sqlitePath"] = None
		payload["connectionString"] = (
			instance.connection_url if instance and instance.connection_url else None
		)
	return payload


def _connection_identifier(instance: Optional[DatabaseConnection]) -> Optional[str]:
	if instance is None:
		return None
	try:
		details = resolve_connection_details(
			instance.mode,
			sqlite_path=instance.sqlite_path or None,
			connection_url=instance.connection_url or None,
			display_name=instance.display_name or None,
		)
		return details.identifier
	except ValueError:
		return None


def _attach_documents_to_message(message: Message, documents: Iterable[UploadedDocument]) -> None:
	docs = list(documents)
	if not docs:
		return
	MessageAttachment.objects.bulk_create(
		[
			MessageAttachment(message=message, document=document)
			for document in docs
		]
	)


def _gather_document_context(documents: Sequence[UploadedDocument], query: str) -> Optional[str]:
	if not documents or not query.strip():
		return None

	def _extract_document_snippets(limit: int = 3) -> List[str]:
		snippets: List[str] = []
		processed_documents: Set[int] = set()
		for document in documents:
			file_field = document.file
			if not file_field:
				continue
			try:
				loader = PyPDFLoader(file_field.path)
				pages = loader.load()
			except Exception as exc:  # pragma: no cover - tolerate parsing edge cases
				print(f"Warning: unable to read PDF {document.pk} ({exc})")
				continue

			processed_documents.add(document.pk)
			for page in pages:
				snippet = page.page_content.strip()
				if snippet:
					snippets.append(snippet)
				if len(snippets) >= limit:
					return snippets
		if not snippets and processed_documents:
			doc_names = [doc.original_name for doc in documents if doc.pk in processed_documents and doc.original_name]
			descriptor = ", ".join(dict.fromkeys(name.strip() for name in doc_names if name.strip())) or "the uploaded PDF"
			return [
				f"No extractable text was found in {descriptor}. It may be a scanned document. Try uploading a text-based version."
			]
		return snippets

	try:
		vector_store = build_pdf_search_tool()
	except Exception as exc:  # pragma: no cover - embeddings might be unavailable locally
		print(f"Warning: unable to load PDF vector store ({exc})")
		fallback_snippets = _extract_document_snippets()
		if fallback_snippets:
			unique_names = ", ".join(
				dict.fromkeys(document.original_name for document in documents if document.original_name)
			)
			header = f"Document excerpts from {unique_names}:" if unique_names else "Document excerpts:"
			separator = "\n\n---\n\n"
			return f"{header}\n\n" + separator.join(fallback_snippets)
		return None

	allowed_sources: Set[Path] = set()
	for document in documents:
		file_field = document.file
		if not file_field:
			continue
		try:
			allowed_sources.add(Path(file_field.path).resolve())
		except Exception:
			continue

	if not allowed_sources:
		return None

	try:
		search_results = vector_store.similarity_search(query, k=8)
	except Exception as exc:  # pragma: no cover - tolerate search failures
		print(f"Warning: PDF similarity search failed ({exc})")
		fallback_snippets = _extract_document_snippets()
		if fallback_snippets:
			unique_names = ", ".join(
				dict.fromkeys(document.original_name for document in documents if document.original_name)
			)
			header = f"Document excerpts from {unique_names}:" if unique_names else "Document excerpts:"
			separator = "\n\n---\n\n"
			return f"{header}\n\n" + separator.join(fallback_snippets)
		return None

	context_chunks: List[str] = []
	for result in search_results:
		metadata_source = result.metadata.get("source") if isinstance(result.metadata, dict) else None
		if not metadata_source:
			continue
		try:
			resolved_source = Path(metadata_source).resolve()
		except Exception:
			continue

		if resolved_source not in allowed_sources:
			continue

		snippet = result.page_content.strip()
		if snippet:
			context_chunks.append(snippet)

		if len(context_chunks) >= 3:
			break

	if not context_chunks:
		fallback_snippets = _extract_document_snippets()
		if fallback_snippets:
			unique_names = ", ".join(
				dict.fromkeys(document.original_name for document in documents if document.original_name)
			)
			header = f"Document excerpts from {unique_names}:" if unique_names else "Document excerpts:"
			separator = "\n\n---\n\n"
			return f"{header}\n\n" + separator.join(fallback_snippets)
		return None

	unique_names = ", ".join(dict.fromkeys(document.original_name for document in documents if document.original_name))
	header = f"Document excerpts from {unique_names}:" if unique_names else "Document excerpts:"
	separator = "\n\n---\n\n"
	return f"{header}\n\n" + separator.join(context_chunks)


@csrf_exempt
@require_http_methods(["POST"])
def chat_view(request: HttpRequest) -> JsonResponse:
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

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
		conversation = get_object_or_404(Conversation, pk=conversation_id, user=request.user)
	else:
		conversation = Conversation.objects.create(user=request.user)

	previous_qs = Message.objects.filter(conversation=conversation).order_by("created_at")
	previous_messages = [{"role": msg.role, "content": msg.content} for msg in previous_qs]

	selected_documents = (
		list(UploadedDocument.objects.filter(pk__in=document_ids, user=request.user))
		if document_ids
		else []
	)
	context_documents: List[UploadedDocument] = list(selected_documents)

	if not context_documents:
		attached_document_ids = (
			MessageAttachment.objects.filter(message__conversation=conversation)
			.values_list("document_id", flat=True)
			.distinct()
		)
		if attached_document_ids:
			context_documents = list(
				UploadedDocument.objects.filter(pk__in=attached_document_ids, user=request.user)
			)

	user_message = Message.objects.create(conversation=conversation, role="user", content=user_content)
	if selected_documents:
		_attach_documents_to_message(user_message, selected_documents)

	document_context = _gather_document_context(context_documents, user_content)

	external_context: Optional[str] = None
	if (not document_context) and _should_query_tavily(user_content):
		try:
			searcher = get_tavily_search_tool()
			results = searcher.run(user_content)
			external_context = _format_tavily_results(results)
		except Exception as exc:  # pragma: no cover - avoid hard failures when Tavily unavailable
			print(f"Warning: Tavily search failed ({exc})")

	connection_details = _resolve_user_database_details(request.user)
	with use_sql_connection(connection_details):
		reply = generate_response(
			user_content,
			previous_messages,
			document_context=document_context,
			external_context=external_context,
		)

	Message.objects.create(conversation=conversation, role="assistant", content=reply)

	_apply_conversation_metadata(conversation, explicit_title)

	conversation.refresh_from_db()

	response_payload = _serialise_conversation(conversation, include_messages=True, request=request)

	return JsonResponse(response_payload)


@require_http_methods(["GET"])
def conversations_view(request: HttpRequest) -> JsonResponse:
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

	conversations = Conversation.objects.filter(user=request.user).order_by("-updated_at")
	data = [
		_serialise_conversation(conversation)
		for conversation in conversations
	]
	return JsonResponse({"conversations": data})

@csrf_exempt
@require_http_methods(["GET", "DELETE"])
def conversation_detail_view(request: HttpRequest, conversation_id: int) -> JsonResponse:
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

	conversation = get_object_or_404(Conversation, pk=conversation_id, user=request.user)

	if request.method == "DELETE":
		conversation.delete()
		return JsonResponse({"status": "deleted"})

	return JsonResponse(_serialise_conversation(conversation, include_messages=True, request=request))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def documents_view(request: HttpRequest) -> JsonResponse:
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

	if request.method == "GET":
		documents = UploadedDocument.objects.filter(user=request.user).order_by("-created_at")
		data = [_serialise_document(document, request) for document in documents]
		return JsonResponse({"documents": data})

	uploaded_file: Optional[UploadedFile] = request.FILES.get("file")
	if uploaded_file is None:
		return JsonResponse({"error": "No file provided."}, status=400)

	if not uploaded_file.name.lower().endswith(".pdf"):
		return JsonResponse({"error": "Only PDF files are supported."}, status=400)

	document = UploadedDocument.objects.create(
		user=request.user,
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
	auth_response = _ensure_authenticated(request)
	if auth_response is not None:
		return auth_response

	document = get_object_or_404(UploadedDocument, pk=document_id, user=request.user)
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


