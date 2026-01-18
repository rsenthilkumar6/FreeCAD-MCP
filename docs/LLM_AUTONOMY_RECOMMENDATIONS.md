# LLM Autonomy Recommendations for FreeCAD MCP

**Goal:** Transform FreeCAD MCP from tool collection → autonomous design platform for LLMs

**Date:** 2026-01-14
**Current Version:** v0.2.0 (50+ tools)
**Target:** v0.3.0 (LLM-optimized design system)

---

## Executive Summary

Current implementation provides **execution capability** but lacks **decision-making infrastructure**. LLMs need:

1. **Discovery** - What can I do? What exists?
2. **Context** - What's the current state? What are constraints?
3. **Validation** - Is this geometrically valid? Will it work?
4. **Feedback** - Did it work? What went wrong?
5. **Iteration** - How do I fix/improve it?

**Critical Gap:** 90% of tools are "write-only" - LLM can create but can't query/inspect/validate intelligently.

---

## 1. Discovery & Introspection (P0 - Critical)

### 1.1 Tool Capability Discovery

**Problem:** LLM doesn't know what operations are possible without hardcoded knowledge.

**Solutions:**

```python
# Add to client
@mcp.tool()
def get_available_operations(category: str = None) -> Dict:
    """
    List all available FreeCAD operations with metadata

    Returns:
        {
            "categories": ["PartDesign", "Sketcher", "Part", "Draft", ...],
            "operations": [
                {
                    "name": "create_body",
                    "category": "PartDesign",
                    "description": "Create parametric body container",
                    "parameters": [...],
                    "returns": {...},
                    "example": "...",
                    "prerequisites": ["active_document"],
                    "complexity": "basic"
                }
            ]
        }
    """

@mcp.tool()
def get_workbench_capabilities(workbench: str) -> Dict:
    """Query what a specific workbench can do"""

@mcp.tool()
def suggest_operations(goal: str, context: Dict) -> List[Dict]:
    """
    Given a design goal and current state, suggest next operations

    Example:
        goal = "create threaded hole"
        context = {"has_cylinder": True, "has_sketch": False}
        → Returns: ["create_sketch", "add_circle", "add_helix", "sweep"]
    """
```

### 1.2 Object Type Discovery

**Problem:** LLM can't query "what types of objects exist?"

```python
@mcp.tool()
def list_object_types(document_name: str = None) -> Dict:
    """
    List all object types in document with counts

    Returns:
        {
            "PartDesign::Body": 3,
            "Sketcher::SketchObject": 5,
            "Part::Box": 2,
            "Part::Cylinder": 1
        }
    """

@mcp.tool()
def filter_objects(document_name: str = None,
                   type_filter: str = None,
                   property_filter: Dict = None) -> List[Dict]:
    """
    Filter objects by type or properties

    Examples:
        type_filter = "Sketcher::SketchObject"
        property_filter = {"Volume": {"gt": 1000}, "Valid": True}
    """

@mcp.tool()
def get_object_hierarchy(document_name: str = None) -> Dict:
    """
    Get complete object dependency tree

    Returns tree showing which objects depend on which
    Enables LLM to understand "if I change X, what breaks?"
    """
```

### 1.3 Constraint Discovery

**Problem:** LLM can't query existing constraints on sketches/assemblies

```python
@mcp.tool()
def list_sketch_constraints(sketch_name: str) -> List[Dict]:
    """
    List all constraints on a sketch with details

    Returns:
        [
            {"type": "Coincident", "geometry": [0, 1], "points": [2, 1]},
            {"type": "Radius", "geometry": [2], "value": 10.0},
            {"type": "Horizontal", "geometry": [3]}
        ]
    """

@mcp.tool()
def get_degrees_of_freedom(sketch_name: str) -> Dict:
    """
    Check if sketch is fully constrained

    Returns:
        {
            "dof": 2,
            "status": "under_constrained",
            "missing_constraints": ["need vertical constraint on line 3"],
            "redundant_constraints": []
        }
    """
```

---

## 2. Missing Core Workflows (P0 - Critical)

### 2.1 Assembly Workbench

**Impact:** Cannot build multi-part assemblies autonomously

```python
@mcp.tool()
def create_assembly(name: str) -> Dict:
    """Create assembly container"""

@mcp.tool()
def add_part_to_assembly(assembly_name: str, part_name: str) -> Dict:
    """Add part to assembly"""

@mcp.tool()
def add_assembly_constraint(assembly: str, constraint_type: str,
                           part1: str, part2: str, params: Dict) -> Dict:
    """
    Add constraint between parts

    Types: FixedOrientation, Planar, Axial, Spherical, etc.
    """

@mcp.tool()
def solve_assembly(assembly_name: str) -> Dict:
    """
    Solve assembly constraints

    Returns:
        {"result": "success", "solver_status": "converged", "iterations": 12}
    """

@mcp.tool()
def detect_collisions(assembly_name: str) -> Dict:
    """Check for part interference"""
```

### 2.2 Material Properties & Physics

**Impact:** Cannot do engineering analysis or realistic simulations

```python
@mcp.tool()
def assign_material(object_name: str, material: str,
                   custom_properties: Dict = None) -> Dict:
    """
    Assign material to object

    Materials: Steel, Aluminum, PLA, ABS, Wood, etc.
    Custom: {"density": 7.85, "youngs_modulus": 200000, ...}
    """

@mcp.tool()
def get_material_properties(object_name: str) -> Dict:
    """Get assigned material and properties"""

@mcp.tool()
def calculate_mass_properties_with_material(object_name: str) -> Dict:
    """
    Get realistic mass/inertia based on material

    Returns actual mass instead of volume-based calculation
    """

@mcp.tool()
def estimate_cost(object_name: str, material: str,
                 manufacturing_method: str) -> Dict:
    """
    Estimate manufacturing cost

    Methods: 3d_print, cnc_mill, injection_mold, etc.
    """
```

### 2.3 Advanced Sketcher Constraints

**Impact:** Limited parametric design capability

```python
@mcp.tool()
def add_geometric_constraint(sketch_name: str, constraint_type: str,
                            geometries: List[int], params: Dict = None) -> Dict:
    """
    Add geometric constraints

    Types:
        - Coincident, PointOnObject, Vertical, Horizontal
        - Parallel, Perpendicular, Tangent, Equal
        - Symmetric, PointOnPoint, Block
    """

@mcp.tool()
def add_dimensional_constraint(sketch_name: str, constraint_type: str,
                              geometries: List[int], value: float) -> Dict:
    """
    Add dimensional constraints

    Types: Distance, DistanceX, DistanceY, Radius, Diameter, Angle
    """

@mcp.tool()
def set_constraint_driven(sketch_name: str, constraint_index: int,
                         driven: bool) -> Dict:
    """Mark constraint as driven (reference dimension)"""

@mcp.tool()
def add_expression_constraint(sketch_name: str, constraint_index: int,
                             expression: str) -> Dict:
    """
    Link constraint to expression

    Example: expression = "spreadsheet.width * 2"
    """
```

### 2.4 Import Capabilities

**Impact:** Can't work with existing models

```python
@mcp.tool()
def import_step(filepath: str, document_name: str = None) -> Dict:
    """Import STEP file"""

@mcp.tool()
def import_iges(filepath: str, document_name: str = None) -> Dict:
    """Import IGES file"""

@mcp.tool()
def import_stl(filepath: str, document_name: str = None) -> Dict:
    """Import STL mesh"""

@mcp.tool()
def import_dxf(filepath: str, as_sketch: bool = True) -> Dict:
    """Import DXF as sketch or geometry"""

@mcp.tool()
def analyze_imported_file(filepath: str) -> Dict:
    """
    Analyze file before import

    Returns: format, units, object_count, bounding_box, estimated_complexity
    """
```

---

## 3. Intelligent Validation & Feedback (P1 - High Priority)

### 3.1 Geometry Validation Suite

```python
@mcp.tool()
def validate_for_manufacturing(object_name: str,
                              method: str,
                              params: Dict = None) -> Dict:
    """
    Check if geometry is manufacturable

    Methods: 3d_print, cnc_mill_3axis, injection_mold, sheet_metal

    Returns:
        {
            "valid": False,
            "errors": [
                {"type": "overhang", "angle": 65, "location": [10, 20, 30]},
                {"type": "thin_wall", "thickness": 0.5, "min_required": 1.0}
            ],
            "warnings": ["small hole may be difficult to tap"],
            "suggestions": ["add support at angle > 45°"]
        }
    """

@mcp.tool()
def check_geometry_quality(object_name: str) -> Dict:
    """
    Check for common geometry issues

    Returns:
        {
            "valid": True,
            "warnings": ["self-intersecting face at edge 12"],
            "quality_score": 0.95,
            "issues": {
                "tiny_edges": 2,
                "nearly_degenerate_faces": 0,
                "non_manifold_edges": 0
            }
        }
    """

@mcp.tool()
def suggest_fixes(object_name: str, issue_type: str) -> List[Dict]:
    """
    Suggest automatic fixes for geometry issues

    Returns list of possible fixes with confidence scores
    """
```

### 3.2 Design Rule Checking

```python
@mcp.tool()
def check_design_rules(object_name: str, rule_set: str) -> Dict:
    """
    Check against design rules

    Rule sets: iso_tolerancing, ansi_standards, fda_medical, etc.

    Returns violations and recommendations
    """

@mcp.tool()
def estimate_tolerances(object_name: str,
                       manufacturing_method: str) -> Dict:
    """
    Suggest appropriate tolerances based on manufacturing

    Returns recommended tolerance grades for each dimension
    """
```

### 3.3 Performance Feedback

```python
@mcp.tool()
def get_operation_cost_estimate(operation: str, params: Dict) -> Dict:
    """
    Estimate computational cost before execution

    Returns: {"estimated_time_ms": 1500, "memory_mb": 45, "complexity": "medium"}
    """

@mcp.tool()
def get_last_operation_metrics() -> Dict:
    """
    Get metrics from last operation

    Returns: actual execution time, memory used, recompute time
    Enables LLM to learn which operations are expensive
    """
```

---

## 4. Advanced Parametric Design (P1 - High Priority)

### 4.1 Spreadsheet Integration

```python
@mcp.tool()
def create_spreadsheet(name: str, data: Dict) -> Dict:
    """
    Create spreadsheet with design parameters

    data = {
        "width": 100,
        "height": 50,
        "hole_diameter": "=width / 10",
        "material": "Steel"
    }
    """

@mcp.tool()
def link_to_spreadsheet(object_name: str, property: str,
                       spreadsheet: str, cell: str) -> Dict:
    """Link object property to spreadsheet cell"""

@mcp.tool()
def batch_generate_variants(template: str,
                           parameter_sets: List[Dict]) -> Dict:
    """
    Generate multiple design variants

    Returns: list of generated documents with parameter values
    Enables design space exploration
    """
```

### 4.2 Expression System

```python
@mcp.tool()
def set_expression(object_name: str, property: str,
                  expression: str) -> Dict:
    """
    Set parametric expression

    Examples:
        expression = "Box.Length * 2"
        expression = "spreadsheet.height + 10"
    """

@mcp.tool()
def get_expressions(object_name: str = None) -> Dict:
    """List all expressions in document or object"""

@mcp.tool()
def validate_expression(expression: str, context: Dict) -> Dict:
    """
    Validate expression before applying

    Returns: valid status, resolved value, dependencies
    """
```

### 4.3 Configuration Management

```python
@mcp.tool()
def create_configuration(name: str, parameters: Dict) -> Dict:
    """Save named configuration of parameters"""

@mcp.tool()
def apply_configuration(name: str) -> Dict:
    """Apply saved configuration"""

@mcp.tool()
def list_configurations() -> List[Dict]:
    """List all saved configurations"""
```

---

## 5. Part/Template Library System (P1 - High Priority)

### 5.1 Dynamic Template Discovery

```python
@mcp.tool()
def list_available_templates(category: str = None) -> List[Dict]:
    """
    List all available templates with metadata

    Returns:
        [
            {
                "name": "parametric_gear",
                "category": "mechanical",
                "description": "Involute spur gear",
                "parameters": [
                    {"name": "teeth", "type": "int", "default": 20, "min": 6},
                    {"name": "module", "type": "float", "default": 2.0}
                ],
                "preview_image": "base64...",
                "complexity": "medium",
                "use_cases": ["power transmission", "timing"]
            }
        ]
    """

@mcp.tool()
def search_templates(query: str, filters: Dict = None) -> List[Dict]:
    """
    Search templates by keyword/category

    Enables LLM to discover: "find templates for threaded holes"
    """

@mcp.tool()
def get_template_preview(template_name: str, params: Dict) -> Dict:
    """
    Generate preview without creating full object

    Returns: quick render, bounding box, mass estimate
    """
```

### 5.2 Part Library Integration

```python
@mcp.tool()
def search_standard_parts(query: str, standard: str = None) -> List[Dict]:
    """
    Search for standard parts

    Examples:
        query = "M6 bolt", standard = "ISO"
        query = "608 bearing", standard = "DIN"

    Returns: available parts with specifications
    """

@mcp.tool()
def insert_standard_part(part_id: str, position: List[float],
                        rotation: List[float] = None) -> Dict:
    """Insert standard part at location"""

@mcp.tool()
def get_part_specifications(part_id: str) -> Dict:
    """Get detailed specs for standard part"""
```

---

## 6. Draft/2D Drawing Enhancements (P2 - Medium Priority)

### 6.1 TechDraw Automation

```python
@mcp.tool()
def create_drawing_page(template: str, scale: float = 1.0) -> Dict:
    """Create TechDraw page from template"""

@mcp.tool()
def add_view_to_page(page_name: str, object_name: str,
                    view_type: str, position: List[float]) -> Dict:
    """
    Add view to drawing

    Types: Front, Top, Isometric, Section, Detail
    """

@mcp.tool()
def add_dimensions(page_name: str, view_name: str,
                  dimension_type: str, points: List) -> Dict:
    """Add dimensions to view"""

@mcp.tool()
def generate_bill_of_materials(assembly_name: str,
                              format: str = "table") -> Dict:
    """Generate BOM from assembly"""
```

### 6.2 Draft Workbench

```python
@mcp.tool()
def create_draft_object(object_type: str, params: Dict) -> Dict:
    """
    Create 2D Draft objects

    Types: Line, Wire, Rectangle, Circle, Arc, Polygon, BSpline, etc.
    """

@mcp.tool()
def convert_to_sketch(draft_object: str) -> Dict:
    """Convert Draft object to Sketcher sketch"""

@mcp.tool()
def create_dimension_style(name: str, properties: Dict) -> Dict:
    """Create custom dimension style"""
```

---

## 7. Workflow Automation (P2 - Medium Priority)

### 7.1 Macro Recording & Replay

```python
@mcp.tool()
def start_recording_operations() -> Dict:
    """Start recording all operations"""

@mcp.tool()
def stop_recording() -> Dict:
    """Stop recording, return operation sequence"""

@mcp.tool()
def replay_operations(operations: List[Dict],
                     parameter_overrides: Dict = None) -> Dict:
    """Replay recorded operations with modified parameters"""
```

### 7.2 Batch Processing

```python
@mcp.tool()
def batch_export(objects: List[str], format: str,
                output_dir: str, naming_pattern: str) -> Dict:
    """
    Export multiple objects

    naming_pattern = "{object_name}_{timestamp}.{ext}"
    """

@mcp.tool()
def batch_apply_operation(objects: List[str], operation: str,
                         params: Dict) -> Dict:
    """Apply same operation to multiple objects"""

@mcp.tool()
def parallel_generate(templates: List[Dict],
                     max_workers: int = 4) -> Dict:
    """Generate multiple parts in parallel"""
```

---

## 8. State Management & Undo (P2 - Medium Priority)

### 8.1 Version Control

```python
@mcp.tool()
def create_checkpoint(name: str, description: str = "") -> Dict:
    """Save current state as checkpoint"""

@mcp.tool()
def restore_checkpoint(name: str) -> Dict:
    """Restore to checkpoint"""

@mcp.tool()
def list_checkpoints() -> List[Dict]:
    """List all checkpoints"""

@mcp.tool()
def undo_last_operation(count: int = 1) -> Dict:
    """Undo last N operations"""

@mcp.tool()
def get_operation_history(limit: int = 100) -> List[Dict]:
    """Get history of operations performed"""
```

### 8.2 Document State Queries

```python
@mcp.tool()
def get_document_state() -> Dict:
    """
    Get complete document state snapshot

    Returns:
        {
            "object_count": 15,
            "total_volume": 125000,
            "total_mass": 985.5,
            "has_errors": False,
            "recompute_needed": False,
            "modified": True,
            "last_modified": "2026-01-14T10:30:00"
        }
    """

@mcp.tool()
def compare_documents(doc1: str, doc2: str) -> Dict:
    """Compare two documents, show differences"""
```

---

## 9. Mesh & Point Cloud Operations (P3 - Low Priority)

```python
@mcp.tool()
def mesh_from_shape(object_name: str, max_deviation: float = 0.1) -> Dict:
    """Convert solid to mesh"""

@mcp.tool()
def simplify_mesh(mesh_name: str, target_faces: int) -> Dict:
    """Reduce mesh complexity"""

@mcp.tool()
def mesh_boolean(mesh1: str, mesh2: str, operation: str) -> Dict:
    """Boolean operations on meshes"""

@mcp.tool()
def import_point_cloud(filepath: str) -> Dict:
    """Import point cloud data"""

@mcp.tool()
def fit_surface_to_points(point_cloud: str, method: str) -> Dict:
    """Reconstruct surface from point cloud"""
```

---

## 10. Architecture Improvements (P1 - High Priority)

### 10.1 Streaming & Progress

**Problem:** Long operations block with no feedback

```python
@mcp.tool()
def execute_with_progress(operation: str, params: Dict,
                         callback_url: str = None) -> Dict:
    """
    Execute operation with progress callbacks

    Sends progress updates: {"progress": 0.45, "message": "Extruding..."}
    """

@mcp.tool()
def cancel_operation(operation_id: str) -> Dict:
    """Cancel long-running operation"""

@mcp.tool()
def get_operation_status(operation_id: str) -> Dict:
    """Check status of async operation"""
```

### 10.2 Batch Request Optimization

```python
@mcp.tool()
def execute_batch(operations: List[Dict],
                 atomic: bool = True) -> List[Dict]:
    """
    Execute multiple operations in one request

    atomic=True: rollback all if any fails
    atomic=False: execute all, return individual results

    Reduces round-trip latency for LLM workflows
    """
```

### 10.3 Smart Recompute

```python
@mcp.tool()
def set_auto_recompute(enabled: bool) -> Dict:
    """Control automatic recompute"""

@mcp.tool()
def mark_for_recompute(object_names: List[str]) -> Dict:
    """Mark specific objects for recompute"""

@mcp.tool()
def recompute_selective(object_names: List[str]) -> Dict:
    """Recompute only specified objects and dependencies"""
```

### 10.4 Enhanced Error Handling

```python
# Every tool should return structured errors:
{
    "result": "error",
    "error_type": "GeometryError",
    "error_code": "E_INVALID_BOOLEAN",
    "message": "Boolean operation failed: shapes do not intersect",
    "details": {
        "object1": "Box",
        "object2": "Cylinder",
        "suggested_fix": "Move Cylinder to intersect Box"
    },
    "recoverable": True,
    "retry_suggested": False,
    "documentation_url": "https://wiki.freecadweb.org/Part_Boolean"
}
```

---

## 11. LLM-Optimized Response Formats

### 11.1 Structured Metadata

Every response should include:

```python
{
    "result": "success",
    "data": {...},
    "metadata": {
        "execution_time_ms": 45,
        "objects_created": ["Pad", "Sketch001"],
        "objects_modified": ["Body"],
        "recompute_triggered": True,
        "affects_downstream": ["Fillet", "Pattern"],
        "cost_estimate": {"memory_mb": 12, "complexity": "low"}
    },
    "next_actions": [
        {"operation": "add_fillet", "confidence": 0.9, "reason": "sharp edges detected"},
        {"operation": "export_stl", "confidence": 0.7, "reason": "geometry complete"}
    ]
}
```

### 11.2 Rich Object Descriptions

```python
@mcp.tool()
def describe_object(object_name: str, detail_level: str = "full") -> Dict:
    """
    Get comprehensive object description

    Returns:
        {
            "name": "Pad",
            "type": "PartDesign::Pad",
            "label": "Main Extrusion",
            "properties": {
                "Length": 50.0,
                "Reversed": False,
                "Type": "Length"
            },
            "geometry": {
                "volume": 125000.0,
                "surface_area": 10500.0,
                "bounding_box": {...}
            },
            "dependencies": {
                "depends_on": ["Sketch"],
                "used_by": ["Fillet", "Pattern"]
            },
            "validity": {
                "is_valid": True,
                "has_errors": False,
                "warnings": []
            },
            "capabilities": {
                "can_export": True,
                "can_mesh": True,
                "supports_boolean": True
            },
            "visual": {
                "visible": True,
                "transparency": 0,
                "color": [0.8, 0.8, 0.8]
            }
        }
    """
```

---

## 12. Semantic Query Interface (P1 - High Priority)

### 12.1 Natural Query Support

```python
@mcp.tool()
def semantic_search(query: str, context: Dict = None) -> List[Dict]:
    """
    Search using natural language

    Examples:
        "all cylinders with radius > 10"
        "sketches that are not fully constrained"
        "parts made of steel heavier than 500g"
        "objects with sharp edges that need filleting"

    Returns ranked results with relevance scores
    """

@mcp.tool()
def suggest_next_steps(goal: str, current_state: Dict) -> List[Dict]:
    """
    Given high-level goal, suggest workflow

    Example:
        goal = "create M8 threaded hole at center of top face"
        → Returns: [
            {"step": 1, "operation": "create_sketch", "params": {..."} },
            {"step": 2, "operation": "add_circle", "params": {...} },
            {"step": 3, "operation": "add_helix", "params": {...} }
        ]
    """
```

---

## 13. CAM/Manufacturing Integration (P3 - Low Priority)

```python
@mcp.tool()
def generate_toolpath(object_name: str, operation: str, params: Dict) -> Dict:
    """
    Generate CAM toolpath

    Operations: profile, pocket, drill, engrave, 3d_surface
    """

@mcp.tool()
def estimate_machining_time(toolpath_name: str) -> Dict:
    """Estimate CNC machining time"""

@mcp.tool()
def export_gcode(toolpath_name: str, filepath: str,
                post_processor: str) -> Dict:
    """Export toolpath as G-code"""
```

---

## 14. Implementation Priority Matrix

| Priority | Category | Tools | Impact | Effort |
|----------|----------|-------|--------|--------|
| **P0** | Discovery & Introspection | 10 tools | Critical | Medium |
| **P0** | Assembly Workbench | 5 tools | Critical | High |
| **P0** | Material Properties | 4 tools | High | Medium |
| **P0** | Geometry Validation | 6 tools | High | High |
| **P1** | Advanced Constraints | 8 tools | High | Medium |
| **P1** | Parametric Design | 12 tools | High | High |
| **P1** | Template Library | 6 tools | Medium | Low |
| **P1** | Architecture Improvements | 8 tools | High | Medium |
| **P2** | Import Capabilities | 5 tools | Medium | Low |
| **P2** | TechDraw Automation | 6 tools | Medium | Medium |
| **P2** | Workflow Automation | 8 tools | Medium | Medium |
| **P2** | State Management | 7 tools | Medium | High |
| **P3** | Mesh Operations | 5 tools | Low | Medium |
| **P3** | CAM Integration | 4 tools | Low | High |

---

## 15. Recommended v0.3.0 Scope

**Theme:** "LLM Decision-Making Infrastructure"

**Include:**
1. All P0 Discovery & Introspection (10 tools)
2. Assembly basics (5 tools)
3. Material assignment (4 tools)
4. Geometry validation suite (6 tools)
5. Template discovery (6 tools)
6. Architecture improvements (8 tools)
7. Enhanced error handling (refactor all existing tools)

**Total:** ~40 new tools + refactor existing 50 = **v0.3.0 with 90 tools**

**Expected Impact:**
- LLM can discover capabilities autonomously
- LLM can validate designs before execution
- LLM can work with assemblies
- LLM gets rich feedback for learning
- 3× more autonomous than v0.2.0

---

## 16. Key Design Principles

### 16.1 Every Tool Should Answer:

1. **What can I do next?** (suggest_next_operations)
2. **Is this valid?** (validation results)
3. **What went wrong?** (structured errors)
4. **What else exists?** (discovery/listing)
5. **How expensive is this?** (cost estimates)

### 16.2 LLM-Friendly Patterns:

**✅ Good:**
```python
# Queryable, discoverable, validates
result = create_body(name="Base")
# Returns: {
#   "result": "success",
#   "body_name": "Base",
#   "next_actions": ["create_sketch", "import_part"],
#   "validation": {"can_add_features": True}
# }
```

**❌ Bad:**
```python
# Write-only, no feedback, opaque
result = create_body(name="Base")
# Returns: {"result": "success"}
# LLM has no idea what to do next or what's possible
```

### 16.3 Always Include Context:

```python
# Instead of:
delete_object("Box")  # What if something depends on it?

# Do:
delete_object("Box", check_dependencies=True)
# Returns: {
#   "result": "error",
#   "message": "Cannot delete: 3 objects depend on Box",
#   "dependencies": ["Fillet", "Pattern", "Boolean"],
#   "suggestions": [
#     {"action": "delete_tree", "description": "Delete Box and all dependents"},
#     {"action": "replace_reference", "description": "Replace Box reference in dependents"}
#   ]
# }
```

---

## 17. Documentation Requirements

For each new tool, provide:

1. **Semantic description** (what it does, not how)
2. **Prerequisites** (what must exist first)
3. **Parameter constraints** (valid ranges, types)
4. **Return value structure** (with metadata)
5. **Common error scenarios** (with recovery steps)
6. **Usage examples** (3 levels: basic, intermediate, advanced)
7. **Related operations** (what typically comes before/after)
8. **Cost profile** (fast/slow, memory usage)

Example:
```python
@mcp.tool()
def create_body(name: str, document_name: str = None) -> Dict:
    """
    Create a PartDesign Body container for parametric features.

    Semantic: Bodies are containers for parametric features (sketches, pads, pockets).
              Think of it as starting a new part within a document.

    Prerequisites:
        - Active document must exist (or provide document_name)

    Parameters:
        name: Body name (alphanumeric, underscore, hyphen only)
        document_name: Target document (optional, uses active if None)

    Returns:
        {
            "result": "success",
            "body_name": str,  # Actual name (may differ if name collision)
            "document": str,   # Document it was created in
            "next_actions": [  # Suggested next steps
                {"operation": "create_sketch", "reason": "Bodies need sketches for features"},
                {"operation": "import_part", "reason": "Or import existing geometry"}
            ],
            "metadata": {
                "execution_time_ms": int,
                "can_add_features": bool
            }
        }

    Errors:
        - E_NO_DOCUMENT: No active document and document_name not found
        - E_INVALID_NAME: Name contains invalid characters
        - E_NAME_COLLISION: Body with this name already exists

    Examples:
        Basic: create_body("Base")
        Intermediate: create_body("Bracket", document_name="Assembly1")
        Advanced: Used in parametric part sequence (see workflow examples)

    Related:
        Before: create_document, get_active_document
        After: create_sketch, add_circle, extrude_sketch
        Alternative: For non-parametric, use Part workbench instead

    Cost: Fast (<10ms), minimal memory
    """
```

---

## 18. Success Metrics for v0.3.0

**Measure LLM autonomy improvement:**

1. **Discovery Score:** Can LLM find 80% of relevant operations without docs? (currently ~20%)
2. **Error Recovery Rate:** LLM successfully recovers from 70% of errors (currently ~30%)
3. **First-Time Success:** 60% of design goals achieved without manual intervention (currently ~25%)
4. **Context Awareness:** LLM queries state before acting 90% of time (currently ~10%)
5. **Validation Usage:** LLM validates before risky operations 80% of time (currently ~5%)

**Target:** 3× improvement in autonomous design capability

---

## 19. References & Resources

### FreeCAD Python API Documentation:
- Official API: https://freecad-python-api.readthedocs.io/
- Part scripting: https://wiki.freecadweb.org/Part_scripting
- Sketcher API: https://wiki.freecad.org/Sketcher_scripting
- Assembly3: https://github.com/realthunder/FreeCAD_assembly3/wiki
- Code snippets: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Code_snippets.md

### Key Gaps Identified:
1. Assembly constraint solver API exposure
2. Advanced Sketcher constraint types
3. Material database access
4. Manufacturing validation rules
5. Template/part library system
6. Semantic search capabilities

---

## 20. Next Steps

1. **Review this document** with team/stakeholders
2. **Prioritize P0 features** for v0.3.0
3. **Prototype discovery tools** (highest ROI for LLM autonomy)
4. **Implement validation suite** (enables safe autonomous operation)
5. **Refactor error handling** (critical for LLM learning)
6. **Test with LLM workflows** (measure autonomy improvements)

**Estimated v0.3.0 Development Time:** 6-8 weeks for P0 features

---

**Document Version:** 1.0
**Last Updated:** 2026-01-14
**Authors:** Claude Sonnet 4.5 (Analysis), FreeCAD Community (API Research)
