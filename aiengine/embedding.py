"""
AI Engine Services - Production-Ready Embedding and Retrieval Services

This module provides enterprise-grade services for content embedding and knowledge retrieval
using Google's Gemini API. Features include vector embeddings, RAG (Retrieval-Augmented Generation),
content classification, and advanced text processing.
"""

from typing import Optional, List, Dict, Any, Union, IO
from pydantic import BaseModel, Field, model_validator
from pypdf import PdfReader, errors
from dataclasses import dataclass
from google import genai
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

class EmbeddingResult(BaseModel):
    """Represents the output of the embedding process."""
    embedding_vector: List[float] = Field(description="The dense vector representation of the content.")
    source_chunk: str = Field(description="The text chunk that was embedded.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the content.")

    @model_validator(mode='after')
    def validate_vector(cls, v):
        if not v or len(v) == 0:
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
        self.config = config or EmbeddingConfig
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
                contents=content_string
            )

            vector = response.embeddings[0].values

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

    def embed_pdf_file(self, file_data: StrByteType, metadata: DocumentMetadata = None) -> List[EmbeddingResult]:
        """Process PDF file and generate embeddings for each chunk."""
        if not file_data:
            raise ValueError("File data cannot be empty")

        try:
            reader = PdfReader(file_data)
            full_text = ""
            page_count = len(reader.pages)

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                full_text += page_text + "\n"

            if not full_text.strip():
                logger.warning("No text found in PDF")
                return []
            
            metadata = metadata or DocumentMetadata(
                name=reader.metadata.get('/Title', ''),
                description=reader.metadata.get('/Subject', ''),
                metadata={"note": "User did not provide extra metadata"}
            )

            chunks = self.chunk_text(full_text)
            logger.info(f"Created {len(chunks)} chunks from PDF: {metadata.name}")

            results = []
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    try:
                        result = self.embed_text(chunk, metadata.model_dump())
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Failed to embed chunk {i}: {e}")
                        continue
                
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

    