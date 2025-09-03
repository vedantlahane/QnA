from django.shortcuts import render, redirect
from .forms import UploadFileForm
from data_app.utils import process_file

def upload_file(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.save()
            process_file(uploaded.file.path)  # parse + prepare vectors
            return redirect("chat")
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})
