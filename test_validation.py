#!/usr/bin/env python3
"""Test script for code validation function"""
import ast

# Security configuration for code validation
ALLOWED_MODULES = {
    'FreeCAD', 'Part', 'Draft', 'Sketcher', 'PartDesign',
    'math', 'numpy', 'Mesh', 'Arch',
    'TechDraw', 'Spreadsheet', 'Drawing', 'Import',
    'App', 'Gui', 'FreeCADGui'
}

DANGEROUS_BUILTINS = {
    '__import__', 'eval', 'exec', 'compile', 'open',
    '__builtins__', 'globals', 'locals', 'vars',
    'dir', 'getattr', 'setattr', 'delattr', 'hasattr'
}

DANGEROUS_ATTRIBUTES = {
    '__code__', '__globals__', '__dict__', '__class__',
    '__subclasses__', '__bases__', '__mro__'
}

def validate_code_safety(code: str) -> tuple:
    """
    Validate macro code for security issues.

    Returns:
        tuple: (is_safe: bool, error_message: str)
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return (False, f"Syntax error: {str(e)}")

    class SecurityVisitor(ast.NodeVisitor):
        def __init__(self):
            self.errors = []

        def visit_Import(self, node):
            """Check import statements"""
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name not in ALLOWED_MODULES:
                    self.errors.append(
                        f"Importing module '{alias.name}' is not allowed. "
                        f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
                    )
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            """Check from-import statements"""
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name not in ALLOWED_MODULES:
                    self.errors.append(
                        f"Importing from module '{node.module}' is not allowed. "
                        f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
                    )
            self.generic_visit(node)

        def visit_Name(self, node):
            """Check for dangerous built-in usage"""
            if node.id in DANGEROUS_BUILTINS:
                self.errors.append(
                    f"Using '{node.id}' is not allowed for security reasons"
                )
            self.generic_visit(node)

        def visit_Attribute(self, node):
            """Check for dangerous attribute access"""
            if isinstance(node.attr, str) and node.attr in DANGEROUS_ATTRIBUTES:
                self.errors.append(
                    f"Accessing attribute '{node.attr}' is not allowed for security reasons"
                )
            self.generic_visit(node)

        def visit_Call(self, node):
            """Check for dangerous function calls"""
            # Check if calling dangerous builtins
            if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_BUILTINS:
                self.errors.append(
                    f"Calling '{node.func.id}' is not allowed for security reasons"
                )
            self.generic_visit(node)

    visitor = SecurityVisitor()
    visitor.visit(tree)

    if visitor.errors:
        return (False, "; ".join(visitor.errors))

    return (True, "")


# Test cases
test_cases = [
    # Safe code
    ("import FreeCAD as App\nimport Part", True, "Safe imports"),
    ("import math\nx = math.sqrt(16)", True, "Safe math import"),

    # Dangerous code
    ("import os", False, "Unsafe OS import"),
    ("import subprocess", False, "Unsafe subprocess import"),
    ("eval('1+1')", False, "Dangerous eval"),
    ("exec('print(1)')", False, "Dangerous exec"),
    ("open('/etc/passwd')", False, "Dangerous open"),
    ("__import__('os')", False, "Dangerous __import__"),
    ("x.__class__", False, "Dangerous attribute access"),
]

print("Running validation tests...\n")
passed = 0
failed = 0

for code, should_pass, description in test_cases:
    is_safe, error_msg = validate_code_safety(code)

    if is_safe == should_pass:
        print(f"✓ PASS: {description}")
        passed += 1
    else:
        print(f"✗ FAIL: {description}")
        print(f"  Code: {code}")
        print(f"  Expected: {'safe' if should_pass else 'unsafe'}")
        print(f"  Got: {'safe' if is_safe else 'unsafe'}")
        if error_msg:
            print(f"  Error: {error_msg}")
        failed += 1

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
print(f"{'='*50}")
