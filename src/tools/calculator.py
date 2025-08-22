from typing import Any, Optional, Type
from pydantic import BaseModel, Field
import math
import re

from .base import BaseTool, ToolConfig


class CalculatorInput(BaseModel):
    """Input for the calculator tool"""
    expression: str = Field(..., description="Mathematical expression to evaluate")


class CalculatorTool(BaseTool):
    """A tool for performing mathematical calculations"""
    
    name: str = "calculator"
    description: str = "Perform mathematical calculations. Input should be a valid mathematical expression."
    args_schema: Type[BaseModel] = CalculatorInput
    
    def __init__(self, config: Optional[ToolConfig] = None):
        if not config:
            config = ToolConfig(
                name=self.name,
                description=self.description
            )
        super().__init__(config)
        
        # Define safe functions for evaluation
        self.safe_dict = {
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
            'sum': sum,
            'pow': pow,
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'log10': math.log10,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e,
        }
    
    def execute(self, expression: str) -> Any:
        """Execute mathematical calculation"""
        try:
            # Clean expression
            expression = expression.strip()
            
            # Basic validation
            if not expression:
                return "Error: Empty expression"
            
            # Check for dangerous patterns
            dangerous_patterns = [
                r'__', r'import', r'exec', r'eval', r'open',
                r'file', r'input', r'raw_input', r'compile'
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, expression, re.IGNORECASE):
                    return f"Error: Unsafe expression pattern detected: {pattern}"
            
            # Evaluate expression
            try:
                result = eval(expression, {"__builtins__": {}}, self.safe_dict)
                return f"{expression} = {result}"
            except ZeroDivisionError:
                return "Error: Division by zero"
            except ValueError as e:
                return f"Error: Math domain error - {str(e)}"
            except Exception as e:
                return f"Error: Invalid expression - {str(e)}"
                
        except Exception as e:
            self.logger.error("Calculator error", error=str(e))
            return f"Error: {str(e)}"