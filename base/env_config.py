"""
Environment configuration utility for WozapAuto project.
Import this module anywhere in your Django project to access environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Evolution API Configuration
EVOLUTION_API_KEY = os.getenv('EVOLUTION_API_KEY')
EVOLUTION_HOST_URL = os.getenv('EVOLUTION_HOST_URL')

# Django Configuration
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# SMTP Email Configuration
SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL')
SMTP_FROM_NAME = os.getenv('SMTP_FROM_NAME')
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_PORT = os.getenv('SMTP_PORT', '587')
SMTP_USERNAME = os.getenv('SMTP_USERNAME')

DATABASE_URL = os.getenv('DATABASE_URL')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def get_env_variable(var_name, default=None):
    """
    Get an environment variable with optional default value.
    
    Args:
        var_name (str): Name of the environment variable
        default: Default value if variable is not found
    
    Returns:
        str: Environment variable value or default
    """
    return os.getenv(var_name, default)

def get_required_env_variable(var_name):
    """
    Get a required environment variable. Raises error if not found.
    
    Args:
        var_name (str): Name of the environment variable
    
    Returns:
        str: Environment variable value
    
    Raises:
        ValueError: If environment variable is not found
    """
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Required environment variable '{var_name}' is not set")
    return value
