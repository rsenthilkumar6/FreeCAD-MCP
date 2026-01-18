# -*- coding: utf-8 -*-
"""
FreeCAD MCP Client - Absolute Path Optimized Version
Ensures 100% path resolution success rate
"""

from typing import Any, Dict
import socket
import json
import asyncio
import re
import sys
import ast
import os
import argparse
import traceback
from pydantic import BaseModel

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    print(f"Unable to import FastMCP: {str(e)}\nPlease run `pip install mcp`")
    sys.exit(1)

mod_dir = os.path.join(os.path.expanduser("~"), "FreeCAD", "Mod", "freecad_mcp")
if mod_dir not in sys.path:
    sys.path.append(mod_dir)

mcp = FastMCP("freecad-bridge-absolute")
FREECAD_HOST = 'localhost'
FREECAD_PORT = 9876

# ============================================================================
# MCP Prompts - Guide LLM behavior
# ============================================================================

@mcp.prompt()
def freecad_design_workflow() -> str:
    """FreeCAD MCP Design Best Practices"""
    return """
# FreeCAD MCP Design Workflow

Follow these best practices for autonomous CAD design:

## 1. Visual Feedback (CRITICAL)
- ALWAYS use get_view() after creating/modifying geometry to SEE the result
- Request multiple views to understand spatial relationships
- Views available: Isometric, Front, Top, Right, Back, Left, Bottom
- Example: get_view("Isometric") → See what you created!

## 2. Parts Library First (CRITICAL)
- ALWAYS check get_parts_list() BEFORE creating standard parts
- Never recreate bolts, nuts, washers, bearings from scratch
- Use insert_part_from_library() for standard parts
- Benefits: Correct dimensions (ISO/DIN/ANSI standards), 50% faster

Workflow:
  1. Check: parts = get_parts_list()
  2. Search: Look for M6 bolt, 608 bearing, etc.
  3. Insert: insert_part_from_library("Fasteners/Screws/ISO4017/M6_x_20.FCStd")

## 3. Tool Selection
- Use specific tools (create_body, create_sketch) for parametric design
- Use execute_code() ONLY for operations not covered by tools
- execute_code() is flexible but less reliable than dedicated tools

## 4. Parametric Design
- Start with create_body() for parametric parts
- Add sketches with create_sketch()
- Add constraints for fully-constrained sketches
- Use extrude_sketch(), revolve_sketch(), pocket_sketch()

## 5. Validation
- Use check_solid_valid() before export
- Use get_bounding_box() to verify dimensions
- Use analyze_shape() for comprehensive checks

## 6. Export
- Use export_stl() for 3D printing
- Use export_step() for professional CAD interchange
- Multiple formats available: STL, STEP, IGES, OBJ, SVG, PDF

## Example Full Workflow:
```
1. Create document: create_document("MyDesign")
2. Check parts library: parts = get_parts_list()
3. Create body: create_body("Base")
4. Create sketch: create_sketch("Base", "Sketch001", "XY")
5. Add geometry: add_circle("Sketch001", 0, 0, 10)
6. Extrude: extrude_sketch("Sketch001", 20)
7. View result: get_view("Isometric")
8. Validate: check_solid_valid("Pad")
9. Export: export_stl("Pad", "/path/to/part.stl")
```

Remember: Visual feedback (get_view) and parts library are game changers for AI design!
"""

def normalize_path_for_platform(path: str) -> str:
    """
    Normalize path to current platform
    Fixes: Windows paths on macOS/Linux, vice versa

    Example:
        /Users/user/AppData/Roaming/FreeCAD/Macro/test.FCMacro on macOS
        → /Users/user/Library/Application Support/FreeCAD/Macro/test.FCMacro
    """
    import platform
    system = platform.system()

    # If path contains Windows-style components on non-Windows
    if system != "Windows" and ("AppData" in path or "Roaming" in path):
        if system == "Darwin":  # macOS
            path = path.replace("AppData/Roaming", "Library/Application Support")
            path = path.replace("AppData\\Roaming", "Library/Application Support")
        else:  # Linux
            path = path.replace("AppData/Roaming", ".local/share")
            path = path.replace("AppData\\Roaming", ".local/share")

    # If path contains macOS-style components on non-macOS
    elif system != "Darwin" and "Library/Application Support" in path:
        if system == "Windows":
            path = path.replace("Library/Application Support", "AppData/Roaming")
        else:  # Linux
            path = path.replace("Library/Application Support", ".local/share")

    # If path contains Linux-style components on non-Linux
    elif ".local/share" in path:
        if system == "Windows":
            path = path.replace(".local/share", "AppData/Roaming")
        elif system == "Darwin":
            path = path.replace(".local/share", "Library/Application Support")

    # Normalize slashes for current platform
    path = os.path.normpath(path)
    return path

def get_absolute_macro_path(macro_name: str) -> str:
    """
    Get absolute path of macro file
    Ensure 100% path resolution success (cross-platform)
    """
    # Get FreeCAD macro directory (cross-platform)
    import platform
    system = platform.system()

    if system == "Windows":
        macro_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "FreeCAD", "Macro")
    elif system == "Darwin":  # macOS
        macro_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "FreeCAD", "Macro")
    else:  # Linux and others
        macro_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "FreeCAD", "Macro")

    # Create directory if it doesn't exist
    os.makedirs(macro_dir, exist_ok=True)

    # Ensure .FCMacro extension
    if not macro_name.endswith('.FCMacro'):
        macro_name = f"{macro_name}.FCMacro"

    # Return absolute path
    absolute_path = os.path.join(macro_dir, macro_name)
    return absolute_path

def normalize_macro_code(code: str) -> str:
    """Normalize macro code"""
    code = code.strip()
    if not code:
        return "# FreeCAD Macro\n"
    lines = code.splitlines()
    has_freecad = any("import FreeCAD" in line for line in lines)
    has_gui = any("import FreeCADGui" in line for line in lines)
    has_part = any("import Part" in line for line in lines)
    has_math = any("import math" in line for line in lines)
    
    result_lines = []
    if not has_freecad:
        result_lines.append("import FreeCAD as App")
    if not has_gui:
        result_lines.append("import FreeCADGui as Gui")
    if not has_part:
        result_lines.append("import Part")
    if not has_math:
        result_lines.append("import math")
    if result_lines:
        result_lines.append("")
    
    result_lines.extend(lines)
    return "\n".join(result_lines)

async def send_command_to_freecad(command: Dict[str, Any]) -> Dict[str, Any]:
    """Send command to FreeCAD server"""
    try:
        reader, writer = await asyncio.open_connection(FREECAD_HOST, FREECAD_PORT)

        # Send command
        command_json = json.dumps(command, ensure_ascii=False)
        writer.write(command_json.encode('utf-8'))
        await writer.drain()

        # Receive response in chunks until complete
        response_data = b""
        while True:
            chunk = await asyncio.wait_for(reader.read(8192), timeout=30)
            if not chunk:
                break
            response_data += chunk
            if len(response_data) > 10 * 1024 * 1024:  # 10MB limit
                raise ValueError("Response too large")

        response = json.loads(response_data.decode('utf-8'))

        writer.close()
        await writer.wait_closed()

        return response

    except Exception as e:
        return {"result": "error", "message": f"Failed to connect to FreeCAD server: {str(e)}"}

@mcp.tool()
def create_macro(macro_name: str, template_type: str = "default") -> Dict[str, Any]:
    """
    Create FreeCAD macro file - Absolute path version

    Args:
        macro_name: Macro file name (only letters, numbers, underscores and hyphens allowed)
        template_type: Template type (default, basic, part, sketch)
    """
    try:
        # Validate macro name
        if not re.match(r'^[a-zA-Z0-9_-]+$', macro_name):
            return {"result": "error", "message": "Macro name can only contain letters, numbers, underscores and hyphens"}

        # Get absolute path
        absolute_path = get_absolute_macro_path(macro_name)
        print(f"Creating macro file: {absolute_path}")

        command = {
            "type": "create_macro",
            "params": {
                "macro_name": macro_name,
                "template_type": template_type
            }
        }

        # Check if there's a running event loop, avoid conflict
        try:
            loop = asyncio.get_running_loop()
            # If there's a running loop, use thread pool execution
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            # No running loop, can directly use asyncio.run
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def update_macro(macro_name: str, code: str) -> Dict[str, Any]:
    """
    Update FreeCAD macro file content - Absolute path version

    Args:
        macro_name: Macro file name
        code: Python code content
    """
    try:
        # Get absolute path
        absolute_path = get_absolute_macro_path(macro_name)
        print(f"Updating macro file: {absolute_path}")

        # Normalize code
        normalized_code = normalize_macro_code(code)

        command = {
            "type": "update_macro",
            "params": {
                "macro_name": macro_name,
                "code": normalized_code
            }
        }

        # Check if there's a running event loop, avoid conflict
        try:
            loop = asyncio.get_running_loop()
            # If there's a running loop, use thread pool execution
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            # No running loop, can directly use asyncio.run
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def run_macro(macro_path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run FreeCAD macro - Absolute path version

    Args:
        macro_path: Macro file path (will be automatically converted to absolute path)
        params: Optional parameters
    """
    try:
        # Normalize path for current platform (fixes Windows paths on macOS, etc.)
        macro_path = normalize_path_for_platform(macro_path)

        # If relative path or macro name is passed, convert to absolute path
        if not os.path.isabs(macro_path):
            # Extract macro name
            macro_name = os.path.basename(macro_path)
            if not macro_name.endswith('.FCMacro'):
                macro_name = f"{macro_name}.FCMacro"

            # Get absolute path
            absolute_path = get_absolute_macro_path(macro_name.replace('.FCMacro', ''))
        else:
            absolute_path = macro_path

        print(f"Executing macro file: {absolute_path}")

        command = {
            "type": "run_macro",
            "params": {
                "macro_path": absolute_path,
                "params": params if params is not None else {}
            }
        }

        # Check if there's a running event loop, avoid conflict
        try:
            loop = asyncio.get_running_loop()
            # If there's a running loop, use thread pool execution
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            # No running loop, can directly use asyncio.run
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def validate_macro_code(macro_name: str = None, code: str = None) -> Dict[str, Any]:
    """
    Validate macro code syntax

    Args:
        macro_name: Macro file name (optional)
        code: Code content (optional)
    """
    try:
        if macro_name:
            absolute_path = get_absolute_macro_path(macro_name)
            print(f"Validating macro file: {absolute_path}")

        command = {
            "type": "validate_macro_code",
            "params": {
                "macro_name": macro_name if macro_name is not None else "",
                "code": code if code is not None else ""
            }
        }

        # Check if there's a running event loop, avoid conflict
        try:
            loop = asyncio.get_running_loop()
            # If there's a running loop, use thread pool execution
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            # No running loop, can directly use asyncio.run
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def set_view(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Set FreeCAD view

    Args:
        params: View parameters
    """
    try:
        command = {
            "type": "set_view",
            "params": params
        }

        # Check if there's a running event loop, avoid conflict
        try:
            loop = asyncio.get_running_loop()
            # If there's a running loop, use thread pool execution
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            # No running loop, can directly use asyncio.run
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def get_report() -> Dict[str, Any]:
    """Get FreeCAD server report"""
    try:
        command = {
            "type": "get_report",
            "params": {}
        }

        # Check if there's a running event loop, avoid conflict
        try:
            loop = asyncio.get_running_loop()
            # If there's a running loop, use thread pool execution
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            # No running loop, can directly use asyncio.run
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def list_documents() -> Dict[str, Any]:
    """
    List all open documents with their information

    Returns a dict containing all open documents with their names, labels, and object counts
    """
    try:
        command = {
            "type": "list_documents",
            "params": {}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def get_active_document() -> Dict[str, Any]:
    """
    Get active document details

    Returns information about the currently active document including name, label, and objects
    """
    try:
        command = {
            "type": "get_active_document",
            "params": {}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def create_document(name: str) -> Dict[str, Any]:
    """
    Create new FreeCAD document

    Args:
        name: Document name (only letters, numbers, underscores allowed)

    Returns a dict with the result and created document name
    """
    try:
        command = {
            "type": "create_document",
            "params": {"name": name}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def save_document(filename: str) -> Dict[str, Any]:
    """
    Save active document to file

    Args:
        filename: Absolute path to save the document (.FCStd extension)

    Returns a dict with the result and saved file path
    """
    try:
        command = {
            "type": "save_document",
            "params": {"filename": filename}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def close_document(name: str) -> Dict[str, Any]:
    """
    Close a document by name

    Args:
        name: Document name to close

    Returns a dict with the result
    """
    try:
        command = {
            "type": "close_document",
            "params": {"name": name}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def list_objects(document_name: str = None) -> Dict[str, Any]:
    """
    List objects in a document

    Args:
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with list of objects and their properties
    """
    try:
        command = {
            "type": "list_objects",
            "params": {"document_name": document_name if document_name else ""}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def get_object_properties(object_name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Get object properties

    Args:
        object_name: Name of the object
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with object properties including type, label, placement, and shape info
    """
    try:
        command = {
            "type": "get_object_properties",
            "params": {
                "object_name": object_name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def delete_object(object_name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Delete an object from a document

    Args:
        object_name: Name of the object to delete
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result
    """
    try:
        command = {
            "type": "delete_object",
            "params": {
                "object_name": object_name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def export_stl(object_name: str, filepath: str, mesh_deviation: float = 0.1) -> Dict[str, Any]:
    """
    Export FreeCAD object as STL file

    Args:
        object_name: Name of the object to export
        filepath: Absolute path for the output STL file
        mesh_deviation: Mesh quality parameter (0.01-1.0, lower=finer mesh)
    """
    try:
        if not os.path.isabs(filepath):
            return {"result": "error", "message": "filepath must be an absolute path"}

        if not filepath.lower().endswith('.stl'):
            filepath = f"{filepath}.stl"

        command = {
            "type": "export_stl",
            "params": {
                "object_name": object_name,
                "filepath": filepath,
                "mesh_deviation": mesh_deviation
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def export_step(filepath: str, objects: str = None) -> Dict[str, Any]:
    """
    Export FreeCAD document or specific objects as STEP file

    Args:
        filepath: Absolute path for the output STEP file
        objects: Optional comma-separated list of object names to export (exports all if None)
    """
    try:
        if not os.path.isabs(filepath):
            return {"result": "error", "message": "filepath must be an absolute path"}

        if not (filepath.lower().endswith('.step') or filepath.lower().endswith('.stp')):
            filepath = f"{filepath}.step"

        command = {
            "type": "export_step",
            "params": {
                "filepath": filepath,
                "objects": objects
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def export_iges(filepath: str, objects: str = None) -> Dict[str, Any]:
    """
    Export FreeCAD document or specific objects as IGES file

    Args:
        filepath: Absolute path for the output IGES file
        objects: Optional comma-separated list of object names to export (exports all if None)
    """
    try:
        if not os.path.isabs(filepath):
            return {"result": "error", "message": "filepath must be an absolute path"}

        if not (filepath.lower().endswith('.iges') or filepath.lower().endswith('.igs')):
            filepath = f"{filepath}.iges"

        command = {
            "type": "export_iges",
            "params": {
                "filepath": filepath,
                "objects": objects
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def export_obj(object_name: str, filepath: str, mesh_deviation: float = 0.1) -> Dict[str, Any]:
    """
    Export FreeCAD object as OBJ file

    Args:
        object_name: Name of the object to export
        filepath: Absolute path for the output OBJ file
        mesh_deviation: Mesh quality parameter (0.01-1.0, lower=finer mesh)
    """
    try:
        if not os.path.isabs(filepath):
            return {"result": "error", "message": "filepath must be an absolute path"}

        if not filepath.lower().endswith('.obj'):
            filepath = f"{filepath}.obj"

        command = {
            "type": "export_obj",
            "params": {
                "object_name": object_name,
                "filepath": filepath,
                "mesh_deviation": mesh_deviation
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def export_svg(filepath: str, page_name: str = None) -> Dict[str, Any]:
    """
    Export FreeCAD 2D drawing/TechDraw page as SVG file

    Args:
        filepath: Absolute path for the output SVG file
        page_name: Optional name of TechDraw page to export (exports first page if None)
    """
    try:
        if not os.path.isabs(filepath):
            return {"result": "error", "message": "filepath must be an absolute path"}

        if not filepath.lower().endswith('.svg'):
            filepath = f"{filepath}.svg"

        command = {
            "type": "export_svg",
            "params": {
                "filepath": filepath,
                "page_name": page_name
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def export_pdf(filepath: str, page_name: str = None) -> Dict[str, Any]:
    """
    Export FreeCAD TechDraw page as PDF file

    Args:
        filepath: Absolute path for the output PDF file
        page_name: Optional name of TechDraw page to export (exports first page if None)
    """
    try:
        if not os.path.isabs(filepath):
            return {"result": "error", "message": "filepath must be an absolute path"}

        if not filepath.lower().endswith('.pdf'):
            filepath = f"{filepath}.pdf"

        command = {
            "type": "export_pdf",
            "params": {
                "filepath": filepath,
                "page_name": page_name
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def get_bounding_box(object_name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Get bounding box of a FreeCAD object

    Args:
        object_name: Name of the object
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with bounding box data including xmin, xmax, ymin, ymax, zmin, zmax, center, diagonal
    """
    try:
        command = {
            "type": "get_bounding_box",
            "params": {
                "object_name": object_name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def measure_distance(obj1_name: str, obj2_name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Measure minimum distance between two FreeCAD objects

    Args:
        obj1_name: Name of the first object
        obj2_name: Name of the second object
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the minimum distance between the two objects
    """
    try:
        command = {
            "type": "measure_distance",
            "params": {
                "obj1_name": obj1_name,
                "obj2_name": obj2_name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def get_volume(object_name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Get volume of a FreeCAD solid object

    Args:
        object_name: Name of the object
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the object's volume in cubic millimeters
    """
    try:
        command = {
            "type": "get_volume",
            "params": {
                "object_name": object_name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def get_surface_area(object_name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Get surface area of a FreeCAD object

    Args:
        object_name: Name of the object
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the object's surface area in square millimeters
    """
    try:
        command = {
            "type": "get_surface_area",
            "params": {
                "object_name": object_name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def get_center_of_mass(object_name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Get center of mass of a FreeCAD object

    Args:
        object_name: Name of the object
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the center of mass coordinates (x, y, z)
    """
    try:
        command = {
            "type": "get_center_of_mass",
            "params": {
                "object_name": object_name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def get_mass_properties(object_name: str, density: float = 1.0, document_name: str = None) -> Dict[str, Any]:
    """
    Get mass properties of a FreeCAD object

    Args:
        object_name: Name of the object
        density: Material density in g/cm^3 (default: 1.0)
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with mass, volume, center of mass, and inertia tensor
    """
    try:
        command = {
            "type": "get_mass_properties",
            "params": {
                "object_name": object_name,
                "density": density,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def check_solid_valid(object_name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Check if a FreeCAD object is a valid solid

    Args:
        object_name: Name of the object
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with validity status and any error messages
    """
    try:
        command = {
            "type": "check_solid_valid",
            "params": {
                "object_name": object_name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def analyze_shape(object_name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Perform comprehensive shape analysis on a FreeCAD object

    Args:
        object_name: Name of the object
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with detailed shape analysis including:
    - Edge count, face count, vertex count
    - Volume and surface area
    - Bounding box dimensions
    - Center of mass
    - Validity status
    """
    try:
        command = {
            "type": "analyze_shape",
            "params": {
                "object_name": object_name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

# ============================================================================
# Part Design Operations
# ============================================================================

@mcp.tool()
def create_body(name: str, document_name: str = None) -> Dict[str, Any]:
    """
    Create a PartDesign Body container

    Args:
        name: Name for the body
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result and body name
    """
    try:
        command = {
            "type": "create_body",
            "params": {
                "name": name,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def create_sketch(body_name: str, sketch_name: str, plane: str, document_name: str = None) -> Dict[str, Any]:
    """
    Create a sketch on a body attached to a plane

    Args:
        body_name: Name of the body to attach sketch to
        sketch_name: Name for the sketch
        plane: Plane to attach sketch to (XY, XZ, or YZ)
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result and sketch name
    """
    try:
        if plane not in ["XY", "XZ", "YZ"]:
            return {"result": "error", "message": "plane must be XY, XZ, or YZ"}

        command = {
            "type": "create_sketch",
            "params": {
                "body_name": body_name,
                "sketch_name": sketch_name,
                "plane": plane,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def add_circle(sketch_name: str, center_x: float, center_y: float, radius: float, document_name: str = None) -> Dict[str, Any]:
    """
    Add a circle to a sketch

    Args:
        sketch_name: Name of the sketch
        center_x: X coordinate of circle center
        center_y: Y coordinate of circle center
        radius: Circle radius
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result
    """
    try:
        command = {
            "type": "add_circle",
            "params": {
                "sketch_name": sketch_name,
                "center_x": center_x,
                "center_y": center_y,
                "radius": radius,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def add_rectangle(sketch_name: str, x1: float, y1: float, x2: float, y2: float, document_name: str = None) -> Dict[str, Any]:
    """
    Add a rectangle to a sketch

    Args:
        sketch_name: Name of the sketch
        x1: X coordinate of first corner
        y1: Y coordinate of first corner
        x2: X coordinate of opposite corner
        y2: Y coordinate of opposite corner
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result
    """
    try:
        command = {
            "type": "add_rectangle",
            "params": {
                "sketch_name": sketch_name,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def add_line(sketch_name: str, x1: float, y1: float, x2: float, y2: float, document_name: str = None) -> Dict[str, Any]:
    """
    Add a line to a sketch

    Args:
        sketch_name: Name of the sketch
        x1: X coordinate of line start
        y1: Y coordinate of line start
        x2: X coordinate of line end
        y2: Y coordinate of line end
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result
    """
    try:
        command = {
            "type": "add_line",
            "params": {
                "sketch_name": sketch_name,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def add_arc(sketch_name: str, center_x: float, center_y: float, radius: float, start_angle: float, end_angle: float, document_name: str = None) -> Dict[str, Any]:
    """
    Add an arc to a sketch

    Args:
        sketch_name: Name of the sketch
        center_x: X coordinate of arc center
        center_y: Y coordinate of arc center
        radius: Arc radius
        start_angle: Start angle in degrees
        end_angle: End angle in degrees
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result
    """
    try:
        command = {
            "type": "add_arc",
            "params": {
                "sketch_name": sketch_name,
                "center_x": center_x,
                "center_y": center_y,
                "radius": radius,
                "start_angle": start_angle,
                "end_angle": end_angle,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def add_constraint(sketch_name: str, constraint_type: str, params: Dict[str, Any], document_name: str = None) -> Dict[str, Any]:
    """
    Add a constraint to a sketch

    Args:
        sketch_name: Name of the sketch
        constraint_type: Type of constraint (horizontal, vertical, coincident, distance, radius, angle, etc.)
        params: Parameters for the constraint (depends on constraint type)
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result
    """
    try:
        command = {
            "type": "add_constraint",
            "params": {
                "sketch_name": sketch_name,
                "constraint_type": constraint_type,
                "constraint_params": params,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def extrude_sketch(sketch_name: str, length: float, reversed: bool = False, document_name: str = None) -> Dict[str, Any]:
    """
    Create a pad (extrusion) from a sketch

    Args:
        sketch_name: Name of the sketch to extrude
        length: Extrusion length
        reversed: Extrude in reverse direction (default False)
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result and pad name
    """
    try:
        command = {
            "type": "extrude_sketch",
            "params": {
                "sketch_name": sketch_name,
                "length": length,
                "reversed": reversed,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def revolve_sketch(sketch_name: str, axis: str, angle: float, document_name: str = None) -> Dict[str, Any]:
    """
    Create a revolution from a sketch

    Args:
        sketch_name: Name of the sketch to revolve
        axis: Axis to revolve around (X, Y, or Z)
        angle: Angle of revolution in degrees (360 for full revolution)
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result and revolution name
    """
    try:
        if axis not in ["X", "Y", "Z"]:
            return {"result": "error", "message": "axis must be X, Y, or Z"}

        command = {
            "type": "revolve_sketch",
            "params": {
                "sketch_name": sketch_name,
                "axis": axis,
                "angle": angle,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def pocket_sketch(sketch_name: str, length: float, document_name: str = None) -> Dict[str, Any]:
    """
    Create a pocket (cut) from a sketch

    Args:
        sketch_name: Name of the sketch to use for pocket
        length: Pocket depth
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result and pocket name
    """
    try:
        command = {
            "type": "pocket_sketch",
            "params": {
                "sketch_name": sketch_name,
                "length": length,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def create_fillet(edge_indices: str, radius: float, base_object: str, document_name: str = None) -> Dict[str, Any]:
    """
    Add fillet to edges

    Args:
        edge_indices: Comma-separated edge indices (e.g., "1,2,3")
        radius: Fillet radius
        base_object: Name of the object to fillet
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result and fillet name
    """
    try:
        command = {
            "type": "create_fillet",
            "params": {
                "edge_indices": edge_indices,
                "radius": radius,
                "base_object": base_object,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def create_chamfer(edge_indices: str, size: float, base_object: str, document_name: str = None) -> Dict[str, Any]:
    """
    Add chamfer to edges

    Args:
        edge_indices: Comma-separated edge indices (e.g., "1,2,3")
        size: Chamfer size
        base_object: Name of the object to chamfer
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result and chamfer name
    """
    try:
        command = {
            "type": "create_chamfer",
            "params": {
                "edge_indices": edge_indices,
                "size": size,
                "base_object": base_object,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def create_pattern_linear(feature_name: str, direction: str, length: float, occurrences: int, document_name: str = None) -> Dict[str, Any]:
    """
    Create a linear pattern of a feature

    Args:
        feature_name: Name of the feature to pattern
        direction: Direction vector as "x,y,z" (e.g., "1,0,0" for X axis)
        length: Total length of pattern
        occurrences: Number of occurrences
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result and pattern name
    """
    try:
        command = {
            "type": "create_pattern_linear",
            "params": {
                "feature_name": feature_name,
                "direction": direction,
                "length": length,
                "occurrences": occurrences,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def create_pattern_polar(feature_name: str, axis: str, angle: float, occurrences: int, document_name: str = None) -> Dict[str, Any]:
    """
    Create a polar pattern of a feature

    Args:
        feature_name: Name of the feature to pattern
        axis: Axis to rotate around (X, Y, or Z)
        angle: Total angle in degrees
        occurrences: Number of occurrences
        document_name: Document name (optional, uses active document if not specified)

    Returns a dict with the result and pattern name
    """
    try:
        if axis not in ["X", "Y", "Z"]:
            return {"result": "error", "message": "axis must be X, Y, or Z"}

        command = {
            "type": "create_pattern_polar",
            "params": {
                "feature_name": feature_name,
                "axis": axis,
                "angle": angle,
                "occurrences": occurrences,
                "document_name": document_name if document_name else ""
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

# ============================================================================
# View Management Tools
# ============================================================================

@mcp.tool()
def set_camera_position(x: float, y: float, z: float, look_at_x: float = 0.0, look_at_y: float = 0.0, look_at_z: float = 0.0) -> Dict[str, Any]:
    """
    Set camera position and target point

    Args:
        x: Camera X position
        y: Camera Y position
        z: Camera Z position
        look_at_x: Target point X coordinate (default 0.0)
        look_at_y: Target point Y coordinate (default 0.0)
        look_at_z: Target point Z coordinate (default 0.0)

    Returns a dict with the result
    """
    try:
        command = {
            "type": "set_camera_position",
            "params": {
                "x": x,
                "y": y,
                "z": z,
                "look_at_x": look_at_x,
                "look_at_y": look_at_y,
                "look_at_z": look_at_z
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def set_view_direction(direction: str) -> Dict[str, Any]:
    """
    Set view direction

    Args:
        direction: View direction - one of: front, back, top, bottom, left, right, iso

    Returns a dict with the result
    """
    try:
        valid_directions = ["front", "back", "top", "bottom", "left", "right", "iso"]
        if direction.lower() not in valid_directions:
            return {"result": "error", "message": f"Invalid direction. Must be one of: {', '.join(valid_directions)}"}

        command = {
            "type": "set_view_direction",
            "params": {"direction": direction.lower()}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def zoom_to_fit() -> Dict[str, Any]:
    """
    Fit all objects in view (zoom to fit all)

    Returns a dict with the result
    """
    try:
        command = {
            "type": "zoom_to_fit",
            "params": {}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def zoom_to_selection(object_names: str) -> Dict[str, Any]:
    """
    Zoom to specific objects

    Args:
        object_names: Comma-separated list of object names to zoom to

    Returns a dict with the result
    """
    try:
        command = {
            "type": "zoom_to_selection",
            "params": {"object_names": object_names}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def set_perspective(enabled: bool) -> Dict[str, Any]:
    """
    Toggle between perspective and orthographic camera view

    Args:
        enabled: True for perspective view, False for orthographic view

    Returns a dict with the result
    """
    try:
        command = {
            "type": "set_perspective",
            "params": {"enabled": enabled}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def capture_screenshot(filepath: str, width: int = 800, height: int = 600, transparent_background: bool = False) -> Dict[str, Any]:
    """
    Capture current view as image file

    Args:
        filepath: Absolute path for the output image file (supports .png, .jpg, .bmp)
        width: Image width in pixels (default 800)
        height: Image height in pixels (default 600)
        transparent_background: Use transparent background (PNG only, default False)

    Returns a dict with the result and saved file path
    """
    try:
        if not os.path.isabs(filepath):
            return {"result": "error", "message": "filepath must be an absolute path"}

        valid_extensions = ['.png', '.jpg', '.jpeg', '.bmp']
        if not any(filepath.lower().endswith(ext) for ext in valid_extensions):
            filepath = f"{filepath}.png"

        command = {
            "type": "capture_screenshot",
            "params": {
                "filepath": filepath,
                "width": width,
                "height": height,
                "transparent_background": transparent_background
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def rotate_view(axis: str, angle: float) -> Dict[str, Any]:
    """
    Rotate view around an axis by specified angle

    Args:
        axis: Rotation axis - one of: x, y, z
        angle: Rotation angle in degrees

    Returns a dict with the result
    """
    try:
        valid_axes = ["x", "y", "z"]
        if axis.lower() not in valid_axes:
            return {"result": "error", "message": f"Invalid axis. Must be one of: {', '.join(valid_axes)}"}

        command = {
            "type": "rotate_view",
            "params": {
                "axis": axis.lower(),
                "angle": angle
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def set_render_style(style: str) -> Dict[str, Any]:
    """
    Set rendering style for the 3D view

    Args:
        style: Render style - one of: "Flat Lines", "Shaded", "Wireframe", "Points", "Hidden Line"

    Returns a dict with the result
    """
    try:
        valid_styles = ["Flat Lines", "Shaded", "Wireframe", "Points", "Hidden Line"]
        if style not in valid_styles:
            return {"result": "error", "message": f"Invalid style. Must be one of: {', '.join(valid_styles)}"}

        command = {
            "type": "set_render_style",
            "params": {"style": style}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def toggle_axis(visible: bool) -> Dict[str, Any]:
    """
    Show or hide the coordinate axis indicator

    Args:
        visible: True to show axis, False to hide

    Returns a dict with the result
    """
    try:
        command = {
            "type": "toggle_axis",
            "params": {"visible": visible}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def set_background_color(r: int, g: int, b: int) -> Dict[str, Any]:
    """
    Set background color of the 3D view

    Args:
        r: Red component (0-255)
        g: Green component (0-255)
        b: Blue component (0-255)

    Returns a dict with the result
    """
    try:
        if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
            return {"result": "error", "message": "RGB values must be between 0 and 255"}

        command = {
            "type": "set_background_color",
            "params": {
                "r": r,
                "g": g,
                "b": b
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

# ============================================================================
# Phase 1: Visual Feedback Tools
# ============================================================================

@mcp.tool()
def get_view(
    view_name: str = "Isometric",
    width: int = None,
    height: int = None,
    focus_object: str = None
) -> Dict[str, Any]:
    """
    Get screenshot of FreeCAD view from specific angle

    This enables visual feedback - LLM can SEE what it created!

    Args:
        view_name: View orientation - "Isometric", "Front", "Top", "Right", "Back", "Left", "Bottom"
        width: Screenshot width in pixels (optional, uses viewport width if not specified)
        height: Screenshot height in pixels (optional, uses viewport height if not specified)
        focus_object: Object name to focus on (optional, otherwise fits all objects)

    Returns:
        Dict with screenshot (base64 PNG) and view information

    Example:
        get_view("Front", width=800, height=600)
        get_view("Isometric", focus_object="Box")
    """
    try:
        command = {
            "type": "get_view",
            "params": {
                "view_name": view_name,
                "width": width,
                "height": height,
                "focus_object": focus_object
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

# ============================================================================
# Phase 2: Parts Library Tools
# ============================================================================

@mcp.tool()
def get_parts_list() -> Dict[str, Any]:
    """
    Get list of parts in FreeCAD parts library

    Returns a list of standard parts (bolts, nuts, bearings, etc.) that can be inserted.
    ALWAYS check this FIRST before creating parts from scratch!

    Returns:
        Dict with list of part paths like:
        - "Fasteners/Screws/ISO4017/M6_x_20.FCStd"
        - "Fasteners/Nuts/ISO4032/M6.FCStd"
        - "Bearings/Ball/608.FCStd"

    Example usage:
        1. Call get_parts_list() to see available parts
        2. Use insert_part_from_library() to insert the part

    Best practice:
        Before creating any standard part (bolt, nut, bearing, etc.),
        check if it exists in the parts library first!
    """
    try:
        command = {"type": "get_parts_list", "params": {}}

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def insert_part_from_library(relative_path: str) -> Dict[str, Any]:
    """
    Insert a standard part from the FreeCAD parts library

    Use this to insert pre-made standard parts like bolts, nuts, bearings.
    Much faster and more accurate than creating from scratch!

    Args:
        relative_path: Path from get_parts_list(), e.g. "Fasteners/Screws/ISO4017/M6_x_20.FCStd"

    Returns:
        Dict with result and screenshot of inserted part

    Example workflow:
        1. parts = get_parts_list()
        2. # Find M6 bolt in parts list
        3. insert_part_from_library("Fasteners/Screws/ISO4017/M6_x_20.FCStd")
        4. # Part is now in active document with correct dimensions

    Note: Requires FreeCAD parts_library addon to be installed
    """
    try:
        command = {
            "type": "insert_part_from_library",
            "params": {"relative_path": relative_path}
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=30)
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

# ============================================================================
# Phase 3: Flexible Code Execution
# ============================================================================

@mcp.tool()
def execute_code(code: str, validate: bool = True) -> Dict[str, Any]:
    """
    Execute arbitrary Python code in FreeCAD (with security validation)

    Use this ONLY when specific tools don't cover your needs.
    For common operations, prefer dedicated tools (create_body, create_sketch, etc.)

    Args:
        code: Python code to execute (has access to FreeCAD, Part, Draft, Sketcher modules)
        validate: Enable security validation (default True, RECOMMENDED)

    Security:
        - Code is validated using AST analysis
        - Only whitelisted modules allowed: FreeCAD, Part, Draft, Sketcher, PartDesign, math, numpy
        - Dangerous builtins blocked: eval, exec, __import__, open, compile
        - File system access restricted

    Returns:
        Dict with execution result, output, and screenshot

    Example:
        execute_code('''
import FreeCAD as App
import Part

doc = App.ActiveDocument
box = Part.makeBox(10, 10, 10)
doc.addObject("Part::Feature", "CustomBox").Shape = box
doc.recompute()
        ''')

    Best practices:
        - Use dedicated tools when possible (more reliable)
        - Keep validate=True for security
        - Always import needed modules at top of code
        - End with doc.recompute() to update view
    """
    try:
        command = {
            "type": "execute_code",
            "params": {
                "code": code,
                "validate": validate
            }
        }

        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, send_command_to_freecad(command))
                result = future.result(timeout=60)  # Longer timeout for code execution
        except RuntimeError:
            result = asyncio.run(send_command_to_freecad(command))

        return result

    except Exception as e:
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='FreeCAD MCP Client - Absolute path version')
    parser.add_argument('--host', default='localhost', help='FreeCAD server host')
    parser.add_argument('--port', type=int, default=9876, help='FreeCAD server port')

    args = parser.parse_args()

    # Use lowercase variable names to avoid constant redefinition warnings
    global FREECAD_HOST, FREECAD_PORT
    freecad_host = args.host
    freecad_port = args.port
    FREECAD_HOST = freecad_host
    FREECAD_PORT = freecad_port

    print(f"FreeCAD MCP client starting")
    print(f"Connecting to: {FREECAD_HOST}:{FREECAD_PORT}")


    # Start MCP server
    mcp.run()

if __name__ == "__main__":
    main()