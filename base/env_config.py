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

# Add more environment variables as needed
# Example:
# DATABASE_URL = os.getenv('DATABASE_URL')
# EMAIL_HOST = os.getenv('EMAIL_HOST')
# EMAIL_PORT = os.getenv('EMAIL_PORT', '587')

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
