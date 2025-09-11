import os
import uuid
import json

from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

from .forms import UploadFileForm
from .models import UploadedFile, Conversation, Message

# Agent manager API
from data_app.manager import process_file_for_agent, get_answer_from_agent


@login_required
def dashboard(request):
    return render(request, 'qna/dashboard.html')


@login_required
def profile(request):
    return render(request, 'registration/profile.html', {"user": request.user})


@login_required
def chat_page(request):
    """Render the chat page for document Q&A."""
    return render(request, 'qna/chat.html')


@login_required
def upload_page(request):
    """Render the upload page for document uploads."""
    return render(request, 'qna/upload.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('qna_app:dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. Please log in.")
            # Uses the app-scoped auth namespace provided by qna_app/auth_urls.py
            return redirect('qna_app_auth:login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def index(request):
    """Simple index page to verify app is running."""
    if request.user.is_authenticated:
        return redirect('qna_app:dashboard')
    return render(request, 'qna/index.html')


@csrf_exempt
@require_http_methods(["POST"])
def upload_file(request):
    """Handle file uploads, persist metadata, and register as an agent tool."""
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest('Invalid form data')

    f = form.cleaned_data['file']

    # Ensure media/uploads exists
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    # Create a unique stored filename to avoid collisions
    ext = os.path.splitext(f.name)[1].lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(upload_dir, stored_name)

    # Save the uploaded file to disk
    with open(stored_path, 'wb+') as dest:
        for chunk in f.chunks():
            dest.write(chunk)

    # Persist metadata in DB
    meta = UploadedFile.objects.create(
        original_name=f.name,
        stored_path=stored_path,
        file_type=ext.lstrip('.')
    )

    # Register with agent (process/vectorize/configure)
    ok = process_file_for_agent(stored_path, meta.id)

    return JsonResponse({
        'id': meta.id,
        'original_name': meta.original_name,
        'file_type': meta.file_type,
        'stored_path': meta.stored_path,
        'registered': bool(ok),
    })


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """Accept a JSON body with {query, thread_id?} and return agent response; persist messages."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    query = payload.get('query')
    thread_id = payload.get('thread_id') or 'web-thread'
    if not query:
        return HttpResponseBadRequest('Missing query')

    # Ensure conversation exists
    convo, _ = Conversation.objects.get_or_create(thread_id=thread_id)

    # Persist user message
    Message.objects.create(conversation=convo, role='user', content=query)

    # Ask the agent
    answer = get_answer_from_agent(query, thread_id=thread_id)

    # Persist assistant reply
    Message.objects.create(conversation=convo, role='assistant', content=answer)

    return JsonResponse({'thread_id': thread_id, 'answer': answer})
