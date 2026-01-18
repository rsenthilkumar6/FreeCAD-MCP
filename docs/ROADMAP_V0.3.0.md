# FreeCAD MCP v0.3.0 Roadmap

**Theme:** "Visual Feedback + Parts Library + Best of Both Architectures"

**Current:** v0.2.0 (50+ tools, comprehensive but no visual feedback)
**Target:** v0.3.0 (60+ tools, visual feedback, parts library, execute_code)

**Timeline:** 8 weeks
**Expected Impact:** 5× improvement in LLM autonomous design capability

---

## Phase 1: Visual Feedback (Weeks 1-2) 🎯 HIGHEST PRIORITY

### What
Add screenshot capture to enable LLM visual understanding

### Why
- LLMs can **see** what they created
- Debug spatial relationships visually
- Validate geometry visually
- **3× improvement** in design success rate

### Tasks

**1.1 Screenshot Infrastructure (Week 1)**
```python
# Add to freecad_mcp_server.py
def capture_screenshot_base64(view_name="Isometric", width=None, height=None):
    """Capture current view as base64 PNG"""
    import tempfile, base64

    if not App.GuiUp or not Gui.ActiveDocument:
        return None

    view = Gui.ActiveDocument.ActiveView
    if not hasattr(view, 'saveImage'):
        return None  # TechDraw, Spreadsheet don't support

    # Set view
    view_map = {
        "Isometric": view.viewIsometric,
        "Front": view.viewFront,
        "Top": view.viewTop,
        "Right": view.viewRight,
        "Back": view.viewBack,
        "Left": view.viewLeft,
        "Bottom": view.viewBottom,
    }
    if view_name in view_map:
        view_map[view_name]()
    view.fitAll()

    # Capture
    fd, tmp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        if width and height:
            view.saveImage(tmp_path, width, height)
        else:
            view.saveImage(tmp_path)

        with open(tmp_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
```

**1.2 Add to MCP Client (Week 1)**
```python
# src/freecad_mcp_client.py
from mcp.types import ImageContent

def add_screenshot_if_available(response, screenshot_b64, only_text=False):
    """Add screenshot to response"""
    if screenshot_b64 and not only_text:
        response.append(ImageContent(
            type="image",
            data=screenshot_b64,
            mimeType="image/png"
        ))
    return response
```

**1.3 Update Existing Tools (Week 2)**

Modify these tools to return screenshots:
- `create_body` ✅
- `create_sketch` ✅
- `extrude_sketch` ✅
- `create_object` ✅
- `edit_object` ✅
- `delete_object` ✅
- All Part Design tools (14 tools) ✅

**1.4 Add get_view Tool (Week 2)**
```python
@mcp.tool()
def get_view(
    view_name: Literal["Isometric", "Front", "Top", "Right", "Back", "Left", "Bottom"],
    width: int = None,
    height: int = None,
    focus_object: str = None
) -> List[ImageContent | TextContent]:
    """Get screenshot from specific view"""
    # Implementation
```

**1.5 Add --only-text-feedback Flag (Week 2)**
```python
# Main entry point
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-text-feedback", action="store_true")
    args = parser.parse_args()

    global INCLUDE_SCREENSHOTS
    INCLUDE_SCREENSHOTS = not args.only_text_feedback
```

**Success Criteria:**
- ✅ All geometry-modifying tools return screenshots
- ✅ `get_view()` works for 7 standard views
- ✅ Flag to disable screenshots for token savings
- ✅ LLM can see results of operations

---

## Phase 2: Parts Library Integration (Weeks 3-4) 🎯 HIGH PRIORITY

### What
Integrate FreeCAD parts library for standard parts

### Why
- Don't reinvent M6 bolts
- Realistic assemblies
- 50% faster assembly creation
- Standard parts are correct dimensions

### Tasks

**2.1 Parts Library Scanner (Week 3)**
```python
# Add parts_library.py
import os

def get_parts_library_path():
    """Find FreeCAD parts library addon"""
    mod_paths = [
        os.path.join(App.getUserAppDataDir(), "Mod"),
        "/Applications/FreeCAD.app/Contents/Resources/Mod",  # macOS
        # ... other paths
    ]

    for mod_path in mod_paths:
        lib_path = os.path.join(mod_path, "parts_library")
        if os.path.exists(lib_path):
            return lib_path
    return None

def get_parts_list():
    """Recursively scan parts library"""
    lib_path = get_parts_library_path()
    if not lib_path:
        return []

    parts = []
    for root, dirs, files in os.walk(lib_path):
        for file in files:
            if file.endswith(".FCStd"):
                rel_path = os.path.relpath(
                    os.path.join(root, file),
                    lib_path
                )
                parts.append(rel_path)
    return sorted(parts)
```

**2.2 Part Insertion (Week 3)**
```python
def insert_part_from_library(relative_path: str):
    """Insert part from library into active document"""
    lib_path = get_parts_library_path()
    if not lib_path:
        raise Exception("Parts library not found")

    full_path = os.path.join(lib_path, relative_path)
    if not os.path.exists(full_path):
        raise Exception(f"Part not found: {relative_path}")

    # Merge into active document
    doc = App.ActiveDocument
    if not doc:
        raise Exception("No active document")

    import Import
    Import.insert(full_path, doc.Name)
    doc.recompute()
```

**2.3 MCP Tools (Week 4)**
```python
@mcp.tool()
def get_parts_list() -> List[TextContent]:
    """Get list of parts in FreeCAD parts library

    Returns paths like:
        "Fasteners/Screws/ISO4017/M6_x_20.FCStd"
        "Fasteners/Nuts/ISO4032/M6.FCStd"
        "Bearings/Ball/608.FCStd"
    """
    parts = get_parts_list_from_library()
    return [TextContent(type="text", text=json.dumps(parts))]

@mcp.tool()
def insert_part_from_library(relative_path: str) -> List[TextContent | ImageContent]:
    """Insert a standard part from the parts library

    Args:
        relative_path: Path from get_parts_list()

    Example:
        insert_part_from_library("Fasteners/Screws/ISO4017/M6_x_20.FCStd")
    """
    result = insert_part_from_lib(relative_path)
    screenshot = capture_screenshot_base64()

    return [
        TextContent(text=f"Inserted part: {relative_path}"),
        ImageContent(data=screenshot, mimeType="image/png") if screenshot else None
    ]
```

**2.4 MCP Prompt (Week 4)**
```python
@mcp.prompt()
def parts_library_workflow() -> str:
    return """
FreeCAD Parts Library Best Practices:

1. ALWAYS check parts library FIRST with get_parts_list()
2. Search for standard parts: bolts, nuts, washers, bearings, gears
3. Use insert_part_from_library() when part exists
4. Example paths:
   - M6 bolt: "Fasteners/Screws/ISO4017/M6_x_20.FCStd"
   - M6 nut: "Fasteners/Nuts/ISO4032/M6.FCStd"
   - 608 bearing: "Bearings/Ball/608.FCStd"
5. Only create from scratch if NOT in library

Benefits:
- Correct dimensions (ISO/DIN/ANSI standards)
- Faster assembly creation
- Professional results
"""
```

**Success Criteria:**
- ✅ Can discover all parts in library
- ✅ Can insert standard parts (bolts, nuts, bearings)
- ✅ LLM prompted to check library first
- ✅ 50% faster assembly creation

---

## Phase 3: execute_code + Enhanced Flexibility (Weeks 5-6) 🎯 HIGH PRIORITY

### What
Add `execute_code` for operations not in tool set, with validation

### Why
- Flexibility for edge cases
- Custom operations
- Advanced geometry
- Falls back to comprehensive tools when possible

### Tasks

**3.1 execute_code with Validation (Week 5)**
```python
@mcp.tool()
def execute_code(code: str, validate: bool = True) -> List[TextContent | ImageContent]:
    """Execute arbitrary Python code in FreeCAD (with security validation)

    Use this ONLY when specific tools don't cover your needs.
    For common operations, use dedicated tools (create_body, create_sketch, etc.)

    Args:
        code: Python code to execute (has access to FreeCAD, Part, Draft, Sketcher modules)
        validate: Enable security validation (default True, recommended)

    Security:
        - Code is validated using AST analysis
        - Only whitelisted modules allowed: FreeCAD, Part, Draft, Sketcher, PartDesign, math, numpy
        - Dangerous builtins blocked: eval, exec, __import__, open, compile
        - File system access restricted

    Example:
        execute_code('''
import FreeCAD as App
import Part

doc = App.ActiveDocument
box = Part.makeBox(10, 10, 10)
doc.addObject("Part::Feature", "CustomBox").Shape = box
doc.recompute()
        ''')

    Returns:
        Execution result message and screenshot
    """
    try:
        # Validate code safety
        if validate:
            is_safe, error_msg = validate_code_safety(code)
            if not is_safe:
                return [TextContent(
                    type="text",
                    text=f"Security validation failed: {error_msg}\n\n"
                         f"For safety, code must:\n"
                         f"- Only use allowed modules (FreeCAD, Part, Draft, Sketcher, etc.)\n"
                         f"- Not use dangerous builtins (eval, exec, open, etc.)\n"
                         f"- Not access file system outside FreeCAD API"
                )]

        # Execute in safe environment
        import io, contextlib
        output_buffer = io.StringIO()

        safe_globals = {
            "App": App,
            "Gui": Gui,
            "__name__": "__main__"
        }

        # Add whitelisted modules
        import Part, Draft, Sketcher, math
        safe_globals.update({
            "Part": Part,
            "Draft": Draft,
            "Sketcher": Sketcher,
            "math": math
        })

        with contextlib.redirect_stdout(output_buffer):
            exec(code, safe_globals)

        output = output_buffer.getvalue()

        # Recompute and capture
        if App.ActiveDocument:
            App.ActiveDocument.recompute()

        screenshot = capture_screenshot_base64()

        return [
            TextContent(
                type="text",
                text=f"Code executed successfully\n\nOutput:\n{output}"
            ),
            ImageContent(data=screenshot, mimeType="image/png") if screenshot else None
        ]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Execution error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        )]
```

**3.2 Enhanced Object Serialization (Week 6)**
```python
def serialize_object(obj):
    """Convert FreeCAD object to comprehensive dictionary"""
    result = {
        "Name": obj.Name,
        "Label": obj.Label,
        "TypeId": obj.TypeId,
        "Properties": {}
    }

    # Serialize all properties
    for prop in obj.PropertiesList:
        try:
            val = getattr(obj, prop)
            if isinstance(val, App.Vector):
                result["Properties"][prop] = {"x": val.x, "y": val.y, "z": val.z}
            elif isinstance(val, App.Placement):
                result["Properties"][prop] = {
                    "Base": {"x": val.Base.x, "y": val.Base.y, "z": val.Base.z},
                    "Rotation": {
                        "Axis": {"x": val.Rotation.Axis.x, "y": val.Rotation.Axis.y, "z": val.Rotation.Axis.z},
                        "Angle": val.Rotation.Angle
                    }
                }
            elif hasattr(val, '__iter__') and not isinstance(val, str):
                result["Properties"][prop] = list(val)
            else:
                result["Properties"][prop] = val
        except:
            pass

    # Shape info
    if hasattr(obj, 'Shape') and obj.Shape:
        bbox = obj.Shape.BoundBox
        result["Shape"] = {
            "Volume": obj.Shape.Volume if obj.Shape.isClosed() else None,
            "Area": obj.Shape.Area,
            "BoundBox": {
                "XMin": bbox.XMin, "XMax": bbox.XMax,
                "YMin": bbox.YMin, "YMax": bbox.YMax,
                "ZMin": bbox.ZMin, "ZMax": bbox.ZMax
            }
        }

    # View properties
    if hasattr(obj, 'ViewObject') and obj.ViewObject:
        result["ViewObject"] = {
            "Visibility": obj.ViewObject.Visibility,
            "ShapeColor": tuple(obj.ViewObject.ShapeColor)[:3],
            "Transparency": obj.ViewObject.Transparency
        }

    return result
```

**3.3 Update get_object/get_objects (Week 6)**
```python
@mcp.tool()
def get_object(object_name: str, document_name: str = None) -> List[TextContent]:
    """Get comprehensive object information

    Returns detailed object properties, placement, shape data, and view properties
    """
    doc = get_document(document_name)
    obj = doc.getObject(object_name)

    if not obj:
        return [TextContent(text=json.dumps({"error": f"Object '{object_name}' not found"}))]

    return [TextContent(text=json.dumps(serialize_object(obj), indent=2))]
```

**Success Criteria:**
- ✅ execute_code works with validation
- ✅ Can create custom geometry not in tool set
- ✅ Object serialization includes all properties
- ✅ LLM can introspect objects comprehensively

---

## Phase 4: Protocol Migration (Optional, Weeks 7-8)

### What
Migrate from raw sockets to XML-RPC for better standardization

### Why
- Industry standard protocol
- Built-in serialization
- Better error handling
- Thread-safe queues

### Tasks

**4.1 XML-RPC Server (Week 7)**
```python
# freecad_mcp_server.py
from xmlrpc.server import SimpleXMLRPCServer
import queue, threading

rpc_request_queue = queue.Queue()
rpc_response_queue = queue.Queue()

class FreeCADRPC:
    def create_body(self, name, document_name=None):
        rpc_request_queue.put(lambda: self._create_body_gui(name, document_name))
        return rpc_response_queue.get()

    # ... all other methods

def process_gui_tasks():
    """Process RPC requests in GUI thread"""
    while not rpc_request_queue.empty():
        task = rpc_request_queue.get()
        res = task()
        if res is not None:
            rpc_response_queue.put(res)
    QtCore.QTimer.singleShot(500, process_gui_tasks)

def start_rpc_server(host="localhost", port=9875):
    server = SimpleXMLRPCServer((host, port), allow_none=True, logRequests=False)
    server.register_instance(FreeCADRPC())

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    QtCore.QTimer.singleShot(500, process_gui_tasks)
```

**4.2 XML-RPC Client (Week 7)**
```python
# src/freecad_mcp_client.py
import xmlrpc.client

class FreeCADConnection:
    def __init__(self, host="localhost", port=9875):
        self.server = xmlrpc.client.ServerProxy(
            f"http://{host}:{port}",
            allow_none=True
        )

    def ping(self):
        return self.server.ping()

    def create_body(self, name, document_name=None):
        return self.server.create_body(name, document_name)

    # ... all other methods
```

**4.3 Dual Port Mode (Week 8)**
```python
# Support both protocols during migration
# Old: Raw socket on port 9876
# New: XML-RPC on port 9875

# Client auto-detects
def get_connection():
    # Try XML-RPC first
    try:
        conn = XMLRPCConnection(port=9875)
        if conn.ping():
            return conn
    except:
        pass

    # Fall back to socket
    return SocketConnection(port=9876)
```

**Success Criteria:**
- ✅ XML-RPC server runs on port 9875
- ✅ Thread-safe queue pattern
- ✅ Backward compatible (dual port)
- ✅ Smooth migration path

---

## Summary

### Timeline
- **Weeks 1-2:** Visual feedback (screenshots)
- **Weeks 3-4:** Parts library integration
- **Weeks 5-6:** execute_code + enhanced introspection
- **Weeks 7-8:** Protocol migration (optional)

### New Tools Added
1. `get_view()` - Screenshot from specific view
2. `get_parts_list()` - List parts library
3. `insert_part_from_library()` - Insert standard part
4. `execute_code()` - Flexible code execution

### Tools Enhanced (with screenshots)
- All 50+ existing tools return visual feedback

### MCP Prompts Added
1. `parts_library_workflow()` - Guide LLM to use library
2. `design_workflow()` - Best practices

### Success Metrics
- 3× improvement from visual feedback
- 2× improvement from parts library
- Overall: **5× improvement in LLM autonomous design capability**

### Version Comparison
| Feature | v0.2.0 | v0.3.0 |
|---------|--------|--------|
| Tools | 50+ | 60+ |
| Visual feedback | ❌ | ✅ |
| Parts library | ❌ | ✅ |
| execute_code | ❌ | ✅ (validated) |
| Protocol | Socket | XML-RPC |
| Thread safety | QTimer | Queue |
| LLM autonomy | 1× | **5×** |

---

**Document Version:** 1.0
**Last Updated:** 2026-01-14
**Priority:** P0 (Critical for LLM autonomy)
**Estimated Effort:** 8 weeks
