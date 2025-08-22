from typing import Any, Optional, Type
from pathlib import Path
from pydantic import BaseModel, Field
import os

from .base import BaseTool, ToolConfig


class FileReadInput(BaseModel):
    """Input for file read tool"""
    file_path: str = Field(..., description="Path to the file to read")
    encoding: str = Field(default="utf-8", description="File encoding")


class FileWriteInput(BaseModel):
    """Input for file write tool"""
    file_path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")
    mode: str = Field(default="w", description="Write mode: 'w' for write, 'a' for append")
    encoding: str = Field(default="utf-8", description="File encoding")


class FileReadTool(BaseTool):
    """Tool for reading files"""
    
    name: str = "file_read"
    description: str = "Read content from a file. Provide the file path."
    args_schema: Type[BaseModel] = FileReadInput
    
    def __init__(self, config: Optional[ToolConfig] = None, base_dir: Optional[str] = None):
        if not config:
            config = ToolConfig(
                name=self.name,
                description=self.description
            )
        super().__init__(config)
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
    
    def execute(self, file_path: str, encoding: str = "utf-8") -> Any:
        """Read file content"""
        try:
            # Resolve path
            path = Path(file_path)
            if not path.is_absolute():
                path = self.base_dir / path
            
            # Security check - ensure path is within base directory
            try:
                path.resolve().relative_to(self.base_dir.resolve())
            except ValueError:
                return f"Error: Access denied - file path is outside allowed directory"
            
            # Check if file exists
            if not path.exists():
                return f"Error: File not found - {file_path}"
            
            if not path.is_file():
                return f"Error: Path is not a file - {file_path}"
            
            # Read file
            try:
                content = path.read_text(encoding=encoding)
                return f"Content of {file_path}:\n\n{content}"
            except Exception as e:
                return f"Error reading file: {str(e)}"
                
        except Exception as e:
            self.logger.error("File read error", error=str(e))
            return f"Error: {str(e)}"


class FileWriteTool(BaseTool):
    """Tool for writing files"""
    
    name: str = "file_write"
    description: str = "Write content to a file. Provide the file path and content."
    args_schema: Type[BaseModel] = FileWriteInput
    
    def __init__(self, config: Optional[ToolConfig] = None, base_dir: Optional[str] = None):
        if not config:
            config = ToolConfig(
                name=self.name,
                description=self.description
            )
        super().__init__(config)
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
    
    def execute(self, file_path: str, content: str, mode: str = "w", encoding: str = "utf-8") -> Any:
        """Write content to file"""
        try:
            # Validate mode
            if mode not in ["w", "a"]:
                return "Error: Invalid mode. Use 'w' for write or 'a' for append"
            
            # Resolve path
            path = Path(file_path)
            if not path.is_absolute():
                path = self.base_dir / path
            
            # Security check - ensure path is within base directory
            try:
                path.resolve().relative_to(self.base_dir.resolve())
            except ValueError:
                return f"Error: Access denied - file path is outside allowed directory"
            
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            try:
                if mode == "w":
                    path.write_text(content, encoding=encoding)
                    return f"Successfully wrote {len(content)} characters to {file_path}"
                else:  # append mode
                    with open(path, "a", encoding=encoding) as f:
                        f.write(content)
                    return f"Successfully appended {len(content)} characters to {file_path}"
            except Exception as e:
                return f"Error writing file: {str(e)}"
                
        except Exception as e:
            self.logger.error("File write error", error=str(e))
            return f"Error: {str(e)}"