"""
Views for knowledge base management.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .models import KnowledgeBase
from .forms import KnowledgeBaseUploadForm, KnowledgeBaseSearchForm
from .service import KnowledgeBaseService

logger = logging.getLogger("knowledgebase.views")


@login_required
def knowledge_base_list(request):
    """Display all user's knowledge base documents."""
    try:
        service = KnowledgeBaseService()
        result = service.get_user_documents(request.user)
        
        if not result['success']:
            messages.error(request, result['error'])
            documents = []
        else:
            documents = result['documents']
        
        # Pagination
        paginator = Paginator(documents, 10)  # 10 documents per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'documents': page_obj,
            'total_documents': len(documents),
            'search_form': KnowledgeBaseSearchForm(),
        }
        
        return render(request, 'knowledgebase/knowledge_base_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in knowledge_base_list: {e}")
        messages.error(request, "An error occurred while loading your documents.")
        return render(request, 'knowledgebase/knowledge_base_list.html', {
            'documents': [],
            'total_documents': 0,
            'search_form': KnowledgeBaseSearchForm(),
        })


@login_required
def knowledge_base_upload(request):
    """Handle PDF upload and processing."""
    if request.method == 'POST':
        form = KnowledgeBaseUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                service = KnowledgeBaseService()
                result = service.upload_pdf(request.user, form.cleaned_data['pdf_file'])
                
                if result['success']:
                    messages.success(
                        request, 
                        f"Successfully uploaded '{result['original_filename']}' "
                        f"and created {result['chunks_created']} chunks."
                    )
                    return redirect('knowledgebase:knowledge_base_list')
                else:
                    messages.error(request, result['error'])
            except Exception as e:
                logger.error(f"Error uploading PDF: {e}")
                messages.error(request, f"An error occurred while processing the PDF: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = KnowledgeBaseUploadForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'knowledgebase/knowledge_base_upload.html', context)


@login_required
@require_http_methods(["POST"])
def knowledge_base_delete(request, document_id):
    """Delete a document and all its chunks."""
    try:
        service = KnowledgeBaseService()
        result = service.delete_document(request.user, document_id)
        
        if result['success']:
            messages.success(
                request, 
                f"Successfully deleted document with {result['deleted_chunks']} chunks."
            )
        else:
            messages.error(request, result['error'])
            
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        messages.error(request, f"An error occurred while deleting the document: {str(e)}")
    
    return redirect('knowledgebase:knowledge_base_list')


@login_required
def knowledge_base_search(request):
    """Perform semantic search on the knowledge base."""
    if request.method == 'POST':
        form = KnowledgeBaseSearchForm(request.POST)
        
        if form.is_valid():
            try:
                service = KnowledgeBaseService()
                query = form.cleaned_data['query']
                top_k = form.cleaned_data['top_k']
                
                results = service.search_knowledge_base(request.user, query, top_k)
                
                context = {
                    'search_form': form,
                    'query': query,
                    'results': results,
                    'results_count': len(results),
                }
                
                return render(request, 'knowledgebase/knowledge_base_search.html', context)
                
            except Exception as e:
                logger.error(f"Error performing search: {e}")
                messages.error(request, f"An error occurred during search: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = KnowledgeBaseSearchForm()
    
    context = {
        'search_form': form,
        'query': '',
        'results': [],
        'results_count': 0,
    }
    
    return render(request, 'knowledgebase/knowledge_base_search.html', context)


@login_required
def knowledge_base_document_detail(request, document_id):
    """View details of a specific document and its chunks."""
    try:
        service = KnowledgeBaseService()
        chunks = service.get_document_chunks(request.user, document_id)
        
        if not chunks:
            messages.error(request, "Document not found.")
            return redirect('knowledgebase:knowledge_base_list')
        
        # Get document info from first chunk
        document_info = {
            'document_id': document_id,
            'filename': chunks[0].original_filename,
            'file_size': chunks[0].file_size,
            'created_at': chunks[0].created_at,
            'chunk_count': len(chunks),
        }
        
        context = {
            'document': document_info,
            'chunks': chunks,
        }
        
        return render(request, 'knowledgebase/knowledge_base_document_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error viewing document {document_id}: {e}")
        messages.error(request, f"An error occurred while loading the document: {str(e)}")
        return redirect('knowledgebase:knowledge_base_list')


@method_decorator(csrf_exempt, name='dispatch')
class KnowledgeBaseAPIView(View):
    """API endpoint for knowledge base operations."""
    
    def post(self, request):
        """Handle API requests for knowledge base operations."""
        try:
            import json
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'search':
                query = data.get('query', '')
                top_k = data.get('top_k', 5)
                
                service = KnowledgeBaseService()
                results = service.search_knowledge_base(request.user, query, top_k)
                
                return JsonResponse({
                    'success': True,
                    'results': [
                        {
                            'chunk_text': result.chunk_text[:200] + '...' if len(result.chunk_text) > 200 else result.chunk_text,
                            'filename': result.original_filename,
                            'chunk_index': result.chunk_index,
                            'similarity_score': getattr(result, 'similarity_score', 0),
                        }
                        for result in results
                    ]
                })
            
            elif action == 'delete':
                document_id = data.get('document_id')
                if not document_id:
                    return JsonResponse({'success': False, 'error': 'Document ID required'})
                
                service = KnowledgeBaseService()
                result = service.delete_document(request.user, document_id)
                
                return JsonResponse(result)
            
            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'})
                
        except Exception as e:
            logger.error(f"Error in KnowledgeBaseAPIView: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
