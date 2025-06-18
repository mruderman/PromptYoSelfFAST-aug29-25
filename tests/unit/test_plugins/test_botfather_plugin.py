"""
Unit tests for BotFather plugin.
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the plugins directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "mcp" / "plugins" / "botfather"))

from cli import click_button, send_message


class TestBotFatherPlugin:
    """Test cases for BotFather plugin."""
    
    def test_click_button_success(self):
        """Test successful button click."""
        args = {
            "button-text": "Payments",
            "msg-id": 12345678
        }
        
        result = click_button(args)
        
        assert "result" in result
        assert "Clicked button Payments on message 12345678" in result["result"]
    
    def test_click_button_missing_button_text(self):
        """Test button click with missing button text."""
        args = {
            "msg-id": 12345678
        }
        
        result = click_button(args)
        
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        assert "button-text" in result["error"]
    
    def test_click_button_missing_msg_id(self):
        """Test button click with missing message ID."""
        args = {
            "button-text": "Payments"
        }
        
        result = click_button(args)
        
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        assert "msg-id" in result["error"]
    
    def test_click_button_missing_both_args(self):
        """Test button click with missing both arguments."""
        args = {}
        
        result = click_button(args)
        
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        assert "button-text" in result["error"]
        assert "msg-id" in result["error"]
    
    def test_send_message_success(self):
        """Test successful message sending."""
        args = {
            "message": "/newbot"
        }
        
        result = send_message(args)
        
        assert "result" in result
        assert "Sent message: /newbot" in result["result"]
    
    def test_send_message_missing_message(self):
        """Test message sending with missing message."""
        args = {}
        
        result = send_message(args)
        
        assert "error" in result
        assert "Missing required argument: message" in result["error"]
    
    def test_send_message_empty_message(self):
        """Test message sending with empty message."""
        args = {
            "message": ""
        }
        
        result = send_message(args)
        
        assert "result" in result
        assert "Sent message: " in result["result"]
    
    def test_send_message_special_characters(self):
        """Test message sending with special characters."""
        args = {
            "message": "Hello @world! #test"
        }
        
        result = send_message(args)
        
        assert "result" in result
        assert "Sent message: Hello @world! #test" in result["result"]
    
    def test_click_button_with_special_characters(self):
        """Test button click with special characters in button text."""
        args = {
            "button-text": "Pay & Save",
            "msg-id": 12345678
        }
        
        result = click_button(args)
        
        assert "result" in result
        assert "Clicked button Pay & Save on message 12345678" in result["result"]
    
    def test_click_button_large_msg_id(self):
        """Test button click with large message ID."""
        args = {
            "button-text": "Test",
            "msg-id": 999999999999
        }
        
        result = click_button(args)
        
        assert "result" in result
        assert "Clicked button Test on message 999999999999" in result["result"] 