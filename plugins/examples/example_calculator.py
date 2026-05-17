"""
Example Plugin: Advanced Calculator
====================================
Demonstrates how to create a plugin for A.N.A. v15.0

This plugin provides advanced mathematical operations.
"""

import math
import ast
import operator
from typing import Dict, Any


# Safe mathematical expression evaluator (replaces dangerous eval)
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
}


def _safe_math_eval(expression: str) -> float:
    """
    Safely evaluate mathematical expressions WITHOUT using eval().
    Only allows basic math operations: +, -, *, /, **, %
    """
    try:
        node = ast.parse(expression, mode='eval')
        return _eval_node(node.body)
    except Exception as e:
        raise ValueError(f"Invalid mathematical expression: {e}")


def _eval_node(node):
    """Recursively evaluate AST node for safe math."""
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants allowed")
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op_type = type(node.op)
        if op_type in _ALLOWED_OPERATORS:
            return _ALLOWED_OPERATORS[op_type](left, right)
        raise ValueError(f"Operator not allowed: {op_type}")
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        op_type = type(node.op)
        if op_type in _ALLOWED_OPERATORS:
            return _ALLOWED_OPERATORS[op_type](operand)
        raise ValueError(f"Unary operator not allowed: {op_type}")
    else:
        raise ValueError(f"Expression not allowed: {type(node)}")


def calculate_advanced(expression: str, operation: str = "eval") -> Dict[str, Any]:
    """
    Perform advanced mathematical calculations.
    
    Args:
        expression: Mathematical expression or values
        operation: Type of operation (eval, sqrt, factorial, sin, cos, tan)
    
    Returns:
        Dict with result and metadata
    """
    try:
        if operation == "eval":
            # SAFE mathematical expression parser (no eval)
            result = _safe_math_eval(expression)
        elif operation == "sqrt":
            result = math.sqrt(float(expression))
        elif operation == "factorial":
            result = math.factorial(int(expression))
        elif operation == "sin":
            result = math.sin(math.radians(float(expression)))
        elif operation == "cos":
            result = math.cos(math.radians(float(expression)))
        elif operation == "tan":
            result = math.tan(math.radians(float(expression)))
        else:
            return {"error": f"Unknown operation: {operation}"}
        
        return {
            "success": True,
            "result": result,
            "operation": operation,
            "expression": expression
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operation": operation,
            "expression": expression
        }


def get_math_constants() -> Dict[str, float]:
    """
    Return commonly used mathematical constants.
    
    Returns:
        Dict of constant names and values
    """
    return {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "golden_ratio": (1 + math.sqrt(5)) / 2,
        "sqrt2": math.sqrt(2),
        "sqrt3": math.sqrt(3)
    }


# Plugin metadata
PLUGIN_INFO = {
    "name": "advanced_calculator",
    "version": "1.0.0",
    "description": "Advanced mathematical operations and constants",
    "author": "A.N.A. Team",
    "category": "utility",
    "tools": [
        {
            "name": "calculate_advanced",
            "description": "Perform advanced mathematical calculations",
            "function": calculate_advanced
        },
        {
            "name": "get_math_constants",
            "description": "Get mathematical constants (pi, e, golden ratio, etc.)",
            "function": get_math_constants
        }
    ]
}


# For testing
if __name__ == "__main__":
    print("Testing Advanced Calculator Plugin...")
    
    # Test eval
    result = calculate_advanced("2 + 2 * 3", "eval")
    print(f"2 + 2 * 3 = {result}")
    
    # Test sqrt
    result = calculate_advanced("16", "sqrt")
    print(f"sqrt(16) = {result}")
    
    # Test factorial
    result = calculate_advanced("5", "factorial")
    print(f"5! = {result}")
    
    # Test constants
    constants = get_math_constants()
    print(f"π = {constants['pi']:.6f}")
    print(f"e = {constants['e']:.6f}")
