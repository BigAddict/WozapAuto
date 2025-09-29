"""
Example usage of environment variables in WozapAuto project.
This file demonstrates how to import and use environment variables anywhere in your project.
"""

# Method 1: Import the pre-configured variables
from base.env_config import EVOLUTION_API_KEY, EVOLUTION_HOST_URL

# Method 2: Import the utility functions
from base.env_config import get_env_variable, get_required_env_variable

def example_usage():
    """
    Example function showing how to use environment variables
    """
    
    # Using pre-configured variables
    print(f"Evolution API Key: {EVOLUTION_API_KEY}")
    print(f"Evolution Host URL: {EVOLUTION_HOST_URL}")
    
    # Using utility functions
    api_key = get_env_variable('EVOLUTION_API_KEY')
    host_url = get_required_env_variable('EVOLUTION_HOST_URL')
    
    # Example: Making an API call
    if EVOLUTION_API_KEY and EVOLUTION_HOST_URL:
        print("Environment variables are loaded successfully!")
        # You can now use these variables in your API calls
        # response = requests.get(f"{EVOLUTION_HOST_URL}/api/endpoint", 
        #                       headers={"Authorization": f"Bearer {EVOLUTION_API_KEY}"})
    else:
        print("Warning: Environment variables not found!")

if __name__ == "__main__":
    example_usage()
