"""
AI Engine Services - Production-Ready Embedding and Retrieval Services

This module provides enterprise-grade services for content embedding and knowledge retrieval
using Google's Gemini API. Features include vector embeddings, RAG (Retrieval-Augmented Generation),
content classification, and advanced text processing.
"""

from typing import Optional, List, Dict, Any, Union, IO
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader, errors
from dataclasses import dataclass
from google import genai
from google.genai import types
import numpy as np
import logging

from aiengine.models import DocumentMetadata
from base.env_config import GEMINI_API_KEY

StreamType = IO[Any]
StrByteType = Union[str, StreamType]

logger = logging.getLogger('aiengine.embedding')

@dataclass
class EmbeddingConfig:
    """Configuration for embedding services."""
    model: str = 'gemini-embedding-001'
    max_chunk_size: int = 2000
    chunk_overlap: int = 200
    batch_size: int = 10
    retry_attempts: int = 3
    timeout: int = 30
    # Gemini embedding tuning
    output_dimensionality: int = 1536  # Align with DB VectorField(dimensions=1536)
    task_type: str = "RETRIEVAL_DOCUMENT"  # Optimize for document storage
    normalize: bool = True  # Normalize vectors when dim != 3072

class EmbeddingResult(BaseModel):
    """Represents the output of the embedding process."""
    embedding_vector: List[float] = Field(description="The dense vector representation of the content.")
    source_chunk: str = Field(description="The text chunk that was embedded.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the content.")

    @field_validator('embedding_vector')
    @classmethod
    def validate_vector(cls, v: List[float]):
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("Embedding vector cannot be empty")
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("All vector elements must be numbers")
        return v

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
    EMBEDDING_CONFIG = EmbeddingConfig()

    def __init__(self, config: EmbeddingConfig = None):
        """Initialize the embedding service."""
        self.config = config or EmbeddingConfig()
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = self.config.model

        logger.info(f"EmbeddingService initialized with model: {self.model}")

    def embed_text(self, content_string: str, metadata: Dict[str, Any] = None) -> EmbeddingResult:
        """
        Generate an embedding vector for text content.

        Args:
            content_string: The text content to embed
            metadata: Optional metadata about the content

        Returns:
            EmbeddingResult: The embedding vector
        """
        if not content_string or not content_string.strip():
            raise ValueError("Content string cannot be empty")

        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=content_string,
                config=types.EmbedContentConfig(
                    output_dimensionality=self.config.output_dimensionality,
                    task_type=self.config.task_type,
                ),
            )

            vector = response.embeddings[0].values

            # Normalize when using non-3072 dims (recommended by Gemini docs)
            if self.config.normalize and self.config.output_dimensionality != 3072:
                vec_np = np.asarray(vector, dtype=float)
                norm = np.linalg.norm(vec_np)
                if norm > 0:
                    vector = (vec_np / norm).tolist()

            logger.info(f"Generated embedding for content: {len(content_string)} chars, vector dim: {len(vector)}")

            return EmbeddingResult(
                embedding_vector=vector,
                source_chunk=content_string,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Gemini API embedding failed: {e}")
        
    def embed_texts_batch(self, texts: List[str], metadata_list: List[Dict[str, Any]] = None) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts efficiently using Gemini batch embedding."""
        if not texts:
            return []

        metadata_list = metadata_list or [{}] * len(texts)

        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=texts,
                config=types.EmbedContentConfig(
                    output_dimensionality=self.config.output_dimensionality,
                    task_type=self.config.task_type,
                ),
            )

            embeddings = []
            for idx, emb in enumerate(response.embeddings):
                vector = emb.values
                if self.config.normalize and self.config.output_dimensionality != 3072:
                    vec_np = np.asarray(vector, dtype=float)
                    norm = np.linalg.norm(vec_np)
                    if norm > 0:
                        vector = (vec_np / norm).tolist()
                embeddings.append(
                    EmbeddingResult(
                        embedding_vector=vector,
                        source_chunk=texts[idx],
                        metadata=metadata_list[idx] if idx < len(metadata_list) else {},
                    )
                )
            return embeddings
        except Exception as e:
            logger.error(f"Batch embed_content failed, falling back to per-text embedding: {e}")
            # Fallback to per-text embedding
            results: List[EmbeddingResult] = []
            for text, meta in zip(texts, metadata_list):
                try:
                    results.append(self.embed_text(text, meta))
                except Exception as inner_e:
                    logger.error(f"Failed to embed text in fallback: {inner_e}")
                    continue
            return results

    def embed_pdf_file(self, file_data: StrByteType, metadata: DocumentMetadata = None) -> List[EmbeddingResult]:
        """Process PDF file and generate embeddings for each chunk."""
        if not file_data:
            raise ValueError("File data cannot be empty")

        try:
            reader = PdfReader(file_data)
            full_text = ""
            page_count = len(reader.pages)

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"

            if not full_text.strip():
                logger.warning("No text found in PDF")
                return []
            
            doc_meta = getattr(reader, 'metadata', {}) or {}
            metadata = metadata or DocumentMetadata(
                name=(doc_meta.get('/Title', '') if isinstance(doc_meta, dict) else ''),
                description=(doc_meta.get('/Subject', '') if isinstance(doc_meta, dict) else ''),
                metadata={"note": "User did not provide extra metadata"}
            )

            chunks = self.chunk_text(full_text)
            logger.info(f"Created {len(chunks)} chunks from PDF: {metadata.name}")

            # Batch embed chunks for performance
            chunk_texts = [c for c in chunks if c.strip()]
            meta_list = [metadata.model_dump()] * len(chunk_texts)
            results = self.embed_texts_batch(chunk_texts, meta_list)
                
            logger.info(f"Successfully generated {len(results)} embeddings from PDF: {metadata.name}")
            return results

        except errors.PdfReadError as e:
            raise ValueError(f"Invalid or encrypted PDF: {e}")
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise RuntimeError(f"PDF processing failed: {e}")

    def chunk_text(self, text: str) -> List[str]:
        """Intelligently chunk text with overlap."""
        max_size = self.config.max_chunk_size
        overlap = self.config.chunk_overlap
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

    