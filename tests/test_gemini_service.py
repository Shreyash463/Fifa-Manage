"""Unit tests for the Gemini wrapper service of FanPath AI."""

import os
import unittest
from unittest.mock import patch, MagicMock
import pytest
import config
import gemini_service

@pytest.fixture(autouse=True)
def run_before_each_test():
    """Resets the Gemini service caches before each test."""
    gemini_service.reset_caches()

def test_language_detection():
    """Verifies that primary languages (English, Spanish, Hindi) are correctly detected."""
    assert gemini_service.detect_language("Where is Gate A?") == "en"
    assert gemini_service.detect_language("Hola! ¿Cómo estás?") == "es"
    assert gemini_service.detect_language("नमस्ते! स्टेशन कहाँ है?") == "hi"

def test_static_shortcircuits():
    """Verifies that simple navigational inputs bypass API calls with predefined strings."""
    # English
    assert "Gate A" in gemini_service.get_static_shortcircuit("Where is Gate A?")
    assert "NJ Transit" in gemini_service.get_static_shortcircuit("How do I get there by train?")
    assert "green bins" in gemini_service.get_static_shortcircuit("Tell me about sustainability.")
    
    # Spanish
    assert "Puerta A" in gemini_service.get_static_shortcircuit("¿dónde está la puerta a?")
    
    # Hindi
    assert "एनजे ट्रांजिट" in gemini_service.get_static_shortcircuit("स्टेडियम के लिए ट्रेन")

@patch('gemini_service.genai.Client')
def test_gemini_caching_and_api_call(mock_client_class):
    """Verifies that identical queries are retrieved from the 5-min cache rather than hitting the API."""
    # Set up mock API response
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = "Mocked Gemini Response Text"
    mock_client.models.generate_content.return_value = mock_response
    
    # Configure API key presence
    config.GEMINI_API_KEY = "dummy_key"
    
    # First call: hits the mock API
    reply_1 = gemini_service.call_gemini("Tell me about section 100", [])
    assert reply_1 == "Mocked Gemini Response Text"
    assert mock_client.models.generate_content.call_count == 1
    
    # Second call (identical): hits the cache
    reply_2 = gemini_service.call_gemini("Tell me about section 100", [])
    assert reply_2 == "Mocked Gemini Response Text"
    # Call count should STILL be 1 (bypassed GenAI client call)
    assert mock_client.models.generate_content.call_count == 1

def test_api_missing_key_fallback():
    """Verifies fallback message is served when GEMINI_API_KEY is missing."""
    config.GEMINI_API_KEY = ""
    
    # Use a query that does NOT trigger a static shortcircuit to test the API key check fallback
    reply = gemini_service.call_gemini("Tell me something random about section 100", [])
    assert "Demo Mode" in reply
