# qna_app/views.py

import json
import time
import uuid
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm

from .models import UploadedFile, Conversation
from .forms import (
    FileUploadForm,
    ChatForm,
    FeedbackForm,
    FileSearchForm,
    ConversationSearchForm,
)

# Agent integration
# Ensure data_app.manager exposes these two functions
from data_app.manager import process_file_for_agent, get_answer_from_agent

logger = logging.getLogger(__name__)


def index(request):
    """Landing page."""
    if request.user.is_authenticated:
        return redirect('qna_app:chat')
    return render(request, 'qna_app/index.html', {
        'title': 'AI Document Assistant',
        'features': [
            'Upload and analyze PDF documents',
            'Query CSV data with natural language',
            'Search SQL databases intelligently',
            'Get answers from the internet',
            'Multi-document conversations',
        ],
    })


def register(request):
    """User registration."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile(request):
    """User profile page."""
    context = {
        'user': request.user,
        'total_files': UploadedFile.objects.filter(user=request.user).count(),
        'total_conversations': Conversation.objects.filter(user=request.user).count(),
    }
    return render(request, 'qna_app/profile.html', context)


@login_required
def chat(request):
    """Main chat interface."""
    # Get or create session ID
    session_id = request.session.get('chat_session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session['chat_session_id'] = session_id

    # Get user's uploaded files
    uploaded_files = UploadedFile.objects.filter(
        user=request.user,
        status='completed',
        is_active=True
    ).order_by('-uploaded_at')

    # Get recent conversations for this session
    recent_conversations = Conversation.objects.filter(
        user=request.user,
        session_id=session_id
    ).order_by('-created_at')[:20]

    # Handle chat form submission (non-AJAX)
    if request.method == 'POST':
        if request.POST.get('action') == 'clear_session':
            if 'chat_session_id' in request.session:
                del request.session['chat_session_id']
            messages.success(request, 'Chat cleared successfully!')
            return redirect('qna_app:chat')

        form = ChatForm(request.POST)
        if form.is_valid():
            return handle_chat_message(request, form, session_id)
    else:
        form = ChatForm()

    context = {
        'form': form,
        'uploaded_files': uploaded_files,
        'recent_conversations': recent_conversations,
        'session_id': session_id,
        'agent_status': get_agent_status(),
    }
    return render(request, 'qna_app/chat.html', context)


def handle_chat_message(request, form, session_id):
    """Handle chat message processing."""
    user_message = form.cleaned_data['message']
    try:
        start_time = time.time()

        # Current agent API accepts only the query string; file/session context is managed internally
        agent_response = get_answer_from_agent(user_message)

        response_time_ms = int((time.time() - start_time) * 1000)

        conversation = Conversation.objects.create(
            user=request.user,
            session_id=session_id,
            user_message=user_message,
            agent_response=agent_response,
            response_time_ms=response_time_ms,
        )

        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': True,
                'response': agent_response,
                'conversation_id': conversation.id,
                'response_time': response_time_ms
            })

        messages.success(request, "Response generated successfully!")
        return redirect('qna_app:chat')

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        error_message = "Sorry, an error occurred while processing the request."
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'error': error_message})
        messages.error(request, error_message)
        return redirect('qna_app:chat')


@login_required
@require_http_methods(["GET", "POST"])
def upload(request):
    """File upload interface."""
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                uploaded_file = form.save()
                uploaded_file.mark_processing()

                success = process_file_for_agent(
                    uploaded_file_path=uploaded_file.file.path,
                    file_id=uploaded_file.file_id,
                )

                if success:
                    uploaded_file.mark_completed()
                    messages.success(
                        request,
                        f'File "{uploaded_file.original_filename}" uploaded and processed successfully!'
                    )
                else:
                    uploaded_file.mark_failed("Agent processing failed")
                    messages.error(
                        request,
                        'File uploaded but processing failed. Please try again or contact support.'
                    )

                return redirect('qna_app:upload')
            except Exception as e:
                logger.error(f"Error uploading file: {e}")
                messages.error(request, f'Error uploading file: {str(e)}')
        else:
            # Fall through to re-render with errors
            pass
    else:
        form = FileUploadForm(user=request.user)

    search_form = FileSearchForm(request.GET or None)
    files_queryset = UploadedFile.objects.filter(user=request.user)

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query')
        file_type = search_form.cleaned_data.get('file_type')
        status = search_form.cleaned_data.get('status')

        if search_query:
            files_queryset = files_queryset.filter(
                Q(original_filename__icontains=search_query)
            )
        if file_type:
            files_queryset = files_queryset.filter(file_type=file_type)
        if status:
            files_queryset = files_queryset.filter(status=status)

    paginator = Paginator(files_queryset.order_by('-uploaded_at'), 10)
    page_number = request.GET.get('page')
    uploaded_files = paginator.get_page(page_number)

    context = {
        'form': form,
        'search_form': search_form,
        'uploaded_files': uploaded_files,
        'can_upload': True,
    }
    return render(request, 'qna_app/upload.html', context)


@login_required
@require_POST
def delete_file(request, file_id):
    """Delete an uploaded file."""
    try:
        uploaded_file = get_object_or_404(
            UploadedFile,
            file_id=file_id,
            user=request.user
        )

        file_name = uploaded_file.original_filename
        if uploaded_file.file and uploaded_file.file.name:
            uploaded_file.file.delete(save=False)
        uploaded_file.delete()
        messages.success(request, f'File "{file_name}" deleted successfully.')
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        messages.error(request, 'Error deleting file. Please try again.')
    return redirect('qna_app:upload')


@login_required
def conversation_history(request):
    """View conversation history."""
    search_form = ConversationSearchForm(request.GET or None)
    conversations_queryset = Conversation.objects.filter(user=request.user)

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        min_rating = search_form.cleaned_data.get('min_rating')

        if search_query:
            conversations_queryset = conversations_queryset.filter(
                Q(user_message__icontains=search_query) |
                Q(agent_response__icontains=search_query)
            )
        if date_from:
            conversations_queryset = conversations_queryset.filter(
                created_at__date__gte=date_from
            )
        if date_to:
            conversations_queryset = conversations_queryset.filter(
                created_at__date__lte=date_to
            )
        if min_rating:
            conversations_queryset = conversations_queryset.filter(
                user_rating__gte=int(min_rating)
            )

    paginator = Paginator(conversations_queryset.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    conversations = paginator.get_page(page_number)

    context = {
        'search_form': search_form,
        'conversations': conversations,
        'total_conversations': conversations_queryset.count(),
    }
    return render(request, 'qna_app/conversation_history.html', context)


@login_required
@require_POST
def rate_conversation(request, conversation_id):
    """Rate a conversation."""
    try:
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            user=request.user
        )
        form = FeedbackForm(request.POST, instance=conversation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you for your feedback!')
        else:
            messages.error(request, 'Invalid feedback data.')
    except Exception as e:
        logger.error(f"Error rating conversation {conversation_id}: {e}")
        messages.error(request, 'Error submitting feedback.')
    return redirect('qna_app:conversation_history')


@login_required
def dashboard(request):
    """User dashboard with statistics and recent activity."""
    user_files = UploadedFile.objects.filter(user=request.user)
    file_stats = {
        'total': user_files.count(),
        'by_status': {
            'completed': user_files.filter(status='completed').count(),
            'processing': user_files.filter(status='processing').count(),
            'failed': user_files.filter(status='failed').count(),
            'pending': user_files.filter(status='pending').count(),
        }
    }

    user_conversations = Conversation.objects.filter(user=request.user)
    conversation_stats = {
        'total': user_conversations.count(),
        'this_month': user_conversations.filter(
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        ).count(),
        'recent': user_conversations.order_by('-created_at')[:5],
        'avg_rating': user_conversations.aggregate(
            avg_rating=Avg('user_rating')
        )['avg_rating'] or 0,
    }

    context = {
        'file_stats': file_stats,
        'conversation_stats': conversation_stats,
        'user_files': user_files.order_by('-uploaded_at')[:10],
    }
    return render(request, 'qna_app/dashboard.html', context)


# API Views for AJAX requests

@login_required
@require_http_methods(["POST"])
def api_chat(request):
    """API endpoint for chat messages (AJAX)."""
    try:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})

        message = (data.get('message') or '').strip()
        if not message:
            return JsonResponse({'success': False, 'error': 'Message is required'})

        # Get or create session ID
        session_id = request.session.get('chat_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session['chat_session_id'] = session_id

        start_time = time.time()

        file_ids = list(UploadedFile.objects.filter(
            user=request.user,
            status='completed',
            is_active=True
        ).values_list('file_id', flat=True))

        try:
            agent_response = get_answer_from_agent(message)
        except Exception as agent_error:
            logger.error(f"Agent error: {agent_error}")
            return JsonResponse({'success': False, 'error': f'Agent error: {str(agent_error)}'})

        response_time_ms = int((time.time() - start_time) * 1000)

        try:
            Conversation.objects.create(
                user=request.user,
                session_id=session_id,
                user_message=message,
                agent_response=agent_response,
                response_time_ms=response_time_ms,
            )
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")

        return JsonResponse({
            'success': True,
            'response': agent_response,
            'session_id': session_id,
            'response_time': response_time_ms
        })

    except Exception as e:
        logger.error(f"API chat error: {e}")
        return JsonResponse({'success': False, 'error': 'Internal server error'})


@login_required
def api_file_status(request, file_id):
    """API endpoint to check file processing status."""
    try:
        uploaded_file = get_object_or_404(
            UploadedFile,
            file_id=file_id,
            user=request.user
        )
        return JsonResponse({
            'success': True,
            'status': uploaded_file.status,
            'filename': uploaded_file.original_filename,
            'error': uploaded_file.processing_error
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def api_system_status(request):
    """API endpoint for system status."""
    try:
        status = get_agent_status()
        return JsonResponse({'success': True, 'status': status})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Utility functions for agent integration
def get_agent_status():
    """Get agent status - simplified version."""
    return {
        "status": "active",
        "message": "Agent system is operational"
    }
