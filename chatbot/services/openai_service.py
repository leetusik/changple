"""
OpenAI service for the chatbot application.
This module contains functionality for OpenAI API integration.
"""

# Import necessary libraries
# import openai
import os
from dotenv import load_dotenv

class OpenAIService:
    """
    Service for handling OpenAI API functionality.
    """
    def __init__(self, api_key=None):
        # Initialize OpenAI components
        self.api_key = api_key or self._get_api_key_from_settings()
    
    def _get_api_key_from_settings(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Try to get API key from environment variables
        api_key = os.environ.get("OPENAI_API_KEY")
        
        # If not found in environment, fallback to Django settings
        if not api_key:
            from django.conf import settings
            api_key = getattr(settings, "OPENAI_API_KEY", None)
            
        return api_key
    
    # Define your service methods here 