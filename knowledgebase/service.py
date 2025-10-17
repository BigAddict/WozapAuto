"""
Knowledge Base Service for PDF processing, embedding, and semantic search.
"""
import logging
import uuid
import os
from typing import List, Dict, Any, Optional
from django.contrib.auth.models import User
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pypdf
import numpy as np

from .models import KnowledgeBase

logger = logging.getLogger("knowledgebase.service")


class KnowledgeBaseService:
    """Service for managing knowledge base documents with PDF processing and semantic search."""
    
    def __init__(self):
        """Initialize the service with Google Gemini embeddings."""
        self.embeddings = None
        self._initialize_embeddings()
        
        # Text splitter configuration
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def _initialize_embeddings(self):
        """Initialize Google Gemini embeddings with error handling."""
        try:
            if not settings.GOOGLE_API_KEY:
                logger.error("GOOGLE_API_KEY not configured")
                return
                
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=settings.GOOGLE_API_KEY,
                task_type="retrieval_document"  # Optimize for document retrieval
            )
            logger.info("Successfully initialized Google Gemini embeddings")
        except Exception as e:
            logger.error(f"Failed to initialize Google Gemini embeddings: {e}")
            self.embeddings = None
    
    def upload_pdf(self, user: User, pdf_file) -> Dict[str, Any]:
        """
        Upload and process a PDF file, extracting text, chunking, and creating embeddings.
        
        Args:
            user: User who uploaded the file
            pdf_file: Django uploaded file object
            
        Returns:
            Dictionary with upload results and statistics
        """
        if not self.embeddings:
            return {
                'success': False,
                'error': 'Embeddings not available. Please check Google API key configuration.'
            }
        
        try:
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Save file to storage
            file_path = default_storage.save(
                f'knowledge_base/{pdf_file.name}',
                ContentFile(pdf_file.read())
            )
            
            # Reset file pointer for processing
            pdf_file.seek(0)
            
            # Extract text from PDF
            text_content = self._extract_pdf_text(pdf_file)
            if not text_content.strip():
                # Clean up saved file if no text extracted
                default_storage.delete(file_path)
                return {
                    'success': False,
                    'error': 'No text content found in PDF'
                }
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(text_content)
            
            # Process chunks in transaction
            with transaction.atomic():
                created_chunks = []
                
                for i, chunk_text in enumerate(chunks):
                    # Generate embedding for chunk
                    try:
                        # Try to get 768 dimensions by truncating if needed
                        embedding_vector = self.embeddings.embed_query(chunk_text)
                        
                        # If we get 3072 dimensions, truncate to 768 for efficiency
                        if len(embedding_vector) == 3072:
                            embedding_vector = embedding_vector[:768]
                            logger.info(f"Truncated embedding from 3072 to 768 dimensions for chunk {i}")
                        elif len(embedding_vector) != 768:
                            logger.warning(f"Unexpected embedding dimension: {len(embedding_vector)} for chunk {i}")
                            
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for chunk {i}: {e}")
                        continue
                    
                    # Create knowledge base entry
                    kb_entry = KnowledgeBase.objects.create(
                        user=user,
                        original_filename=pdf_file.name,
                        file_path=file_path,
                        file_size=pdf_file.size,
                        file_type='pdf',
                        chunk_text=chunk_text,
                        chunk_index=i,
                        parent_document_id=document_id,
                        embedding=embedding_vector,
                        metadata={
                            'total_chunks': len(chunks),
                            'chunk_size': len(chunk_text),
                            'file_size': pdf_file.size
                        }
                    )
                    created_chunks.append(kb_entry)
                
                if not created_chunks:
                    # Clean up file if no chunks created
                    default_storage.delete(file_path)
                    return {
                        'success': False,
                        'error': 'Failed to create embeddings for any chunks'
                    }
            
            logger.info(f"Successfully processed PDF {pdf_file.name} into {len(created_chunks)} chunks")
            
            return {
                'success': True,
                'document_id': document_id,
                'chunks_created': len(created_chunks),
                'file_size': pdf_file.size,
                'original_filename': pdf_file.name
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_file.name}: {e}")
            # Clean up file if error occurred
            try:
                if 'file_path' in locals():
                    default_storage.delete(file_path)
            except:
                pass
            
            return {
                'success': False,
                'error': f'Error processing PDF: {str(e)}'
            }
    
    def _extract_pdf_text(self, pdf_file) -> str:
        """Extract text content from PDF file."""
        try:
            pdf_reader = pypdf.PdfReader(pdf_file)
            text_content = ""
            
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            
            return text_content.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    def search_knowledge_base(self, user: User, query: str, top_k: int = 5) -> List[KnowledgeBase]:
        """
        Perform semantic search on user's knowledge base.
        
        Args:
            user: User whose knowledge base to search
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of KnowledgeBase entries ordered by relevance
        """
        if not self.embeddings:
            logger.warning("Embeddings not available for search")
            return []
        
        try:
            # Generate embedding for query
            query_embedding = self.embeddings.embed_query(query)
            
            # If we get 3072 dimensions, truncate to 768 for efficiency
            if len(query_embedding) == 3072:
                query_embedding = query_embedding[:768]
                logger.info("Truncated query embedding from 3072 to 768 dimensions")
            elif len(query_embedding) != 768:
                logger.warning(f"Unexpected query embedding dimension: {len(query_embedding)}")
            
            # Perform vector similarity search
            # Using raw SQL for pgvector similarity search
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Convert embedding to proper format for pgvector
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                
                cursor.execute("""
                    SELECT id, chunk_text, parent_document_id, chunk_index, 
                           original_filename, page_number, metadata,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM knowledgebase_knowledgebase 
                    WHERE user_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, [embedding_str, user.id, embedding_str, top_k])
                
                results = cursor.fetchall()
                
                # Convert to KnowledgeBase objects
                kb_entries = []
                for row in results:
                    kb_entry = KnowledgeBase.objects.get(id=row[0])
                    kb_entry.similarity_score = row[7]  # Add similarity score
                    kb_entries.append(kb_entry)
                
                return kb_entries
                
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []
    
    def delete_document(self, user: User, document_id: str) -> Dict[str, Any]:
        """
        Delete a document and all its chunks.
        
        Args:
            user: User who owns the document
            document_id: Document ID to delete
            
        Returns:
            Dictionary with deletion results
        """
        try:
            # Get all chunks for this document
            chunks = KnowledgeBase.objects.filter(
                user=user,
                parent_document_id=document_id
            )
            
            if not chunks.exists():
                return {
                    'success': False,
                    'error': 'Document not found'
                }
            
            # Get file path for cleanup
            file_path = chunks.first().file_path
            
            # Delete all chunks
            deleted_count = chunks.count()
            chunks.delete()
            
            # Clean up file
            try:
                if file_path and default_storage.exists(file_path):
                    default_storage.delete(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete file {file_path}: {e}")
            
            logger.info(f"Deleted document {document_id} with {deleted_count} chunks")
            
            return {
                'success': True,
                'deleted_chunks': deleted_count,
                'document_id': document_id
            }
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return {
                'success': False,
                'error': f'Error deleting document: {str(e)}'
            }
    
    def get_user_documents(self, user: User) -> Dict[str, Any]:
        """
        Get all documents for a user with statistics.
        
        Args:
            user: User whose documents to retrieve
            
        Returns:
            Dictionary with document statistics
        """
        try:
            # Get all chunks for the user
            all_chunks = KnowledgeBase.objects.filter(user=user)
            
            # Group by parent_document_id to get unique documents
            documents_dict = {}
            for chunk in all_chunks:
                doc_id = chunk.parent_document_id
                if doc_id not in documents_dict:
                    documents_dict[doc_id] = {
                        'document_id': doc_id,
                        'filename': chunk.original_filename,
                        'file_size': chunk.file_size,
                        'chunk_count': 0,
                        'created_at': chunk.created_at
                    }
                documents_dict[doc_id]['chunk_count'] += 1
            
            # Convert to list and sort by creation date (newest first)
            document_stats = list(documents_dict.values())
            document_stats.sort(key=lambda x: x['created_at'], reverse=True)
            
            return {
                'success': True,
                'documents': document_stats,
                'total_documents': len(document_stats)
            }
            
        except Exception as e:
            logger.error(f"Error getting user documents: {e}")
            return {
                'success': False,
                'error': f'Error retrieving documents: {str(e)}'
            }
    
    def get_document_chunks(self, user: User, document_id: str) -> List[KnowledgeBase]:
        """
        Get all chunks for a specific document.
        
        Args:
            user: User who owns the document
            document_id: Document ID
            
        Returns:
            List of KnowledgeBase chunks ordered by chunk_index
        """
        try:
            return KnowledgeBase.objects.filter(
                user=user,
                parent_document_id=document_id
            ).order_by('chunk_index')
        except Exception as e:
            logger.error(f"Error getting document chunks: {e}")
            return []
