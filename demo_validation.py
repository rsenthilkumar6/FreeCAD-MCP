#!/usr/bin/env python3
"""
Demo script showing code validation in action
This demonstrates how the validation protects against dangerous operations
"""

import ast
import sys

# Import the validation function
sys.path.insert(0, '/Users/rajamans/Library/Application Support/FreeCAD/Mod/FreeCAD-MCP')

# Security configuration
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
    """Validate macro code for security issues."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return (False, f"Syntax error: {str(e)}")

    class SecurityVisitor(ast.NodeVisitor):
        def __init__(self):
            self.errors = []

        def visit_Import(self, node):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name not in ALLOWED_MODULES:
                    self.errors.append(
                        f"Importing module '{alias.name}' is not allowed"
                    )
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name not in ALLOWED_MODULES:
                    self.errors.append(
                        f"Importing from module '{node.module}' is not allowed"
                    )
            self.generic_visit(node)

        def visit_Name(self, node):
            if node.id in DANGEROUS_BUILTINS:
                self.errors.append(f"Using '{node.id}' is not allowed")
            self.generic_visit(node)

        def visit_Attribute(self, node):
            if isinstance(node.attr, str) and node.attr in DANGEROUS_ATTRIBUTES:
                self.errors.append(f"Accessing attribute '{node.attr}' is not allowed")
            self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_BUILTINS:
                self.errors.append(f"Calling '{node.func.id}' is not allowed")
            self.generic_visit(node)

    visitor = SecurityVisitor()
    visitor.visit(tree)

    if visitor.errors:
        return (False, "; ".join(visitor.errors))
    return (True, "")


print("=" * 70)
print("FreeCAD MCP Server - Code Validation Demo")
print("=" * 70)
print()

# Demo 1: Safe FreeCAD code
print("1. SAFE CODE - FreeCAD Box Creation")
print("-" * 70)
safe_code_1 = """
import FreeCAD as App
import Part

# Create a box
box = Part.makeBox(10, 10, 10)
App.ActiveDocument.addObject("Part::Feature", "Box").Shape = box
"""
print("Code:")
print(safe_code_1)
is_safe, error = validate_code_safety(safe_code_1)
print(f"Result: {'✓ PASSED' if is_safe else '✗ BLOCKED'}")
if error:
    print(f"Error: {error}")
print()

# Demo 2: Safe math operations
print("2. SAFE CODE - Math Operations")
print("-" * 70)
safe_code_2 = """
import math
import numpy as np

radius = 5
circumference = 2 * math.pi * radius
area = math.pi * radius ** 2
"""
print("Code:")
print(safe_code_2)
is_safe, error = validate_code_safety(safe_code_2)
print(f"Result: {'✓ PASSED' if is_safe else '✗ BLOCKED'}")
if error:
    print(f"Error: {error}")
print()

# Demo 3: Dangerous file operations
print("3. DANGEROUS CODE - File System Access")
print("-" * 70)
dangerous_code_1 = """
# Attempting to read system files
with open('/etc/passwd', 'r') as f:
    data = f.read()
"""
print("Code:")
print(dangerous_code_1)
is_safe, error = validate_code_safety(dangerous_code_1)
print(f"Result: {'✓ PASSED' if is_safe else '✗ BLOCKED'}")
if error:
    print(f"Error: {error}")
print()

# Demo 4: Code injection attempt
print("4. DANGEROUS CODE - Code Injection via eval()")
print("-" * 70)
dangerous_code_2 = """
# Attempting code injection
user_input = "malicious_code()"
eval(user_input)
"""
print("Code:")
print(dangerous_code_2)
is_safe, error = validate_code_safety(dangerous_code_2)
print(f"Result: {'✓ PASSED' if is_safe else '✗ BLOCKED'}")
if error:
    print(f"Error: {error}")
print()

# Demo 5: Subprocess execution
print("5. DANGEROUS CODE - Subprocess Execution")
print("-" * 70)
dangerous_code_3 = """
import subprocess
# Attempting to execute shell commands
subprocess.run(['rm', '-rf', '/'])
"""
print("Code:")
print(dangerous_code_3)
is_safe, error = validate_code_safety(dangerous_code_3)
print(f"Result: {'✓ PASSED' if is_safe else '✗ BLOCKED'}")
if error:
    print(f"Error: {error}")
print()

# Demo 6: Dynamic import
print("6. DANGEROUS CODE - Dynamic Module Import")
print("-" * 70)
dangerous_code_4 = """
# Attempting dynamic import to bypass restrictions
os_module = __import__('os')
os_module.system('whoami')
"""
print("Code:")
print(dangerous_code_4)
is_safe, error = validate_code_safety(dangerous_code_4)
print(f"Result: {'✓ PASSED' if is_safe else '✗ BLOCKED'}")
if error:
    print(f"Error: {error}")
print()

# Demo 7: Introspection attack
print("7. DANGEROUS CODE - Python Introspection Attack")
print("-" * 70)
dangerous_code_5 = """
# Attempting to access internal Python structures
for cls in object.__subclasses__():
    if 'warning' in cls.__name__.lower():
        print(cls)
"""
print("Code:")
print(dangerous_code_5)
is_safe, error = validate_code_safety(dangerous_code_5)
print(f"Result: {'✓ PASSED' if is_safe else '✗ BLOCKED'}")
if error:
    print(f"Error: {error}")
print()

print("=" * 70)
print("Summary: Validation successfully protects against dangerous operations")
print("while allowing safe FreeCAD scripting.")
print("=" * 70)
