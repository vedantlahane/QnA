from django import forms
from .models import UploadedFile

class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': '.pdf,.csv,.sql',
                'id': 'id_file'
            })
        }
