"""
Forms for the AI Engine application.

This module contains forms for knowledge base management and PDF uploads.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import os


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class PDFUploadForm(forms.Form):
    """
    Form for uploading PDF files to the knowledge base.
    
    Validates file size (5MB max), file type (PDF only), and file count (5 files max).
    """
    
    pdf_files = MultipleFileField(
        widget=MultipleFileInput(attrs={
            'accept': '.pdf',
            'class': 'form-control',
            'id': 'pdf-files'
        }),
        help_text="Upload up to 5 PDF files (5MB each max). Files will be processed and embedded into your knowledge base.",
        label="PDF Files"
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional description for these files...'
        }),
        required=False,
        max_length=500,
        help_text="Optional description to help identify these files in your knowledge base.",
        label="Description"
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_pdf_files(self):
        """
        Validate uploaded PDF files.
        
        Returns:
            List of validated file objects
            
        Raises:
            ValidationError: If files don't meet requirements
        """
        files = self.files.getlist('pdf_files')
        
        if not files:
            raise ValidationError(_("Please select at least one PDF file."))
        
        if len(files) > 5:
            raise ValidationError(_("You can upload a maximum of 5 files at once."))
        
        # Check existing files for this user
        if self.user:
            from .models import KnowledgeBase
            existing_files = KnowledgeBase.objects.filter(
                user=self.user,
                file_type='pdf'
            ).values_list('original_filename', flat=True).distinct()
            
            if len(existing_files) + len(files) > 5:
                raise ValidationError(
                    _("You already have %(existing_count)d files. You can upload a maximum of 5 files total.") % {
                        'existing_count': len(existing_files)
                    }
                )
        
        validated_files = []
        total_size = 0
        
        for file in files:
            # Check file extension
            if not file.name.lower().endswith('.pdf'):
                raise ValidationError(_("File '%(filename)s' is not a PDF file.") % {
                    'filename': file.name
                })
            
            # Check file size (5MB = 5 * 1024 * 1024 bytes)
            max_size = 5 * 1024 * 1024
            if file.size > max_size:
                raise ValidationError(
                    _("File '%(filename)s' is too large. Maximum size is 5MB.") % {
                        'filename': file.name
                    }
                )
            
            # Check if file already exists for this user
            if self.user and file.name in existing_files:
                raise ValidationError(
                    _("File '%(filename)s' already exists in your knowledge base.") % {
                        'filename': file.name
                    }
                )
            
            total_size += file.size
            validated_files.append(file)
        
        # Check total size of all files
        if total_size > 25 * 1024 * 1024:  # 25MB total
            raise ValidationError(_("Total size of all files cannot exceed 25MB."))
        
        return validated_files

    def clean_description(self):
        """Clean and validate description field."""
        description = self.cleaned_data.get('description', '').strip()
        return description


class KnowledgeBaseDeleteForm(forms.Form):
    """
    Form for confirming deletion of knowledge base entries.
    """
    
    confirm_delete = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="I understand this will permanently delete the selected files and their embeddings."
    )
    
    entry_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    def clean_entry_ids(self):
        """Validate entry IDs."""
        entry_ids = self.cleaned_data.get('entry_ids', '')
        if not entry_ids:
            raise ValidationError(_("No entries selected for deletion."))
        
        try:
            # Convert comma-separated string to list of integers
            ids = [int(id.strip()) for id in entry_ids.split(',') if id.strip()]
            if not ids:
                raise ValidationError(_("No valid entry IDs provided."))
            return ids
        except ValueError:
            raise ValidationError(_("Invalid entry IDs provided."))
