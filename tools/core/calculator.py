"""Calculator tool with structured results and validation."""

from langchain_core.tools import tool
from typing import Literal, Union
from tools.core.base_tool import ToolResult, log_tool_call
from tools.schemas import CalculatorInput


@log_tool_call("calculator")
@tool
def calculator(
    operation: Literal["add", "subtract", "multiply", "divide"],
    a: Union[int, float],
    b: Union[int, float],
) -> str:
    """Define a two-input calculator tool that returns precise answers.

    This tool performs basic mathematical operations with validation.
    Returns structured results with success/error information.

    Args:
        operation: The operation to perform ('add', 'subtract', 'multiply', 'divide')
        a: The first number (int or float)
        b: The second number (int or float)
        
    Returns:
        String representation of ToolResult with calculation result or error message

    Example:
        calculator("add", 5, 3) -> "8"
        calculator("divide", 10, 0) -> "Error: Division by zero is not allowed"
    """
    try:
        # Validate input using Pydantic schema
        input_data = CalculatorInput(operation=operation, a=a, b=b)
        
        # Perform calculation
        if input_data.operation == 'add':
            result = input_data.a + input_data.b
        elif input_data.operation == 'subtract':
            result = input_data.a - input_data.b
        elif input_data.operation == 'multiply':
            result = input_data.a * input_data.b
        elif input_data.operation == 'divide':
            result = input_data.a / input_data.b
        else:
            return ToolResult(
                success=False,
                error=f"Unknown operation: {operation}"
            ).to_string()
        
        # Return structured result
        return ToolResult(
            success=True,
            data={"result": result, "operation": operation, "a": a, "b": b},
            metadata={"operation_type": operation}
        ).to_string()
        
    except ValueError as e:
        # Validation errors (e.g., division by zero)
        return ToolResult(success=False, error=str(e)).to_string()
    except Exception as e:
        # Unexpected errors
        return ToolResult(
            success=False,
            error=f"Calculation failed: {str(e)}"
        ).to_string()