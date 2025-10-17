"""
Forms for knowledge base management.
"""
from django import forms
from django.core.validators import FileExtensionValidator


class KnowledgeBaseUploadForm(forms.Form):
    """Form for uploading PDF documents to the knowledge base."""
    
    pdf_file = forms.FileField(
        label="Upload PDF Document",
        help_text="Select a PDF file to add to your knowledge base. Maximum file size: 10MB",
        validators=[FileExtensionValidator(['pdf'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf',
            'id': 'pdf-file-input'
        })
    )
    
    def clean_pdf_file(self):
        """Validate the uploaded PDF file."""
        pdf_file = self.cleaned_data.get('pdf_file')
        
        if not pdf_file:
            raise forms.ValidationError("Please select a PDF file to upload.")
        
        # Check file size (10MB limit)
        if pdf_file.size > 10 * 1024 * 1024:  # 10MB in bytes
            raise forms.ValidationError("File size must be less than 10MB.")
        
        # Check if file is empty
        if pdf_file.size == 0:
            raise forms.ValidationError("The uploaded file is empty.")
        
        return pdf_file


class KnowledgeBaseSearchForm(forms.Form):
    """Form for searching the knowledge base."""
    
    query = forms.CharField(
        label="Search Query",
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your search query...',
            'id': 'search-query'
        })
    )
    
    top_k = forms.IntegerField(
        label="Number of Results",
        min_value=1,
        max_value=20,
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '20'
        })
    )
    
    def clean_query(self):
        """Validate the search query."""
        query = self.cleaned_data.get('query', '').strip()
        
        if not query:
            raise forms.ValidationError("Please enter a search query.")
        
        if len(query) < 3:
            raise forms.ValidationError("Search query must be at least 3 characters long.")
        
        return query
