# FreeCAD MCP API Reference

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Authentication & Connection](#authentication--connection)
- [Error Handling](#error-handling)
- [API Categories](#api-categories)
  - [Macro Management](#macro-management)
  - [Document Management](#document-management)
  - [Object Management](#object-management)
  - [Part Design](#part-design)
  - [Export Operations](#export-operations)
  - [View Management](#view-management)
  - [Measurement & Analysis](#measurement--analysis)
- [Best Practices](#best-practices)
- [Example Workflows](#example-workflows)

## Overview

The FreeCAD MCP API provides programmatic access to FreeCAD through the Model Control Protocol (MCP). It enables automation of CAD operations, macro execution, and model generation through a client-server architecture.

**Architecture:**
- **Server**: Runs inside FreeCAD (`freecad_mcp_server.py`), listens on `localhost:9876`
- **Client**: Python client (`freecad_mcp_client.py`) using `stdio` or TCP communication
- **Protocol**: JSON-based command/response structure

**Supported Communication Modes:**
- **stdio**: For MCP-compatible tools (Claude Desktop, Claude Code, Cursor)
- **TCP**: For direct socket communication on port 9876

## Quick Start

### Setup

```bash
# macOS
cd ~/Library/Application\ Support/FreeCAD/Mod/FreeCAD-MCP
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install mcp-server httpx

# Windows
cd D:\FreeCAD\Mod\FreeCAD-MCP
uv venv .venv --python 3.12
.venv\Scripts\activate
uv pip install mcp-server httpx

# Linux
cd ~/.local/share/FreeCAD/Mod/FreeCAD-MCP
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install mcp-server httpx
```

### Start Server

1. Open FreeCAD
2. Switch to "FreeCAD MCP" workbench
3. Click "FreeCAD_MCP_Show" to open control panel
4. Click "Start Server"

### First API Call

```python
from freecad_mcp_client import create_macro

# Create a new macro
result = create_macro("my_first_macro", "basic")
print(result)
# Output: {"result": "success", "message": "Macro file created successfully: ..."}
```

## Authentication & Connection

### Connection Setup

No authentication required for local connections. The server binds to `localhost:9876` by default.

**Security Notes:**
- Server only accepts local connections
- Code validation prevents dangerous operations
- Allowed modules: `FreeCAD`, `Part`, `Draft`, `Sketcher`, `PartDesign`, `math`, `numpy`, `Mesh`, `Arch`, `TechDraw`, `Spreadsheet`, `Import`
- Blocked operations: `__import__`, `eval`, `exec`, `open`, `compile`, file system access

### Client Configuration

**For Claude Desktop/Code** (add to `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "freecad": {
      "type": "stdio",
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/freecad_mcp_client.py"],
      "timeout": 60
    }
  }
}
```

**For Direct Python Usage**:

```python
import asyncio
from freecad_mcp_client import send_command_to_freecad

async def call_api():
    command = {"type": "list_documents", "params": {}}
    result = await send_command_to_freecad(command)
    return result

result = asyncio.run(call_api())
```

## Error Handling

All API responses follow this structure:

**Success Response:**
```json
{
  "result": "success",
  "message": "Operation completed",
  "data": { ... }
}
```

**Error Response:**
```json
{
  "result": "error",
  "message": "Error description",
  "traceback": "Full Python traceback"
}
```

### Common Error Codes

| Error Type | Cause | Solution |
|------------|-------|----------|
| Connection Failed | Server not running | Start FreeCAD MCP server |
| Module Not Allowed | Importing restricted module | Use allowed modules only |
| Invalid Macro Name | Invalid characters | Use only letters, numbers, underscores, hyphens |
| File Not Found | Macro path incorrect | Check macro path, use absolute paths |
| No Active Document | Document not open | Create or open a document first |
| Syntax Error | Invalid Python code | Validate code syntax |

### Error Handling Pattern

```python
from freecad_mcp_client import run_macro

try:
    result = run_macro("my_macro.FCMacro")
    if result["result"] == "error":
        print(f"Error: {result['message']}")
        print(f"Traceback: {result.get('traceback', 'N/A')}")
    else:
        print(f"Success: {result['message']}")
except Exception as e:
    print(f"Client error: {str(e)}")
```

## API Categories

---

## Macro Management

### create_macro

Creates a new FreeCAD macro file.

**Function Signature:**
```python
def create_macro(macro_name: str, template_type: str = "default") -> Dict[str, Any]
```

**Parameters:**
- `macro_name` (str, required): Macro file name (only letters, numbers, underscores, hyphens)
- `template_type` (str, optional): Template type
  - `"default"`: Basic comment header
  - `"basic"`: Imports FreeCAD and GUI
  - `"part"`: Includes Part module
  - `"sketch"`: Includes Sketcher module

**Returns:**
```json
{
  "result": "success",
  "message": "Macro file created successfully: /path/to/macro.FCMacro"
}
```

**Example:**
```python
from freecad_mcp_client import create_macro

# Create a part design macro
result = create_macro("parametric_gear", "part")
print(result)
```

**Common Errors:**
- Invalid macro name characters: Returns error with allowed character list
- File already exists: Overwrites existing file

---

### update_macro

Updates the content of an existing macro file.

**Function Signature:**
```python
def update_macro(macro_name: str, code: str) -> Dict[str, Any]
```

**Parameters:**
- `macro_name` (str, required): Macro file name (without .FCMacro extension)
- `code` (str, required): Python code content

**Returns:**
```json
{
  "result": "success",
  "message": "Macro file updated successfully: /path/to/macro.FCMacro"
}
```

**Code Normalization:**
The function automatically adds missing imports:
- `import FreeCAD as App`
- `import FreeCADGui as Gui`
- `import Part`
- `import math`

**Example:**
```python
from freecad_mcp_client import update_macro

code = """
# Create a cylinder
radius = 10
height = 20
cylinder = Part.makeCylinder(radius, height)
Part.show(cylinder)
"""

result = update_macro("my_cylinder", code)
```

**Common Errors:**
- File not found: Returns error with expected path
- Invalid code syntax: Returns syntax error details

---

### run_macro

Executes a FreeCAD macro file.

**Function Signature:**
```python
def run_macro(macro_path: str, params: Dict[str, Any] = None) -> Dict[str, Any]
```

**Parameters:**
- `macro_path` (str, required): Macro file path (absolute or relative)
  - Absolute: `/full/path/to/macro.FCMacro`
  - Relative: `macro_name` or `macro_name.FCMacro`
- `params` (dict, optional): Parameters to inject into macro
  - `doc_name`: Document name to use/create
  - Custom parameters accessible in macro code

**Path Resolution:**
1. If absolute path: Use directly
2. If relative path:
   - Search in FreeCAD macro directory
   - Auto-append `.FCMacro` extension if missing
   - Search in current working directory
   - Search in project directory

**Returns:**
```json
{
  "result": "success",
  "message": "Macro executed successfully in document MyDoc",
  "document": "MyDoc"
}
```

**Parameter Injection:**
Parameters are injected as Python variables at the top of the macro:
```python
# User calls: run_macro("gear.FCMacro", {"radius": 15, "teeth": 20})
# Macro receives:
radius = 15
teeth = 20

# Original macro code follows...
```

**Example:**
```python
from freecad_mcp_client import run_macro

# Simple execution
result = run_macro("gear.FCMacro")

# With parameters
result = run_macro("parametric_gear.FCMacro", {
    "radius": 25,
    "teeth": 30,
    "height": 10,
    "doc_name": "GearAssembly"
})
print(f"Created in document: {result['document']}")
```

**Automatic Post-Execution:**
- Document recompute
- View adjusted to axonometric
- Zoom to fit all objects

**Common Errors:**
- Macro not found: Lists searched paths
- Syntax error in macro: Returns traceback
- Runtime error: Returns execution traceback
- No GUI available: Returns error (requires FreeCAD GUI mode)

---

### validate_macro_code

Validates macro code syntax and security.

**Function Signature:**
```python
def validate_macro_code(macro_name: str = None, code: str = None) -> Dict[str, Any]
```

**Parameters:**
- `macro_name` (str, optional): Macro file name to validate
- `code` (str, optional): Code string to validate
- Note: Provide either `macro_name` or `code`, not both

**Returns:**
```json
{
  "result": "success",
  "message": "Macro code validation successful"
}
```

**Validation Checks:**
1. Syntax validation using Python AST parser
2. Module import restrictions
3. Dangerous built-in detection (`eval`, `exec`, `open`, etc.)
4. Attribute access restrictions (no `__dict__`, `__globals__`, etc.)

**Example:**
```python
from freecad_mcp_client import validate_macro_code

# Validate file
result = validate_macro_code(macro_name="my_macro")

# Validate code string
code = """
import Part
cylinder = Part.makeCylinder(10, 20)
Part.show(cylinder)
"""
result = validate_macro_code(code=code)

if result["result"] == "error":
    print(f"Validation failed: {result['message']}")
```

**Common Errors:**
- Syntax error: Returns line number and description
- Forbidden import: Lists allowed modules
- Dangerous operation: Specifies blocked function/attribute

---

## Document Management

### list_documents

Lists all open FreeCAD documents.

**Function Signature:**
```python
def list_documents() -> Dict[str, Any]
```

**Parameters:** None

**Returns:**
```json
{
  "result": "success",
  "documents": [
    {
      "name": "Unnamed",
      "label": "Unnamed",
      "object_count": 5,
      "is_active": true
    },
    {
      "name": "GearAssembly",
      "label": "Gear Assembly",
      "object_count": 12,
      "is_active": false
    }
  ]
}
```

**Example:**
```python
from freecad_mcp_client import list_documents

result = list_documents()
for doc in result["documents"]:
    print(f"{doc['name']}: {doc['object_count']} objects")
```

**Status:** Implemented in client, requires server handler implementation

---

### get_active_document

Gets details about the currently active document.

**Function Signature:**
```python
def get_active_document() -> Dict[str, Any]
```

**Parameters:** None

**Returns:**
```json
{
  "result": "success",
  "document": {
    "name": "GearAssembly",
    "label": "Gear Assembly",
    "object_count": 12,
    "objects": [
      {"name": "Body", "type": "PartDesign::Body", "label": "Body"},
      {"name": "Sketch", "type": "Sketcher::SketchObject", "label": "Sketch"}
    ]
  }
}
```

**Example:**
```python
from freecad_mcp_client import get_active_document

result = get_active_document()
if result["result"] == "success":
    doc = result["document"]
    print(f"Active: {doc['name']} with {doc['object_count']} objects")
```

**Common Errors:**
- No active document: Returns error message

**Status:** Implemented in client, requires server handler implementation

---

### create_document

Creates a new FreeCAD document.

**Function Signature:**
```python
def create_document(name: str) -> Dict[str, Any]
```

**Parameters:**
- `name` (str, required): Document name (only letters, numbers, underscores)

**Returns:**
```json
{
  "result": "success",
  "message": "Document created successfully",
  "document_name": "MyProject"
}
```

**Example:**
```python
from freecad_mcp_client import create_document

result = create_document("GearAssembly")
```

**Common Errors:**
- Invalid name characters: Returns error
- Document already exists: May overwrite or return error

**Status:** Implemented in client, requires server handler implementation

---

### save_document

Saves the active document to a file.

**Function Signature:**
```python
def save_document(filename: str) -> Dict[str, Any]
```

**Parameters:**
- `filename` (str, required): Absolute file path (must end with `.FCStd`)

**Returns:**
```json
{
  "result": "success",
  "message": "Document saved successfully",
  "filepath": "/path/to/document.FCStd"
}
```

**Example:**
```python
from freecad_mcp_client import save_document

result = save_document("/Users/username/Documents/gear_assembly.FCStd")
```

**Common Errors:**
- No active document: Returns error
- Invalid path: Returns error
- Permission denied: Returns error

**Status:** Implemented in client, requires server handler implementation

---

### close_document

Closes a document by name.

**Function Signature:**
```python
def close_document(name: str) -> Dict[str, Any]
```

**Parameters:**
- `name` (str, required): Document name to close

**Returns:**
```json
{
  "result": "success",
  "message": "Document closed successfully"
}
```

**Example:**
```python
from freecad_mcp_client import close_document

result = close_document("GearAssembly")
```

**Common Errors:**
- Document not found: Returns error
- Unsaved changes: May prompt or auto-discard

**Status:** Implemented in client, requires server handler implementation

---

## Object Management

### list_objects

Lists all objects in a document.

**Function Signature:**
```python
def list_objects(document_name: str = None) -> Dict[str, Any]
```

**Parameters:**
- `document_name` (str, optional): Document name (uses active document if not specified)

**Returns:**
```json
{
  "result": "success",
  "objects": [
    {
      "name": "Body",
      "type": "PartDesign::Body",
      "label": "Body",
      "visibility": true
    },
    {
      "name": "Sketch",
      "type": "Sketcher::SketchObject",
      "label": "Sketch001",
      "visibility": true
    },
    {
      "name": "Pad",
      "type": "PartDesign::Pad",
      "label": "Pad",
      "visibility": true
    }
  ]
}
```

**Example:**
```python
from freecad_mcp_client import list_objects

# List objects in active document
result = list_objects()

# List objects in specific document
result = list_objects("GearAssembly")

for obj in result["objects"]:
    print(f"{obj['label']} ({obj['type']})")
```

**Status:** Implemented in client, requires server handler implementation

---

### get_object_properties

Gets detailed properties of an object.

**Function Signature:**
```python
def get_object_properties(object_name: str, document_name: str = None) -> Dict[str, Any]
```

**Parameters:**
- `object_name` (str, required): Name of the object
- `document_name` (str, optional): Document name (uses active document if not specified)

**Returns:**
```json
{
  "result": "success",
  "properties": {
    "name": "Pad",
    "type": "PartDesign::Pad",
    "label": "Pad",
    "placement": {
      "base": [0.0, 0.0, 0.0],
      "rotation": [0.0, 0.0, 0.0, 1.0]
    },
    "shape_info": {
      "volume": 1256.64,
      "surface_area": 942.48,
      "bounding_box": {
        "x_min": -10, "x_max": 10,
        "y_min": -10, "y_max": 10,
        "z_min": 0, "z_max": 20
      }
    },
    "visibility": true
  }
}
```

**Example:**
```python
from freecad_mcp_client import get_object_properties

result = get_object_properties("Pad", "GearAssembly")
props = result["properties"]
print(f"Volume: {props['shape_info']['volume']}")
```

**Status:** Implemented in client, requires server handler implementation

---

### delete_object

Deletes an object from a document.

**Function Signature:**
```python
def delete_object(object_name: str, document_name: str = None) -> Dict[str, Any]
```

**Parameters:**
- `object_name` (str, required): Name of the object to delete
- `document_name` (str, optional): Document name (uses active document if not specified)

**Returns:**
```json
{
  "result": "success",
  "message": "Object deleted successfully"
}
```

**Example:**
```python
from freecad_mcp_client import delete_object

result = delete_object("Sketch001")
```

**Common Errors:**
- Object not found: Returns error
- Object has dependencies: May return error or cascade delete

**Status:** Implemented in client, requires server handler implementation

---

## Part Design

**Note:** Part design operations are currently implemented through macro execution. Below are recommended macro patterns for common operations.

### create_body

Creates a new PartDesign Body.

**Macro Pattern:**
```python
# Create via macro
code = """
import FreeCAD as App
import PartDesign

doc = App.ActiveDocument
body = doc.addObject('PartDesign::Body', 'Body')
doc.recompute()
"""

from freecad_mcp_client import update_macro, run_macro
update_macro("create_body", code)
run_macro("create_body.FCMacro")
```

---

### create_sketch

Creates a sketch on a body or face.

**Macro Pattern:**
```python
code = """
import FreeCAD as App
import Sketcher

doc = App.ActiveDocument
body = doc.getObject('Body')

# Create sketch on XY plane
sketch = doc.addObject('Sketcher::SketchObject', 'Sketch')
sketch.Support = (body, [''])
sketch.MapMode = 'FlatFace'
doc.recompute()
"""

update_macro("create_sketch", code)
run_macro("create_sketch.FCMacro")
```

---

### add_geometry

Adds geometric elements to a sketch.

**Circle:**
```python
code = """
import FreeCAD as App
from FreeCAD import Vector

doc = App.ActiveDocument
sketch = doc.getObject('Sketch')

# Add circle at origin with radius 10
sketch.addGeometry(Part.Circle(Vector(0, 0, 0), Vector(0, 0, 1), 10))
doc.recompute()
"""
```

**Rectangle:**
```python
code = """
# Add rectangle
sketch.addGeometry(Part.LineSegment(Vector(-10, -10, 0), Vector(10, -10, 0)))
sketch.addGeometry(Part.LineSegment(Vector(10, -10, 0), Vector(10, 10, 0)))
sketch.addGeometry(Part.LineSegment(Vector(10, 10, 0), Vector(-10, 10, 0)))
sketch.addGeometry(Part.LineSegment(Vector(-10, 10, 0), Vector(-10, -10, 0)))
"""
```

**Line:**
```python
code = """
# Add line
sketch.addGeometry(Part.LineSegment(Vector(0, 0, 0), Vector(10, 10, 0)))
"""
```

**Arc:**
```python
code = """
# Add arc
import math
arc = Part.ArcOfCircle(
    Part.Circle(Vector(0, 0, 0), Vector(0, 0, 1), 10),
    0, math.pi/2  # Start angle, end angle
)
sketch.addGeometry(arc)
"""
```

---

### add_constraint

Adds constraints to sketch geometry.

**Macro Pattern:**
```python
code = """
import Sketcher

doc = App.ActiveDocument
sketch = doc.getObject('Sketch')

# Distance constraint
sketch.addConstraint(Sketcher.Constraint('Distance', 0, 10.0))

# Coincident constraint
sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 2, 1, 1))

# Horizontal constraint
sketch.addConstraint(Sketcher.Constraint('Horizontal', 0))

# Vertical constraint
sketch.addConstraint(Sketcher.Constraint('Vertical', 1))

# Radius constraint
sketch.addConstraint(Sketcher.Constraint('Radius', 0, 15.0))

doc.recompute()
"""
```

---

### extrude_sketch

Creates a pad (extrusion) from a sketch.

**Macro Pattern:**
```python
code = """
import PartDesign

doc = App.ActiveDocument
body = doc.getObject('Body')
sketch = doc.getObject('Sketch')

# Create pad
pad = doc.addObject('PartDesign::Pad', 'Pad')
pad.Profile = sketch
pad.Length = 20.0
body.addObject(pad)
doc.recompute()
"""
```

**With Parameters:**
```python
from freecad_mcp_client import run_macro

result = run_macro("extrude.FCMacro", {
    "length": 25.0,
    "reversed": False
})
```

---

### revolve_sketch

Creates a revolution from a sketch.

**Macro Pattern:**
```python
code = """
import PartDesign
from FreeCAD import Vector

doc = App.ActiveDocument
body = doc.getObject('Body')
sketch = doc.getObject('Sketch')

# Create revolution
revolution = doc.addObject('PartDesign::Revolution', 'Revolution')
revolution.Profile = sketch
revolution.ReferenceAxis = (sketch, ['V_Axis'])
revolution.Angle = 360.0
body.addObject(revolution)
doc.recompute()
"""
```

---

### pocket_sketch

Creates a pocket (cut) from a sketch.

**Macro Pattern:**
```python
code = """
import PartDesign

doc = App.ActiveDocument
body = doc.getObject('Body')
sketch = doc.getObject('Sketch')

# Create pocket
pocket = doc.addObject('PartDesign::Pocket', 'Pocket')
pocket.Profile = sketch
pocket.Length = 10.0
body.addObject(pocket)
doc.recompute()
"""
```

---

### create_fillet

Creates fillets on edges.

**Macro Pattern:**
```python
code = """
import PartDesign

doc = App.ActiveDocument
body = doc.getObject('Body')
pad = doc.getObject('Pad')

# Create fillet
fillet = doc.addObject('PartDesign::Fillet', 'Fillet')
fillet.Base = (pad, ['Edge1', 'Edge2'])
fillet.Radius = 2.0
body.addObject(fillet)
doc.recompute()
"""
```

---

### create_chamfer

Creates chamfers on edges.

**Macro Pattern:**
```python
code = """
import PartDesign

doc = App.ActiveDocument
body = doc.getObject('Body')
pad = doc.getObject('Pad')

# Create chamfer
chamfer = doc.addObject('PartDesign::Chamfer', 'Chamfer')
chamfer.Base = (pad, ['Edge1', 'Edge2'])
chamfer.Size = 2.0
body.addObject(chamfer)
doc.recompute()
"""
```

---

### patterns

**Linear Pattern:**
```python
code = """
import PartDesign

doc = App.ActiveDocument
body = doc.getObject('Body')
feature = doc.getObject('Pocket')

# Create linear pattern
pattern = doc.addObject('PartDesign::LinearPattern', 'LinearPattern')
pattern.Originals = [feature]
pattern.Direction = (doc.getObject('Sketch'), ['H_Axis'])
pattern.Length = 100
pattern.Occurrences = 5
body.addObject(pattern)
doc.recompute()
"""
```

**Polar Pattern:**
```python
code = """
import PartDesign

doc = App.ActiveDocument
body = doc.getObject('Body')
feature = doc.getObject('Pocket')

# Create polar pattern
pattern = doc.addObject('PartDesign::PolarPattern', 'PolarPattern')
pattern.Originals = [feature]
pattern.Axis = (doc.getObject('Sketch'), ['N_Axis'])
pattern.Angle = 360
pattern.Occurrences = 8
body.addObject(pattern)
doc.recompute()
"""
```

---

## Export Operations

### export_stl

Exports an object as STL file (3D printing format).

**Function Signature:**
```python
def export_stl(object_name: str, filepath: str, mesh_deviation: float = 0.1) -> Dict[str, Any]
```

**Parameters:**
- `object_name` (str, required): Name of object to export
- `filepath` (str, required): Absolute output path (auto-appends `.stl`)
- `mesh_deviation` (float, optional): Mesh quality (0.01-1.0, lower=finer)

**Returns:**
```json
{
  "result": "success",
  "message": "STL exported successfully",
  "filepath": "/path/to/output.stl"
}
```

**Example:**
```python
from freecad_mcp_client import export_stl

# Export with default quality
result = export_stl("Body", "/Users/username/Desktop/gear.stl")

# Export with high quality (fine mesh)
result = export_stl("Body", "/Users/username/Desktop/gear_hq.stl", mesh_deviation=0.01)
```

**Status:** Implemented in client, requires server handler implementation

---

### export_step

Exports objects as STEP file (CAD interchange format).

**Function Signature:**
```python
def export_step(filepath: str, objects: str = None) -> Dict[str, Any]
```

**Parameters:**
- `filepath` (str, required): Absolute output path (auto-appends `.step`)
- `objects` (str, optional): Comma-separated object names (exports all if None)

**Returns:**
```json
{
  "result": "success",
  "message": "STEP exported successfully",
  "filepath": "/path/to/output.step"
}
```

**Example:**
```python
from freecad_mcp_client import export_step

# Export all objects
result = export_step("/Users/username/Desktop/assembly.step")

# Export specific objects
result = export_step("/Users/username/Desktop/parts.step", "Body,Body001,Body002")
```

**Status:** Implemented in client, requires server handler implementation

---

### export_iges

Exports objects as IGES file (legacy CAD format).

**Function Signature:**
```python
def export_iges(filepath: str, objects: str = None) -> Dict[str, Any]
```

**Parameters:**
- `filepath` (str, required): Absolute output path (auto-appends `.iges`)
- `objects` (str, optional): Comma-separated object names (exports all if None)

**Returns:**
```json
{
  "result": "success",
  "message": "IGES exported successfully",
  "filepath": "/path/to/output.iges"
}
```

**Example:**
```python
from freecad_mcp_client import export_iges

result = export_iges("/Users/username/Desktop/model.iges", "Body")
```

**Status:** Implemented in client, requires server handler implementation

---

### export_obj

Exports an object as OBJ file (3D graphics format).

**Function Signature:**
```python
def export_obj(object_name: str, filepath: str, mesh_deviation: float = 0.1) -> Dict[str, Any]
```

**Parameters:**
- `object_name` (str, required): Name of object to export
- `filepath` (str, required): Absolute output path (auto-appends `.obj`)
- `mesh_deviation` (float, optional): Mesh quality (0.01-1.0)

**Returns:**
```json
{
  "result": "success",
  "message": "OBJ exported successfully",
  "filepath": "/path/to/output.obj"
}
```

**Example:**
```python
from freecad_mcp_client import export_obj

result = export_obj("Body", "/Users/username/Desktop/model.obj", 0.05)
```

**Status:** Implemented in client, requires server handler implementation

---

### export_svg

Exports 2D drawing/TechDraw page as SVG.

**Function Signature:**
```python
def export_svg(filepath: str, page_name: str = None) -> Dict[str, Any]
```

**Parameters:**
- `filepath` (str, required): Absolute output path (auto-appends `.svg`)
- `page_name` (str, optional): TechDraw page name (uses first page if None)

**Returns:**
```json
{
  "result": "success",
  "message": "SVG exported successfully",
  "filepath": "/path/to/output.svg"
}
```

**Example:**
```python
from freecad_mcp_client import export_svg

# Export first page
result = export_svg("/Users/username/Desktop/drawing.svg")

# Export specific page
result = export_svg("/Users/username/Desktop/section.svg", "Page001")
```

**Status:** Implemented in client, requires server handler implementation

---

### export_pdf

Exports TechDraw page as PDF.

**Function Signature:**
```python
def export_pdf(filepath: str, page_name: str = None) -> Dict[str, Any]
```

**Parameters:**
- `filepath` (str, required): Absolute output path (auto-appends `.pdf`)
- `page_name` (str, optional): TechDraw page name (uses first page if None)

**Returns:**
```json
{
  "result": "success",
  "message": "PDF exported successfully",
  "filepath": "/path/to/output.pdf"
}
```

**Example:**
```python
from freecad_mcp_client import export_pdf

result = export_pdf("/Users/username/Desktop/drawing.pdf", "Assembly_View")
```

**Status:** Implemented in client, requires server handler implementation

---

## View Management

### set_view

Sets the 3D view orientation.

**Function Signature:**
```python
def set_view(params: Dict[str, Any]) -> Dict[str, Any]
```

**Parameters:**
- `params` (dict, required): View parameters
  - `view_type` (str): View type code
    - `"1"`: Front view
    - `"2"`: Top view
    - `"3"`: Right view
    - `"7"`: Isometric/axonometric view

**Returns:**
```json
{
  "result": "success",
  "view_name": "isometric"
}
```

**Example:**
```python
from freecad_mcp_client import set_view

# Set to isometric view
result = set_view({"view_type": "7"})

# Set to front view
result = set_view({"view_type": "1"})
```

**Common Errors:**
- No GUI available: Returns error
- No active view: Returns error
- Invalid view type: Returns error with valid options

---

### set_camera_position

**Status:** Not yet implemented. Use macro pattern:

```python
code = """
import FreeCADGui as Gui
from FreeCAD import Vector

view = Gui.ActiveDocument.ActiveView
camera = view.getCameraNode()

# Set camera position
camera.position.setValue(100, 100, 100)
camera.pointAt(Vector(0, 0, 0), Vector(0, 0, 1))

Gui.updateGui()
"""
```

---

### zoom_to_fit

**Status:** Automatically called after `run_macro`. For manual use:

```python
code = """
import FreeCADGui as Gui

view = Gui.ActiveDocument.ActiveView
view.fitAll()
Gui.updateGui()
"""
```

---

### capture_screenshot

**Status:** Not yet implemented. Use macro pattern:

```python
code = """
import FreeCADGui as Gui

view = Gui.ActiveDocument.ActiveView
view.saveImage('/path/to/screenshot.png', 1920, 1080, 'White')
"""
```

---

### set_render_style

**Status:** Not yet implemented. Use macro pattern:

```python
code = """
import FreeCADGui as Gui

view = Gui.ActiveDocument.ActiveView

# Available styles: "Flat Lines", "Shaded", "Wireframe", "Points", "Hidden Line"
view.setAnimationEnabled(False)
view.setRenderStyle("Flat Lines")
Gui.updateGui()
"""
```

---

## Measurement & Analysis

**Note:** Measurement and analysis operations are currently implemented through macro execution.

### get_bounding_box

**Macro Pattern:**
```python
code = """
import FreeCAD as App

doc = App.ActiveDocument
obj = doc.getObject('Body')

bbox = obj.Shape.BoundBox
result = {
    'x_min': bbox.XMin, 'x_max': bbox.XMax,
    'y_min': bbox.YMin, 'y_max': bbox.YMax,
    'z_min': bbox.ZMin, 'z_max': bbox.ZMax,
    'x_length': bbox.XLength,
    'y_length': bbox.YLength,
    'z_length': bbox.ZLength
}

print(f"Bounding Box: {result}")
"""
```

---

### measure_distance

**Macro Pattern:**
```python
code = """
from FreeCAD import Vector

point1 = Vector(0, 0, 0)
point2 = Vector(10, 10, 10)

distance = point1.distanceToPoint(point2)
print(f"Distance: {distance}")
"""
```

---

### get_volume

**Macro Pattern:**
```python
code = """
import FreeCAD as App

doc = App.ActiveDocument
obj = doc.getObject('Body')

if hasattr(obj.Shape, 'Volume'):
    volume = obj.Shape.Volume
    print(f"Volume: {volume} mm³")
else:
    print("Object has no volume")
"""
```

---

### get_surface_area

**Macro Pattern:**
```python
code = """
import FreeCAD as App

doc = App.ActiveDocument
obj = doc.getObject('Body')

if hasattr(obj.Shape, 'Area'):
    area = obj.Shape.Area
    print(f"Surface Area: {area} mm²")
else:
    print("Object has no surface area")
"""
```

---

### get_center_of_mass

**Macro Pattern:**
```python
code = """
import FreeCAD as App

doc = App.ActiveDocument
obj = doc.getObject('Body')

if hasattr(obj.Shape, 'CenterOfMass'):
    com = obj.Shape.CenterOfMass
    print(f"Center of Mass: X={com.x}, Y={com.y}, Z={com.z}")
else:
    print("Cannot compute center of mass")
"""
```

---

### analyze_shape

**Macro Pattern:**
```python
code = """
import FreeCAD as App
import Part

doc = App.ActiveDocument
obj = doc.getObject('Body')
shape = obj.Shape

analysis = {
    'is_valid': shape.isValid(),
    'is_closed': shape.isClosed(),
    'is_null': shape.isNull(),
    'volume': shape.Volume if hasattr(shape, 'Volume') else 0,
    'area': shape.Area if hasattr(shape, 'Area') else 0,
    'num_faces': len(shape.Faces),
    'num_edges': len(shape.Edges),
    'num_vertices': len(shape.Vertexes),
    'shape_type': shape.ShapeType
}

print(f"Shape Analysis: {analysis}")
"""
```

---

## Best Practices

### 1. Error Handling

Always check response status:
```python
result = run_macro("my_macro.FCMacro")
if result["result"] != "success":
    print(f"Error: {result['message']}")
    return
```

### 2. Path Management

Use absolute paths for file operations:
```python
import os
output_path = os.path.abspath(os.path.expanduser("~/Desktop/model.stl"))
export_stl("Body", output_path)
```

### 3. Parameter Validation

Validate parameters before API calls:
```python
import re

def is_valid_macro_name(name):
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))

macro_name = "my-gear"
if not is_valid_macro_name(macro_name):
    print("Invalid macro name")
else:
    create_macro(macro_name)
```

### 4. Code Normalization

Let the client normalize imports:
```python
# Don't manually add imports
code = """
import FreeCAD as App
import Part
# ...
"""

# Just write your logic, imports are auto-added
code = """
cylinder = Part.makeCylinder(10, 20)
Part.show(cylinder)
"""
update_macro("cylinder", code)
```

### 5. Parametric Macros

Design macros with parameters:
```python
# gear.FCMacro
code = """
# Parameters (injected by run_macro)
# radius, teeth, height

import Part
import math

# Generate gear geometry
gear = Part.makeCylinder(radius, height)
Part.show(gear)
"""

# Run with different parameters
run_macro("gear.FCMacro", {"radius": 20, "teeth": 24, "height": 10})
run_macro("gear.FCMacro", {"radius": 30, "teeth": 36, "height": 15})
```

### 6. Batch Operations

Use loops for batch processing:
```python
models = [
    ("gear", {"radius": 10}),
    ("shaft", {"length": 50}),
    ("housing", {"width": 100})
]

for macro_name, params in models:
    result = run_macro(f"{macro_name}.FCMacro", params)
    if result["result"] == "success":
        print(f"Created {macro_name}")
```

### 7. Server Health Checks

Check server availability:
```python
from freecad_mcp_client import get_report

try:
    result = get_report()
    if result["result"] == "success":
        print("Server is running")
except Exception as e:
    print(f"Server not available: {e}")
```

### 8. Logging

Monitor operations via logs:
```python
import os
import platform

# Locate log file
if platform.system() == "Windows":
    log_path = os.path.join(os.environ['TEMP'], "freecad_mcp_log.txt")
else:
    log_path = "/tmp/freecad_mcp_log.txt"

# Read recent logs
with open(log_path, 'r') as f:
    logs = f.readlines()
    print("Recent logs:", logs[-10:])
```

---

## Example Workflows

### Workflow 1: Create Parametric Gear

```python
from freecad_mcp_client import create_macro, update_macro, run_macro, export_stl

# Step 1: Create macro
create_macro("parametric_gear", "part")

# Step 2: Write gear generation code
code = """
import math

# Parameters: radius, teeth, height (injected by run_macro)

# Create basic gear shape (simplified)
gear = Part.makeCylinder(radius, height)

# Position and display
gear.Placement.Base = Vector(0, 0, 0)
Part.show(gear, 'Gear')
"""

update_macro("parametric_gear", code)

# Step 3: Generate gear with different sizes
sizes = [
    {"radius": 20, "teeth": 20, "height": 10, "doc_name": "SmallGear"},
    {"radius": 30, "teeth": 30, "height": 15, "doc_name": "MediumGear"},
    {"radius": 40, "teeth": 40, "height": 20, "doc_name": "LargeGear"}
]

for params in sizes:
    result = run_macro("parametric_gear.FCMacro", params)
    if result["result"] == "success":
        # Export to STL
        doc_name = params["doc_name"]
        export_stl("Gear", f"/Users/username/Desktop/{doc_name}.stl", 0.05)
        print(f"Created and exported {doc_name}")
```

---

### Workflow 2: Analyze Part Properties

```python
from freecad_mcp_client import run_macro, update_macro

# Create analysis macro
analysis_code = """
import FreeCAD as App

doc = App.ActiveDocument
obj = doc.getObject('Body')

if obj and hasattr(obj, 'Shape'):
    shape = obj.Shape

    results = {
        'volume': shape.Volume,
        'surface_area': shape.Area,
        'center_of_mass': {
            'x': shape.CenterOfMass.x,
            'y': shape.CenterOfMass.y,
            'z': shape.CenterOfMass.z
        },
        'bounding_box': {
            'x_length': shape.BoundBox.XLength,
            'y_length': shape.BoundBox.YLength,
            'z_length': shape.BoundBox.ZLength
        }
    }

    # Write results to file
    import json
    with open('/tmp/analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("Analysis complete")
else:
    print("No Body object found")
"""

update_macro("analyze_part", analysis_code)
run_macro("analyze_part.FCMacro")

# Read results
import json
with open('/tmp/analysis_results.json', 'r') as f:
    results = json.load(f)
    print(f"Volume: {results['volume']:.2f} mm³")
    print(f"Surface Area: {results['surface_area']:.2f} mm²")
```

---

### Workflow 3: Batch Export Models

```python
from freecad_mcp_client import run_macro, export_stl, export_step, close_document

models = ["gear", "shaft", "housing", "bearing"]

for model in models:
    # Generate model
    result = run_macro(f"{model}.FCMacro", {"doc_name": model.capitalize()})

    if result["result"] == "success":
        doc_name = result["document"]

        # Export to multiple formats
        export_stl("Body", f"/Users/username/Desktop/{model}.stl", 0.05)
        export_step(f"/Users/username/Desktop/{model}.step", "Body")

        # Close document to free memory
        close_document(doc_name)

        print(f"Processed {model}")
```

---

### Workflow 4: Interactive Design with Claude

```text
User: Create a parametric flange with 6 bolt holes

Claude: I'll create a parametric flange macro for you.

[Creates macro with parameters: outer_radius, inner_radius, thickness, bolt_count, bolt_radius]

User: Generate flange with outer radius 50mm, inner radius 20mm, 8 holes

Claude: Executing with your parameters...

[Runs macro, displays result, exports STL]

User: Increase thickness to 15mm

Claude: Updating and regenerating...

[Modifies parameters, re-runs macro]
```

Implementation:
```python
# Claude internally executes:
from freecad_mcp_client import create_macro, update_macro, run_macro

# Create flange macro with full parametric code
# (Implementation details in macro)

# Run with user parameters
result = run_macro("flange.FCMacro", {
    "outer_radius": 50,
    "inner_radius": 20,
    "thickness": 15,
    "bolt_count": 8,
    "bolt_radius": 4,
    "doc_name": "CustomFlange"
})
```

---

### Workflow 5: CAD Drawing Recognition

```text
User: [Uploads image of technical drawing]

User: Recreate this table in FreeCAD

Claude: [Analyzes drawing, generates macro]

[Creates macro with detected dimensions]
[Executes macro, displays result]
[Exports model]
```

Implementation:
```python
# Pseudo-code (requires external vision analysis)

# 1. Extract dimensions from image
dimensions = analyze_drawing(image_path)

# 2. Generate macro code
code = generate_table_macro(dimensions)

# 3. Create and run macro
update_macro("table_from_drawing", code)
result = run_macro("table_from_drawing.FCMacro")

# 4. Export result
export_step("/Users/username/Desktop/table.step")
```

---

## API Implementation Status

| Category | Tool | Client | Server | Status |
|----------|------|--------|--------|--------|
| **Macro** | create_macro | ✅ | ✅ | Complete |
| | update_macro | ✅ | ✅ | Complete |
| | run_macro | ✅ | ✅ | Complete |
| | validate_macro_code | ✅ | ✅ | Complete |
| **Document** | list_documents | ✅ | ❌ | Client Only |
| | get_active_document | ✅ | ❌ | Client Only |
| | create_document | ✅ | ❌ | Client Only |
| | save_document | ✅ | ❌ | Client Only |
| | close_document | ✅ | ❌ | Client Only |
| **Object** | list_objects | ✅ | ❌ | Client Only |
| | get_object_properties | ✅ | ❌ | Client Only |
| | delete_object | ✅ | ❌ | Client Only |
| **Export** | export_stl | ✅ | ❌ | Client Only |
| | export_step | ✅ | ❌ | Client Only |
| | export_iges | ✅ | ❌ | Client Only |
| | export_obj | ✅ | ❌ | Client Only |
| | export_svg | ✅ | ❌ | Client Only |
| | export_pdf | ✅ | ❌ | Client Only |
| **View** | set_view | ✅ | ✅ | Complete |
| | get_report | ✅ | ✅ | Complete |
| **Part Design** | All operations | Macro | Macro | Via Macros |
| **Analysis** | All operations | Macro | Macro | Via Macros |

**Legend:**
- ✅ Implemented
- ❌ Not Implemented (requires server handler)
- Macro: Implemented via macro execution patterns

---

## Support & Resources

- **GitHub**: [https://github.com/ATOI-Ming/FreeCAD-MCP](https://github.com/ATOI-Ming/FreeCAD-MCP)
- **Issues**: [Bug Tracker](https://github.com/ATOI-Ming/FreeCAD-MCP/issues)
- **FreeCAD Documentation**: [https://wiki.freecad.org](https://wiki.freecad.org)
- **MCP Protocol**: [Model Context Protocol Docs](https://modelcontextprotocol.io)

---

**Last Updated**: 2026-01-14
**Version**: 0.1.0
**License**: MIT
