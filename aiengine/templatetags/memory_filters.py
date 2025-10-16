"""
Custom template filters for memory management.
"""
from django import template
import numpy as np

register = template.Library()

@register.filter
def has_embedding(value):
    """
    Check if a message has an embedding.
    """
    if value is None:
        return False
    
    # Handle numpy arrays
    if isinstance(value, np.ndarray):
        return len(value) > 0
    
    # Handle lists
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    
    # Handle other types
    return bool(value)

@register.filter
def embedding_length(value):
    """
    Get the length of an embedding.
    """
    if value is None:
        return 0
    
    # Handle numpy arrays
    if isinstance(value, np.ndarray):
        return len(value)
    
    # Handle lists
    if isinstance(value, (list, tuple)):
        return len(value)
    
    return 0
