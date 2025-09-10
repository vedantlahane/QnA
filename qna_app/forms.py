# qna_app/forms.py

from django import forms
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from .models import UploadedFile, Conversation
import os

class FileUploadForm(forms.ModelForm):
    """Form for uploading files to the agent system."""
    
    class Meta:
        model = UploadedFile
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'accept': '.pdf,.csv,.sql,.db,.sqlite,.sqlite3',
                'id': 'file-upload-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add validation for supported file types
        self.fields['file'].validators.append(
            FileExtensionValidator(
                allowed_extensions=['pdf', 'csv', 'sql', 'db', 'sqlite', 'sqlite3'],
                message='Only PDF, CSV, and SQL database files are supported.'
            )
        )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if not file:
            raise ValidationError("Please select a file to upload.")
        
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if file.size > max_size:
            raise ValidationError(f"File size must be less than 50MB. Current size: {file.size / (1024*1024):.1f}MB")
        
        # Simple file count check (max 10 files per user)
        if self.user:
            active_files = UploadedFile.objects.filter(user=self.user, is_active=True).count()
            if active_files >= 10:
                raise ValidationError("You have reached the maximum limit of 10 active files.")
        
        return file
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.user:
            instance.user = self.user
        
        # Set file metadata
        file = self.cleaned_data['file']
        instance.original_filename = file.name
        instance.file_size = file.size
        
        # Determine file type
        extension = os.path.splitext(file.name)[1].lower()
        if extension == '.pdf':
            instance.file_type = 'pdf'
        elif extension == '.csv':
            instance.file_type = 'csv'
        elif extension in ['.sql', '.db', '.sqlite', '.sqlite3']:
            instance.file_type = 'sql'
        
        # Generate unique file_id
        if not instance.file_id:
            # Get the next available file_id
            last_file = UploadedFile.objects.order_by('-file_id').first()
            instance.file_id = (last_file.file_id + 1) if last_file else 1
        
        if commit:
            instance.save()
            # No need to increment file count without UserProfile
        
        return instance


class ChatForm(forms.Form):
    """Form for chat messages."""
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none',
            'rows': 3,
            'placeholder': 'Ask me anything about your uploaded documents or general questions...',
            'id': 'id_message'
        }),
        max_length=2000,
        help_text="Maximum 2000 characters"
    )
    
    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        
        if not message:
            raise ValidationError("Please enter a message.")
        
        if len(message) < 3:
            raise ValidationError("Message must be at least 3 characters long.")
        
        return message


class FeedbackForm(forms.ModelForm):
    """Form for user feedback on conversations."""
    
    class Meta:
        model = Conversation
        fields = ['user_rating', 'user_feedback']
        widgets = {
            'user_rating': forms.Select(
                choices=[(i, f"{i} Star{'s' if i != 1 else ''}") for i in range(1, 6)],
                attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'}
            ),
            'user_feedback': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none',
                'rows': 3,
                'placeholder': 'Optional: Tell us how we can improve...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_rating'].required = True
        self.fields['user_feedback'].required = False


class FileSearchForm(forms.Form):
    """Form for searching through uploaded files."""
    
    search_query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Search files by name...',
            'id': 'file-search-input'
        })
    )
    
    file_type = forms.ChoiceField(
        choices=[('', 'All Types')] + UploadedFile.FILE_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + UploadedFile.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'})
    )


class ConversationSearchForm(forms.Form):
    """Form for searching through conversation history."""
    
    search_query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Search conversations...',
            'id': 'conversation-search-input'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'type': 'date'
        })
    )
    
    min_rating = forms.ChoiceField(
        choices=[('', 'Any Rating')] + [(i, f"{i}+ Stars") for i in range(1, 6)],
        required=False,
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'})
    )
