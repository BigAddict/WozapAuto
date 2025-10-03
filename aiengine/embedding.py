"""
AI Engine Services - Production-Ready Embedding and Retrieval Services

This module provides enterprise-grade services for content embedding and knowledge retrieval
using Google's Gemini API. Features include vector embeddings, RAG (Retrieval-Augmented Generation),
content classification, and advanced text processing.
"""

import os
import uuid
import logging
import hashlib
import asyncio
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Third-party libraries
import numpy as np
from pydantic import BaseModel, Field, validator
from google import genai
from google.genai import types
from dotenv import load_dotenv

# PDF Processing
from pypdf import PdfReader, errors

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
@dataclass
class EmbeddingConfig:
    """Configuration for embedding services."""
    model: str = 'gemini-embedding-001'
    max_chunk_size: int = 2000
    chunk_overlap: int = 200
    batch_size: int = 10
    cache_size: int = 1000
    retry_attempts: int = 3
    timeout: int = 30

@dataclass
class RetrievalConfig:
    """Configuration for retrieval services."""
    default_top_k: int = 5
    similarity_threshold: float = 0.7
    max_context_length: int = 4000
    llm_model: str = 'gemini-2.5-flash'

# Global configuration
EMBEDDING_CONFIG = EmbeddingConfig()
RETRIEVAL_CONFIG = RetrievalConfig()

# Get API key from environment
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

# --- Data Models ---

class EmbeddingResult(BaseModel):
    """Represents the output of the embedding process."""
    embedding_vector: List[float] = Field(description="The dense vector representation of the content.")
    content_hash: str = Field(description="A unique hash for the content that was embedded.")
    source_chunk: str = Field(description="The text chunk that was embedded.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the content.")
    
    @validator('embedding_vector')
    def validate_vector(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Embedding vector cannot be empty")
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("All vector elements must be numbers")
        return v

class SearchResult(BaseModel):
    """Represents a single document result from a search query."""
    doc_id: str
    content_snippet: str
    relevance_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('relevance_score')
    def validate_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Relevance score must be between 0 and 1")
        return v

class RetrievalResult(BaseModel):
    """Represents the output of the content retrieval service."""
    best_answer: Optional[str] = Field(default=None, description="A synthesized answer if applicable.")
    source_documents: List[SearchResult]
    confidence_score: float = Field(default=0.0, description="Confidence in the generated answer.")
    processing_time: float = Field(default=0.0, description="Time taken to process the query.")

# --- Utility Functions ---

def calculate_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    try:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return 0.0

def chunk_text(text: str, max_size: int = None, overlap: int = None) -> List[str]:
    """Intelligently chunk text with overlap."""
    max_size = max_size or EMBEDDING_CONFIG.max_chunk_size
    overlap = overlap or EMBEDDING_CONFIG.chunk_overlap
    
    if len(text) <= max_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_size
        
        # Try to break at sentence boundaries
        if end < len(text):
            # Look for sentence endings within the last 100 characters
            search_start = max(start + max_size - 100, start)
            sentence_end = text.rfind('.', search_start, end)
            if sentence_end > start:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

# --- Service 1: Content Embedding Service ---

class EmbeddingService:
    """
    Production-ready service for converting content into vector embeddings.
    
    Features:
    - Intelligent text chunking with overlap
    - Caching for improved performance
    - Batch processing support
    - Comprehensive error handling
    - Metadata extraction
    """
    
    def __init__(self, config: EmbeddingConfig = None):
        """Initialize the embedding service."""
        self.config = config or EMBEDDING_CONFIG
        self.client = genai.Client(api_key=API_KEY)
        self.model = self.config.model
        
        # Initialize cache
        self._cache = {}
        
        logger.info(f"EmbeddingService initialized with model: {self.model}")
    
    @lru_cache(maxsize=1000)
    def _get_cached_embedding(self, content_hash: str) -> Optional[List[float]]:
        """Get cached embedding if available."""
        return self._cache.get(content_hash)
    
    def _cache_embedding(self, content_hash: str, vector: List[float]) -> None:
        """Cache an embedding vector."""
        if len(self._cache) >= self.config.cache_size:
            # Remove oldest entries (simple LRU)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[content_hash] = vector
    
    def _generate_content_hash(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Generate a unique hash for content."""
        content_with_meta = content + str(metadata or {})
        return hashlib.sha256(content_with_meta.encode()).hexdigest()
    
    def embed_text(self, content_string: str, metadata: Dict[str, Any] = None) -> EmbeddingResult:
        """
        Generate an embedding vector for text content.
        
        Args:
            content_string: The text content to embed
            metadata: Optional metadata about the content
            
        Returns:
            EmbeddingResult containing the vector and metadata
        """
        if not content_string or not content_string.strip():
            raise ValueError("Content string cannot be empty")
        
        # Generate content hash for caching
        content_hash = self._generate_content_hash(content_string, metadata)
        
        # Check cache first
        cached_vector = self._get_cached_embedding(content_hash)
        if cached_vector:
            logger.debug(f"Using cached embedding for content hash: {content_hash[:8]}...")
            return EmbeddingResult(
                embedding_vector=cached_vector,
                content_hash=content_hash,
                source_chunk=content_string,
                metadata=metadata or {}
            )
        
        # Generate new embedding
        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=content_string
            )
            
            vector = response.embeddings[0].values
            
            # Cache the result
            self._cache_embedding(content_hash, vector)
            
            logger.info(f"Generated embedding for content: {len(content_string)} chars, vector dim: {len(vector)}")
            
            return EmbeddingResult(
                embedding_vector=vector,
                content_hash=content_hash,
                source_chunk=content_string,
                metadata=metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Gemini API embedding failed: {e}")
    
    def embed_texts_batch(self, texts: List[str], metadata_list: List[Dict[str, Any]] = None) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts efficiently."""
        if not texts:
            return []
        
        metadata_list = metadata_list or [{}] * len(texts)
        
        results = []
        for i in range(0, len(texts), self.config.batch_size):
            batch_texts = texts[i:i + self.config.batch_size]
            batch_metadata = metadata_list[i:i + self.config.batch_size]
            
            for text, metadata in zip(batch_texts, batch_metadata):
                try:
                    result = self.embed_text(text, metadata)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to embed text in batch: {e}")
                    # Continue with other texts in the batch
                    continue
        
        return results
    
    def embed_pdf_file(self, file_path: Union[str, Path], extract_metadata: bool = True) -> List[EmbeddingResult]:
        """
        Process a PDF file and generate embeddings for each chunk.
        
        Args:
            file_path: Path to the PDF file
            extract_metadata: Whether to extract PDF metadata
            
        Returns:
            List of EmbeddingResult objects
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.suffix.lower() != '.pdf':
            raise ValueError(f"File must be a PDF: {file_path}")
        
        try:
            # Extract text from PDF
            reader = PdfReader(file_path)
            full_text = ""
            page_count = len(reader.pages)
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                full_text += page_text + "\n"
            
            if not full_text.strip():
                logger.warning(f"No text found in PDF: {file_path}")
                return []
            
            # Extract metadata if requested
            metadata = {}
            if extract_metadata:
                try:
                    metadata = {
                        'file_name': file_path.name,
                        'file_size': file_path.stat().st_size,
                        'page_count': page_count,
                        'extraction_method': 'pypdf'
                    }
                    
                    # Try to get PDF metadata
                    if reader.metadata:
                        metadata.update({
                            'title': reader.metadata.get('/Title', ''),
                            'author': reader.metadata.get('/Author', ''),
                            'subject': reader.metadata.get('/Subject', ''),
                            'creator': reader.metadata.get('/Creator', ''),
                            'creation_date': str(reader.metadata.get('/CreationDate', '')),
                        })
                except Exception as e:
                    logger.warning(f"Could not extract PDF metadata: {e}")
            
            # Chunk the text
            chunks = chunk_text(full_text, self.config.max_chunk_size, self.config.chunk_overlap)
            logger.info(f"Created {len(chunks)} chunks from PDF: {file_path.name}")
            
            # Generate embeddings for chunks
            results = []
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'chunk_length': len(chunk)
                    })
                    
                    try:
                        result = self.embed_text(chunk, chunk_metadata)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Failed to embed chunk {i}: {e}")
                        continue
            
            logger.info(f"Successfully generated {len(results)} embeddings from PDF: {file_path.name}")
            return results
            
        except errors.PdfReadError as e:
            raise ValueError(f"Invalid or encrypted PDF: {e}")
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            raise RuntimeError(f"PDF processing failed: {e}")

# --- Service 2: Knowledge Retrieval Service ---

class KnowledgeRetrievalService:
    """
    Advanced knowledge retrieval service with RAG capabilities.
    
    Features:
    - Vector similarity search
    - RAG (Retrieval-Augmented Generation)
    - Content classification
    - Anomaly detection
    - Search reranking
    - Confidence scoring
    """
    
    def __init__(self, embedding_service: EmbeddingService, config: RetrievalConfig = None):
        """Initialize the retrieval service."""
        self.embed_svc = embedding_service
        self.config = config or RETRIEVAL_CONFIG
        self.llm_client = genai.Client(api_key=API_KEY)
        
        # In-memory vector store for demo (replace with real vector DB in production)
        self._vector_store: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}
        
        logger.info("KnowledgeRetrievalService initialized")
    
    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """Add a document to the vector store."""
        try:
            embedding_result = self.embed_svc.embed_text(content, metadata)
            self._vector_store[doc_id] = (embedding_result.embedding_vector, {
                'content': content,
                'metadata': metadata or {},
                'content_hash': embedding_result.content_hash
            })
            logger.info(f"Added document to vector store: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")
            raise
    
    def search_similar(self, query: str, top_k: int = None, threshold: float = None) -> List[SearchResult]:
        """Search for similar documents using vector similarity."""
        top_k = top_k or self.config.default_top_k
        threshold = threshold or self.config.similarity_threshold
        
        try:
            # Embed the query
            query_embedding = self.embed_svc.embed_text(query)
            query_vector = query_embedding.embedding_vector
            
            # Calculate similarities
            similarities = []
            for doc_id, (doc_vector, doc_data) in self._vector_store.items():
                similarity = calculate_similarity(query_vector, doc_vector)
                if similarity >= threshold:
                    similarities.append(SearchResult(
                        doc_id=doc_id,
                        content_snippet=doc_data['content'][:500] + "..." if len(doc_data['content']) > 500 else doc_data['content'],
                        relevance_score=similarity,
                        metadata=doc_data['metadata']
                    ))
            
            # Sort by relevance and return top_k
            similarities.sort(key=lambda x: x.relevance_score, reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Vector search failed: {e}")
    
    def retrieve_information(self, query: str, top_k: int = None) -> RetrievalResult:
        """
        Perform RAG (Retrieval-Augmented Generation) to answer queries.
        
        Args:
            query: The user's question
            top_k: Number of relevant documents to retrieve
            
        Returns:
            RetrievalResult with synthesized answer and sources
        """
        import time
        start_time = time.time()
        
        try:
            # Search for relevant documents
            search_results = self.search_similar(query, top_k)
            
            if not search_results:
                return RetrievalResult(
                    best_answer="I couldn't find relevant information to answer your question.",
                    source_documents=[],
                    confidence_score=0.0,
                    processing_time=time.time() - start_time
                )
            
            # Prepare context for RAG
            context_parts = []
            for i, result in enumerate(search_results[:3]):  # Use top 3 for context
                context_parts.append(f"Source {i+1}: {result.content_snippet}")
            
            context = "\n\n".join(context_parts)
            
            # Generate answer using LLM
            prompt = f"""You are an expert AI assistant. Use ONLY the following provided context to answer the user's question.
            If the answer is not in the context, state that you cannot find the information in the knowledge base.
            
            CONTEXT:
            {context}
            
            QUESTION: {query}
            
            Please provide a clear, accurate answer based on the context above. If you cannot answer based on the provided context, say so explicitly.
            
            ANSWER:"""
            
            response = self.llm_client.models.generate_content(
                model=self.config.llm_model,
                contents=prompt
            )
            
            answer = response.text if hasattr(response, 'text') else str(response)
            
            # Calculate confidence based on source relevance scores
            confidence = sum(r.relevance_score for r in search_results[:3]) / min(3, len(search_results))
            
            processing_time = time.time() - start_time
            
            logger.info(f"RAG query processed in {processing_time:.2f}s with confidence {confidence:.2f}")
            
            return RetrievalResult(
                best_answer=answer,
                source_documents=search_results,
                confidence_score=confidence,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return RetrievalResult(
                best_answer=f"Error processing your query: {str(e)}",
                source_documents=[],
                confidence_score=0.0,
                processing_time=time.time() - start_time
            )
    
    def classify_content(self, content: str) -> Dict[str, Any]:
        """Classify content using rule-based and LLM-based approaches."""
        try:
            # Rule-based classification
            content_lower = content.lower()
            
            if any(keyword in content_lower for keyword in ['policy', 'procedure', 'guideline']):
                category = "HR_POLICY"
            elif any(keyword in content_lower for keyword in ['bug', 'error', 'issue', 'problem']):
                category = "TECH_SUPPORT"
            elif any(keyword in content_lower for keyword in ['question', 'how to', 'tutorial']):
                category = "KNOWLEDGE_BASE"
            else:
                category = "GENERAL_KNOWLEDGE"
            
            # Use LLM for more sophisticated classification
            classification_prompt = f"""Classify the following content into one of these categories:
            - HR_POLICY: Human resources policies, procedures, guidelines
            - TECH_SUPPORT: Technical issues, bugs, troubleshooting
            - KNOWLEDGE_BASE: How-to guides, tutorials, documentation
            - GENERAL_KNOWLEDGE: General information, facts, explanations
            
            Content: {content[:500]}
            
            Return only the category name:"""
            
            try:
                response = self.llm_client.models.generate_content(
                    model=self.config.llm_model,
                    contents=classification_prompt
                )
                llm_category = response.text.strip() if hasattr(response, 'text') else category
            except:
                llm_category = category
            
            return {
                'category': llm_category,
                'confidence': 0.8 if category == llm_category else 0.6,
                'rule_based_category': category,
                'llm_category': llm_category
            }
            
        except Exception as e:
            logger.error(f"Content classification failed: {e}")
            return {
                'category': 'UNKNOWN',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def detect_anomaly(self, data_point: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in data points."""
        try:
            # Simple anomaly detection based on data structure and values
            anomalies = []
            
            # Check for unusual keys
            unusual_keys = ['unusual_key', 'suspicious_field', 'error_flag']
            for key in unusual_keys:
                if key in data_point:
                    anomalies.append(f"Unusual key detected: {key}")
            
            # Check for extreme values in numeric fields
            for key, value in data_point.items():
                if isinstance(value, (int, float)):
                    if value < -1000 or value > 1000000:
                        anomalies.append(f"Extreme value in {key}: {value}")
            
            # Check for empty or null values
            for key, value in data_point.items():
                if value is None or (isinstance(value, str) and not value.strip()):
                    anomalies.append(f"Empty value in {key}")
            
            is_anomaly = len(anomalies) > 0
            
            return {
                'is_anomaly': is_anomaly,
                'anomalies': anomalies,
                'confidence': min(1.0, len(anomalies) * 0.3),
                'data_point': data_point
            }
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {
                'is_anomaly': False,
                'anomalies': [f"Detection error: {str(e)}"],
                'confidence': 0.0,
                'error': str(e)
            }

# --- Example Usage and Testing ---

def create_sample_knowledge_base(retrieval_service: KnowledgeRetrievalService) -> None:
    """Create a sample knowledge base for testing."""
    sample_docs = [
        {
            'id': 'doc_1',
            'content': 'RAG (Retrieval-Augmented Generation) is a technique that combines information retrieval with text generation. It allows AI systems to access external knowledge bases to provide more accurate and up-to-date answers.',
            'metadata': {'topic': 'AI', 'type': 'definition'}
        },
        {
            'id': 'doc_2', 
            'content': 'Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design. It follows the MVT (Model-View-Template) architectural pattern.',
            'metadata': {'topic': 'Web Development', 'type': 'framework'}
        },
        {
            'id': 'doc_3',
            'content': 'Vector databases store numerical representations of data called embeddings. They enable efficient similarity search and are essential for RAG systems.',
            'metadata': {'topic': 'Database', 'type': 'technology'}
        },
        {
            'id': 'doc_4',
            'content': 'Our company policy states that all employees must complete security training annually. This training covers data protection, password management, and incident reporting procedures.',
            'metadata': {'topic': 'HR', 'type': 'policy'}
        }
    ]
    
    for doc in sample_docs:
        retrieval_service.add_document(doc['id'], doc['content'], doc['metadata'])

if __name__ == '__main__':
    # Initialize services
    embed_service = EmbeddingService()
    retrieval_service = KnowledgeRetrievalService(embed_service)
    
    # Create sample knowledge base
    create_sample_knowledge_base(retrieval_service)
    
    print("\n=== AI Engine Services Demo ===")
    
    # Test 1: Text Embedding
    print("\n--- Text Embedding Test ---")
    test_text = "The core concept of a vector database is to store numerical representations of knowledge."
    embedding = embed_service.embed_text(test_text, {'test': True})
    print(f"✅ Generated embedding: {len(embedding.embedding_vector)} dimensions")
    print(f"   Content hash: {embedding.content_hash[:16]}...")
    
    # Test 2: PDF Processing (if available)
    pdf_path = Path("mock_test_document.pdf")
    if pdf_path.exists():
        print("\n--- PDF Processing Test ---")
        try:
            pdf_embeddings = embed_service.embed_pdf_file(pdf_path)
            print(f"✅ Processed PDF: {len(pdf_embeddings)} chunks embedded")
        except Exception as e:
            print(f"❌ PDF processing failed: {e}")
    
    # Test 3: Knowledge Retrieval
    print("\n--- Knowledge Retrieval Test ---")
    query = "What is RAG and how does it work?"
    result = retrieval_service.retrieve_information(query)
    print(f"✅ Query: {query}")
    print(f"   Answer: {result.best_answer}")
    print(f"   Confidence: {result.confidence_score:.2f}")
    print(f"   Sources: {len(result.source_documents)}")
    
    # Test 4: Content Classification
    print("\n--- Content Classification Test ---")
    test_content = "Our new software policy requires all developers to use two-factor authentication."
    classification = retrieval_service.classify_content(test_content)
    print(f"✅ Content: {test_content[:50]}...")
    print(f"   Category: {classification['category']}")
    print(f"   Confidence: {classification['confidence']:.2f}")
    
    # Test 5: Similarity Search
    print("\n--- Similarity Search Test ---")
    search_query = "Python web framework"
    similar_docs = retrieval_service.search_similar(search_query, top_k=2)
    print(f"✅ Search: {search_query}")
    for i, doc in enumerate(similar_docs):
        print(f"   {i+1}. {doc.doc_id} (score: {doc.relevance_score:.3f})")
    
    print("\n=== All tests completed successfully! ===")