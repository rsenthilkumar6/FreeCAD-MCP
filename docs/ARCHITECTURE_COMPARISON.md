# Architecture Comparison: neka-nat/freecad-mcp vs Current Implementation

**Date:** 2026-01-14
**Repos Compared:**
- **A:** neka-nat/freecad-mcp (Popular, 9 tools)
- **B:** Current implementation (50+ tools)

---

## Executive Summary

**neka-nat's approach:** Simple, flexible, visual-first (9 tools + execute_code)
**Our approach:** Comprehensive, structured, secure (50+ specific tools)

**Recommendation:** **Merge the best of both** - Add visual feedback, execute_code, and parts library to our comprehensive tool set.

---

## 1. Architecture Comparison

### Communication Protocol

| Aspect | neka-nat (A) | Current (B) | Winner |
|--------|--------------|-------------|--------|
| Protocol | XML-RPC (port 9875) | Raw Socket (port 9876) | **A** |
| Serialization | Built-in | Manual JSON | **A** |
| Standard | Industry standard | Custom | **A** |
| Error Handling | Built-in | Manual | **A** |

**Winner: neka-nat** - XML-RPC is more robust and standard

### Thread Safety

| Aspect | neka-nat (A) | Current (B) | Winner |
|--------|--------------|-------------|--------|
| GUI Thread Safety | Queue pattern | QTimer direct | **A** |
| Request Queue | Yes | No | **A** |
| Response Queue | Yes | No | **A** |
| Race Conditions | Protected | Potential issues | **A** |

**Code Example (neka-nat):**
```python
# RPC server runs in background thread
rpc_request_queue = queue.Queue()
rpc_response_queue = queue.Queue()

def process_gui_tasks():
    while not rpc_request_queue.empty():
        task = rpc_request_queue.get()
        res = task()  # Execute in GUI thread
        if res is not None:
            rpc_response_queue.put(res)
    QtCore.QTimer.singleShot(500, process_gui_tasks)

# Usage
def create_object(self, doc_name, obj_data):
    rpc_request_queue.put(lambda: self._create_object_gui(doc_name, obj))
    res = rpc_response_queue.get()  # Wait for GUI thread result
    return res
```

**Winner: neka-nat** - Much safer threading model

---

## 2. Visual Feedback (CRITICAL DIFFERENCE)

### Screenshot Capability

| Feature | neka-nat (A) | Current (B) | Impact |
|---------|--------------|-------------|--------|
| Auto screenshots | ✅ Every operation | ❌ None | **HUGE** |
| `get_view()` tool | ✅ Dedicated tool | ❌ None | **HUGE** |
| Multiple views | ✅ 9 view types | ❌ None | **HUGE** |
| Base64 encoding | ✅ Yes | ❌ N/A | Medium |
| Token saving | ✅ `--only-text-feedback` | ✅ No images | Low |

**Code Example (neka-nat):**
```python
@mcp.tool()
def create_object(ctx, doc_name, obj_type, obj_name, obj_properties):
    """Create object and return screenshot"""
    freecad = get_freecad_connection()
    res = freecad.create_object(doc_name, obj_data)
    screenshot = freecad.get_active_screenshot()  # Automatic screenshot!

    if res["success"]:
        return [
            TextContent(text=f"Object '{res['object_name']}' created"),
            ImageContent(data=screenshot, mimeType="image/png")  # Visual feedback!
        ]

@mcp.tool()
def get_view(ctx, view_name: Literal["Isometric", "Front", "Top", ...],
            width: int = None, height: int = None):
    """Get screenshot from specific view"""
    screenshot = freecad.get_active_screenshot(view_name, width, height)
    return [ImageContent(data=screenshot, mimeType="image/png")]
```

**Impact:** LLM can **see** what it created, understand spatial relationships, debug visually

**Winner: neka-nat** - This is a GAME CHANGER for LLM autonomy

---

## 3. Tool Philosophy

### Tool Count & Design

| Aspect | neka-nat (A) | Current (B) | Analysis |
|--------|--------------|-------------|----------|
| Total Tools | 9 | 50+ | B has 5× more |
| Philosophy | Generic + Flexible | Specific | Different goals |
| `execute_code` | ✅ Unlimited capability | ❌ None | **A wins flexibility** |
| Type Safety | Less | More | **B wins safety** |
| Documentation | Minimal | Comprehensive | **B wins** |

### Tool List Comparison

**neka-nat (9 tools):**
1. `create_document` - Create document
2. `create_object` - Generic object creation (Part::*, Draft::*, PartDesign::*, Fem::*)
3. `edit_object` - Generic editing
4. `delete_object` - Delete object
5. `execute_code` - **Run arbitrary Python** ⭐
6. `insert_part_from_library` - Use pre-built parts ⭐
7. `get_view` - Screenshot tool ⭐
8. `get_objects` - List objects
9. `get_object` - Get object details
10. `get_parts_list` - Discover parts library ⭐
11. `list_documents` - List documents

**Current (50+ tools):** (Grouped by category)

**Document Management (8):**
- create_document, list_documents, get_active_document
- save_document, close_document
- list_objects, get_object_properties, delete_object

**Part Design (14):**
- create_body, create_sketch
- add_circle, add_rectangle, add_line, add_arc
- add_constraint, extrude_sketch, revolve_sketch, pocket_sketch
- create_fillet, create_chamfer
- create_pattern_linear, create_pattern_polar

**Export (6):**
- export_stl, export_step, export_iges
- export_obj, export_svg, export_pdf

**Measurement (8):**
- get_bounding_box, measure_distance
- get_volume, get_surface_area, get_center_of_mass
- get_mass_properties, check_solid_valid, analyze_shape

**View Management (10):**
- set_camera_position, set_view_direction
- zoom_to_fit, zoom_to_selection, set_perspective
- capture_screenshot, rotate_view, set_render_style
- toggle_axis, set_background_color

**Macro System (6):**
- create_macro, update_macro, run_macro, validate_macro_code
- set_view, get_report

### Flexibility vs Structure

**neka-nat advantage:**
```python
# Want to do something not in the tool list? Just use execute_code!
execute_code("""
import FreeCAD as App
import Part

# Create custom parametric spiral
doc = App.ActiveDocument
t = np.linspace(0, 4*np.pi, 100)
points = [App.Vector(np.cos(t[i])*t[i], np.sin(t[i])*t[i], t[i])
          for i in range(len(t))]
wire = Part.makePolygon(points)
doc.addObject("Part::Feature", "Spiral").Shape = wire
doc.recompute()
""")
```

**Current advantage:**
```python
# Type-safe, validated, documented
create_body("Base")
create_sketch("Base", "Sketch001", "XY")
add_circle("Sketch001", 0, 0, 10)
extrude_sketch("Sketch001", 20)
# Each operation is validated, documented, safe
```

**Winner: TIE** - Both approaches valid for different use cases

---

## 4. Parts Library Integration (CRITICAL)

| Feature | neka-nat (A) | Current (B) | Impact |
|---------|--------------|-------------|--------|
| Parts library | ✅ Full integration | ❌ None | **HUGE** |
| `get_parts_list()` | ✅ Yes | ❌ No | **HUGE** |
| `insert_part` | ✅ Yes | ❌ No | **HUGE** |
| Standard parts | ✅ Bolts, nuts, bearings | ❌ Must create | **HUGE** |

**Code Example (neka-nat):**
```python
# Discover what parts are available
parts = get_parts_list()
# Returns: [
#   "Fasteners/Screws/ISO4017/M6_x_20.FCStd",
#   "Fasteners/Nuts/ISO4032/M6.FCStd",
#   "Bearings/Ball/608.FCStd",
#   ...
# ]

# Insert a standard M6 bolt
insert_part_from_library("Fasteners/Screws/ISO4017/M6_x_20.FCStd")
# Returns: Image of bolt + success message
```

**MCP Prompt (neka-nat):**
```python
@mcp.prompt()
def asset_creation_strategy() -> str:
    return """
When creating content in FreeCAD, ALWAYS:

1. Check parts library FIRST using get_parts_list()
2. If part exists, use insert_part_from_library()
3. Only create from scratch if not in library
4. Use execute_code() for complex/custom operations
"""
```

**Impact:**
- LLM doesn't reinvent the wheel
- Standard parts are correct dimensions
- Huge time savings
- Realistic assemblies

**Winner: neka-nat** - This is critical for real-world CAD

---

## 5. Security & Validation

| Feature | neka-nat (A) | Current (B) | Winner |
|---------|--------------|-------------|--------|
| Code validation | ❌ None | ✅ AST-based | **B** |
| Module whitelist | ❌ None | ✅ Yes | **B** |
| Dangerous builtins | ❌ Allowed | ✅ Blocked | **B** |
| Sandboxing | ❌ No | ✅ Yes | **B** |
| File system access | ❌ Unrestricted | ✅ Restricted | **B** |

**Security Risk (neka-nat):**
```python
# LLM could accidentally (or intentionally) do:
execute_code("""
import os
os.system("rm -rf /")  # DANGEROUS!
""")
# No validation, no restrictions
```

**Security Protection (Current):**
```python
# AST validation blocks:
- __import__, eval, exec, compile
- open, file operations
- os.system, subprocess
- Only whitelisted modules: FreeCAD, Part, Draft, Sketcher, PartDesign, math, numpy
```

**Winner: Current** - Critical for production use

---

## 6. Object Introspection

### Object Serialization

**neka-nat has superior object serialization:**

```python
# serialize.py
def serialize_object(obj):
    """Convert FreeCAD object to dictionary"""
    return {
        "Name": obj.Name,
        "Label": obj.Label,
        "TypeId": obj.TypeId,
        "Properties": {
            prop: serialize_property(getattr(obj, prop))
            for prop in obj.PropertiesList
        },
        "Placement": {
            "Base": {"x": obj.Placement.Base.x, ...},
            "Rotation": {...}
        },
        "Shape": {
            "Volume": obj.Shape.Volume if hasattr(obj, 'Shape') else None,
            "BoundBox": {...}
        },
        "ViewObject": {
            "ShapeColor": obj.ViewObject.ShapeColor,
            "Transparency": obj.ViewObject.Transparency,
        } if hasattr(obj, 'ViewObject') else None
    }
```

**Current implementation:** Limited object introspection

**Winner: neka-nat** - Better object discovery

---

## 7. Packaging & Distribution

| Aspect | neka-nat (A) | Current (B) | Winner |
|--------|--------------|-------------|--------|
| PyPI Package | ✅ `uvx freecad-mcp` | ❌ Manual install | **A** |
| uv.lock | ✅ Yes | ❌ No | **A** |
| Version pinning | ✅ Yes | ❌ No | **A** |
| Easy install | ✅ One command | ❌ Multi-step | **A** |
| FreeCAD addon | ✅ Separate addon dir | ✅ Mod folder | TIE |

**Winner: neka-nat** - Professional packaging

---

## 8. Documentation & Examples

| Aspect | neka-nat (A) | Current (B) | Winner |
|--------|--------------|-------------|--------|
| README demos | ✅ 3 GIFs | ✅ Text | **A** |
| Conversation links | ✅ claude.ai share | ❌ No | **A** |
| API docs | ❌ Minimal | ✅ Comprehensive | **B** |
| Example usage | ✅ In tool docstrings | ✅ docs/API.md | TIE |
| Dev guide | ❌ No | ✅ DEVELOPMENT.md | **B** |

**Winner: TIE** - Different strengths

---

## 9. Key Innovations to Adopt

### From neka-nat:

1. **Visual Feedback (CRITICAL)** ⭐⭐⭐
   - Return screenshots with every operation
   - `get_view()` tool for different perspectives
   - LLM can see what it created

2. **Parts Library Integration** ⭐⭐⭐
   - `get_parts_list()` - discover standard parts
   - `insert_part_from_library()` - use pre-built parts
   - MCP prompt guides LLM to check library first

3. **execute_code() Tool** ⭐⭐
   - Flexibility for operations not in tool set
   - Enables advanced/custom operations
   - Should add WITH validation

4. **XML-RPC Protocol** ⭐⭐
   - More standard than raw sockets
   - Better error handling
   - Built-in serialization

5. **Thread-Safe Queue Pattern** ⭐⭐
   - Prevents GUI threading issues
   - Request/response queues
   - Safer than direct QTimer

6. **Object Serialization** ⭐
   - `serialize_object()` - complete object metadata
   - Better introspection

7. **MCP Prompts** ⭐
   - Guide LLM behavior
   - Asset creation strategy
   - Best practices embedded

8. **--only-text-feedback Flag** ⭐
   - Save tokens when images not needed
   - Good for batch operations

### Keep from Current:

1. **Comprehensive Tool Coverage** ⭐⭐⭐
   - 50+ specific tools
   - Part Design, Measurement, Export
   - Structured operations

2. **Security & Validation** ⭐⭐⭐
   - AST-based code validation
   - Module whitelisting
   - Dangerous builtin blocking

3. **Measurement Tools** ⭐⭐
   - Volume, surface area, mass properties
   - Engineering analysis
   - Quality checks

4. **Export Tools** ⭐⭐
   - STL, STEP, IGES, OBJ, SVG, PDF
   - Multiple format support

5. **View Management** ⭐
   - Camera control, render styles
   - Background color, axis toggle

6. **Documentation** ⭐⭐
   - API.md, DEVELOPMENT.md
   - Comprehensive examples

---

## 10. Recommended Hybrid Architecture

### Phase 1: Quick Wins (1-2 weeks)

**Add visual feedback (HIGHEST PRIORITY):**

```python
# Add to every tool that modifies geometry
@mcp.tool()
def create_body(name: str, document_name: str = None) -> List[TextContent | ImageContent]:
    """Create a PartDesign Body container"""
    # ... existing code ...
    doc.recompute()

    # NEW: Capture screenshot
    screenshot = capture_screenshot_base64()

    return [
        TextContent(text=f"Body '{body.Name}' created"),
        ImageContent(data=screenshot, mimeType="image/png") if screenshot else None
    ]

# Add dedicated view tool
@mcp.tool()
def get_view(view_name: Literal["Isometric", "Front", "Top", ...],
            width: int = None, height: int = None) -> List[ImageContent]:
    """Get screenshot from specific view"""
    # Implement view capture
```

**Add execute_code with validation:**

```python
@mcp.tool()
def execute_code(code: str, validate: bool = True) -> Dict:
    """Execute Python code in FreeCAD (with validation)"""
    if validate:
        is_safe, error_msg = validate_code_safety(code)  # Use existing validation
        if not is_safe:
            return {"result": "error", "message": f"Validation failed: {error_msg}"}

    # Execute safely
    screenshot = capture_screenshot_base64()
    return {
        "result": "success",
        "screenshot": screenshot
    }
```

**Add parts library integration:**

```python
@mcp.tool()
def get_parts_list() -> List[str]:
    """Get list of parts in FreeCAD parts library"""
    # Implement parts library scanning

@mcp.tool()
def insert_part_from_library(relative_path: str) -> Dict:
    """Insert a part from the parts library"""
    # Implement part insertion
```

### Phase 2: Protocol Migration (2-3 weeks)

**Migrate to XML-RPC:**

```python
# Server side (freecad_mcp_server.py)
from xmlrpc.server import SimpleXMLRPCServer

class FreeCADRPC:
    def create_body(self, name, document_name=None):
        # Queue-based execution in GUI thread
        rpc_request_queue.put(lambda: self._create_body_gui(name, document_name))
        res = rpc_response_queue.get()
        return res

# Client side (src/freecad_mcp_client.py)
import xmlrpc.client

class FreeCADConnection:
    def __init__(self, host="localhost", port=9875):
        self.server = xmlrpc.client.ServerProxy(f"http://{host}:{port}")

    def create_body(self, name, document_name=None):
        return self.server.create_body(name, document_name)
```

**Add thread-safe queues:**

```python
rpc_request_queue = queue.Queue()
rpc_response_queue = queue.Queue()

def process_gui_tasks():
    """Process RPC requests in GUI thread"""
    while not rpc_request_queue.empty():
        task = rpc_request_queue.get()
        res = task()
        if res is not None:
            rpc_response_queue.put(res)
    QtCore.QTimer.singleShot(500, process_gui_tasks)
```

### Phase 3: Enhanced Introspection (1-2 weeks)

**Add object serialization:**

```python
def serialize_object(obj):
    """Convert FreeCAD object to comprehensive dict"""
    return {
        "Name": obj.Name,
        "Label": obj.Label,
        "TypeId": obj.TypeId,
        "Properties": {prop: get_property_value(obj, prop) for prop in obj.PropertiesList},
        "Placement": serialize_placement(obj.Placement),
        "Shape": serialize_shape(obj.Shape) if hasattr(obj, 'Shape') else None,
        "ViewObject": serialize_view_object(obj.ViewObject) if hasattr(obj, 'ViewObject') else None
    }
```

### Phase 4: Polish (1 week)

**Add MCP prompts:**

```python
@mcp.prompt()
def design_workflow() -> str:
    return """
FreeCAD MCP Design Workflow:

1. ALWAYS check parts library first with get_parts_list()
2. Use insert_part_from_library() for standard parts (bolts, nuts, bearings)
3. Use specific tools (create_body, create_sketch) for parametric design
4. Use execute_code() ONLY for complex/custom operations
5. Request get_view() to see results from different angles
6. Validate geometry with check_solid_valid() before export
"""
```

**Add --only-text-feedback flag:**

```python
# In client
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-text-feedback", action="store_true")
    args = parser.parse_args()

    global _include_screenshots
    _include_screenshots = not args.only_text_feedback
```

---

## 11. Migration Strategy

### Backward Compatibility

**Option 1: Dual Ports (Recommended)**
- Keep existing socket server on port 9876
- Add new XML-RPC server on port 9875
- Gradual migration, deprecate old port later

**Option 2: Complete Migration**
- Replace socket with XML-RPC
- Breaking change, requires client updates

### Testing Plan

1. **Unit Tests:** Test visual feedback capture
2. **Integration Tests:** Test XML-RPC communication
3. **Security Tests:** Verify validation still works with execute_code
4. **Performance Tests:** Compare screenshot overhead

### Rollout Plan

**Week 1-2:**
- Add screenshot capture infrastructure
- Implement get_view() tool
- Add screenshots to 5-10 most-used tools

**Week 3-4:**
- Implement parts library integration
- Add execute_code with validation
- Add MCP prompts

**Week 5-6:**
- Migrate to XML-RPC (dual port mode)
- Add thread-safe queues
- Comprehensive testing

**Week 7-8:**
- Add object serialization
- Documentation updates
- Performance optimization

---

## 12. Success Metrics

**Visual Feedback Impact:**
- Measure: LLM design success rate increases 2-3×
- Reason: LLM can see and debug visually

**Parts Library Impact:**
- Measure: Time to create assemblies decreases 50%
- Reason: No need to recreate standard parts

**execute_code Impact:**
- Measure: Can handle 90% of custom requests
- Reason: Flexibility for edge cases

**Overall Goal:**
- 5× improvement in LLM autonomous design capability
- Combine flexibility (neka-nat) with comprehensiveness (current)

---

## 13. Final Recommendation

### Adopt from neka-nat (CRITICAL):
1. ⭐⭐⭐ **Visual feedback** - Screenshots with every operation
2. ⭐⭐⭐ **Parts library** - Standard parts integration
3. ⭐⭐ **execute_code** - Flexibility (with validation)
4. ⭐⭐ **XML-RPC** - Better protocol
5. ⭐⭐ **Thread safety** - Queue pattern
6. ⭐ **MCP prompts** - Guide LLM behavior

### Keep from Current (CRITICAL):
1. ⭐⭐⭐ **Security** - Code validation, sandboxing
2. ⭐⭐⭐ **Comprehensive tools** - 50+ specialized operations
3. ⭐⭐ **Measurement** - Engineering analysis
4. ⭐⭐ **Export** - Multiple formats
5. ⭐⭐ **Documentation** - API reference, dev guide

### Result: **Best of Both Worlds**
- neka-nat's simplicity + visual feedback + parts library
- Current's comprehensiveness + security + measurements
- = **Most capable FreeCAD MCP server for LLM autonomy**

---

**Document Version:** 1.0
**Last Updated:** 2026-01-14
**Comparison by:** Claude Sonnet 4.5
**Recommendation:** Merge architectures for v0.3.0
