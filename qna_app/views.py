from django.shortcuts import render, redirect
from .forms import UploadFileForm
from .models import Conversation, UploadedFile
# Corrected import to use the new manager module
from data_app.manager import process_file_for_agent, get_answer_from_agent

def home(request):
    """
    Renders the home page.
    """
    return render(request, 'home.html')

def upload_file(request):
    """
    Handles file uploads and processes the file for the agent.
    """
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.save()
            # Call the new function that handles multi-tool processing
            process_file_for_agent(uploaded.file.path, uploaded.id)
            return redirect("chat")
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})

def chat(request):
    """
    Handles chat interactions, displays conversation history, and gets answers from the agent.
    """
    conversations = Conversation.objects.all().order_by("-timestamp")
    if request.method == "POST":
        question = request.POST.get("question")
        
        # The agent's brain will decide which file to use, or search the internet.
        answer = get_answer_from_agent(question)

        # The source_file is not directly known by the view, as the agent
        # could have used any file or no file at all.
        Conversation.objects.create(
            question=question, 
            answer=answer, 
            source_file=None 
        )
        return redirect("chat")

    return render(request, "chat.html", {"conversations": conversations})
