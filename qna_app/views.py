from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .forms import UploadFileForm
from .models import Conversation, UploadedFile
from data_app.manager import process_file_for_agent, get_answer_from_agent

def home(request):
    """
    Renders the main single-page application.
    """
    conversations = Conversation.objects.all().order_by("-timestamp")
    context = {
        'conversations': conversations,
        'form': UploadFileForm()
    }
    return render(request, 'index.html', context)


def chat_page(request):
    """
    Renders the chat page with conversation history.
    """
    conversations = Conversation.objects.all().order_by("-timestamp")
    context = {
        'conversations': conversations,
        'current_page': 'chat'
    }
    return render(request, 'chat.html', context)


def upload_page(request):
    """
    Renders the upload page with the file upload form.
    """
    context = {
        'form': UploadFileForm(),
        'current_page': 'upload'
    }
    return render(request, 'upload.html', context)


@csrf_exempt
def upload_file(request):
    """
    Handles file uploads and processes the file for the agent.
    This view is designed to be an API endpoint for the SPA.
    """
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.save()
            process_file_for_agent(uploaded.file.path, uploaded.id)
            return JsonResponse({'status': 'success', 'message': 'File uploaded and processed successfully.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid file upload.'}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@csrf_exempt
def ask_question(request):
    """
    Handles a user's question and returns an AI-generated answer.
    This view is designed to be an API endpoint for the SPA.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            question = data.get('question')

            if not question:
                return JsonResponse({'status': 'error', 'message': 'Question cannot be empty.'}, status=400)

            # The agent's brain will decide which tool to use
            answer = get_answer_from_agent(question)

            # Save the conversation with a temporary source_file of None
            # You could later add logic to retrieve and link the correct source file
            Conversation.objects.create(
                question=question, 
                answer=answer, 
                source_file=None
            )
            
            return JsonResponse({'status': 'success', 'answer': answer})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
