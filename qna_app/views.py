from django.shortcuts import render, redirect
from .forms import UploadFileForm
from .models import Conversation, UploadedFile
from data_app.utils import process_file, answer_question

def upload_file(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.save()
            process_file(uploaded.file.path, uploaded.id)
            return redirect("chat")
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})

def chat(request):
    conversations = Conversation.objects.all().order_by("-timestamp")
    if request.method == "POST":
        question = request.POST.get("question")
        latest_file = UploadedFile.objects.last()
        answer = answer_question(question, latest_file.id if latest_file else None)

        Conversation.objects.create(
            question=question, answer=answer, source_file=latest_file
        )
        return redirect("chat")

    return render(request, "chat.html", {"conversations": conversations})
