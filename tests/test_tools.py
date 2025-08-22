import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json

from src.tools import ToolConfig
from src.tools import CalculatorTool, WebSearchTool, FileReadTool, FileWriteTool, APICallerTool


class TestCalculatorTool:
    """Test CalculatorTool"""
    
    def test_simple_calculation(self):
        tool = CalculatorTool()
        result = tool.execute("2 + 2")
        assert "2 + 2 = 4" in result
    
    def test_complex_calculation(self):
        tool = CalculatorTool()
        result = tool.execute("sqrt(16) + pow(2, 3)")
        assert "sqrt(16) + pow(2, 3) = 12.0" in result
    
    def test_math_functions(self):
        tool = CalculatorTool()
        
        # Test various math functions
        assert "pi" in tool.execute("pi")
        assert "2.718" in tool.execute("e")  # Euler's number
        assert "1.0" in tool.execute("sin(pi/2)")
        assert "0.0" in tool.execute("cos(pi/2)")
    
    def test_division_by_zero(self):
        tool = CalculatorTool()
        result = tool.execute("1/0")
        assert "Division by zero" in result
    
    def test_invalid_expression(self):
        tool = CalculatorTool()
        result = tool.execute("2 +")
        assert "Error" in result
    
    def test_unsafe_expression(self):
        tool = CalculatorTool()
        
        # Test dangerous patterns
        dangerous_inputs = [
            "__import__('os')",
            "exec('print(1)')",
            "eval('2+2')",
            "open('/etc/passwd')"
        ]
        
        for dangerous_input in dangerous_inputs:
            result = tool.execute(dangerous_input)
            assert "Unsafe expression" in result or "Error" in result


class TestWebSearchTool:
    """Test WebSearchTool"""
    
    def test_search_execution(self):
        tool = WebSearchTool()
        result = tool.execute("Python programming", max_results=3)
        
        assert "Result 1 for: Python programming" in result
        assert "https://example.com/result1" in result
        assert "snippet" in result.lower()
    
    @pytest.mark.asyncio
    async def test_async_search(self):
        tool = WebSearchTool()
        result = await tool.aexecute("AI agents", max_results=2)
        
        assert "Result 1 for: AI agents" in result
        assert "Result 2 for: AI agents" in result


class TestFileOperations:
    """Test file operation tools"""
    
    def test_file_read_success(self, temp_dir):
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")
        
        tool = FileReadTool(base_dir=str(temp_dir))
        result = tool.execute("test.txt")
        
        assert "Hello, World!" in result
        assert "Content of test.txt" in result
    
    def test_file_read_not_found(self, temp_dir):
        tool = FileReadTool(base_dir=str(temp_dir))
        result = tool.execute("nonexistent.txt")
        
        assert "File not found" in result
    
    def test_file_read_outside_base_dir(self, temp_dir):
        tool = FileReadTool(base_dir=str(temp_dir))
        result = tool.execute("../../../etc/passwd")
        
        assert "Access denied" in result
    
    def test_file_write_success(self, temp_dir):
        tool = FileWriteTool(base_dir=str(temp_dir))
        result = tool.execute("output.txt", "Test content")
        
        assert "Successfully wrote" in result
        assert "12 characters" in result
        
        # Verify file was created
        output_file = temp_dir / "output.txt"
        assert output_file.exists()
        assert output_file.read_text() == "Test content"
    
    def test_file_write_append(self, temp_dir):
        # Create initial file
        test_file = temp_dir / "append.txt"
        test_file.write_text("Initial content\n")
        
        tool = FileWriteTool(base_dir=str(temp_dir))
        result = tool.execute("append.txt", "Appended content", mode="a")
        
        assert "Successfully appended" in result
        assert test_file.read_text() == "Initial content\nAppended content"
    
    def test_file_write_invalid_mode(self, temp_dir):
        tool = FileWriteTool(base_dir=str(temp_dir))
        result = tool.execute("test.txt", "content", mode="x")
        
        assert "Invalid mode" in result


class TestAPICallerTool:
    """Test APICallerTool"""
    
    @patch('httpx.Client')
    def test_api_get_request(self, mock_client_class):
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://api.example.com/data"
        mock_response.json.return_value = {"key": "value"}
        
        # Mock client
        mock_client = Mock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        tool = APICallerTool()
        result = tool.execute("https://api.example.com/data")
        
        # Parse result
        result_data = json.loads(result)
        assert result_data["status_code"] == 200
        assert result_data["json"]["key"] == "value"
    
    @patch('httpx.Client')
    def test_api_post_request(self, mock_client_class):
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://api.example.com/create"
        mock_response.json.return_value = {"id": 123, "created": True}
        
        # Mock client
        mock_client = Mock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        tool = APICallerTool()
        result = tool.execute(
            "https://api.example.com/create",
            method="POST",
            data={"name": "test"}
        )
        
        result_data = json.loads(result)
        assert result_data["status_code"] == 201
        assert result_data["json"]["created"] is True
    
    def test_invalid_method(self):
        tool = APICallerTool()
        result = tool.execute("https://api.example.com", method="INVALID")
        
        assert "Invalid HTTP method" in result
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_async_api_call(self, mock_client_class):
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "https://api.example.com/async"
        mock_response.json.return_value = {"async": True}
        
        # Mock client
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        tool = APICallerTool()
        result = await tool.aexecute("https://api.example.com/async")
        
        result_data = json.loads(result)
        assert result_data["status_code"] == 200
        assert result_data["json"]["async"] is True