"""
FreeCAD Macro Template System

Provides reusable templates for common FreeCAD operations with parameter injection.
"""

TEMPLATES = {
    "parametric_box": '''"""Create a parametric box.
Parameters:
    length: Box length (default: 10)
    width: Box width (default: 10)
    height: Box height (default: 10)
"""
import FreeCAD as App
import Part

length = {length}
width = {width}
height = {height}

doc = App.ActiveDocument or App.newDocument("Box")
box = doc.addObject("Part::Box", "Box")
box.Length = length
box.Width = width
box.Height = height
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "parametric_cylinder": '''"""Create a parametric cylinder.
Parameters:
    radius: Cylinder radius (default: 5)
    height: Cylinder height (default: 10)
"""
import FreeCAD as App
import Part

radius = {radius}
height = {height}

doc = App.ActiveDocument or App.newDocument("Cylinder")
cylinder = doc.addObject("Part::Cylinder", "Cylinder")
cylinder.Radius = radius
cylinder.Height = height
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "sketch_rectangle": '''"""Create a sketch with a rectangle.
Parameters:
    width: Rectangle width (default: 10)
    height: Rectangle height (default: 10)
    x: X position of bottom-left corner (default: 0)
    y: Y position of bottom-left corner (default: 0)
"""
import FreeCAD as App
import Sketcher

width = {width}
height = {height}
x = {x}
y = {y}

doc = App.ActiveDocument or App.newDocument("Sketch")
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
sketch.addGeometry(Part.LineSegment(
    App.Vector(x, y, 0),
    App.Vector(x + width, y, 0)
))
sketch.addGeometry(Part.LineSegment(
    App.Vector(x + width, y, 0),
    App.Vector(x + width, y + height, 0)
))
sketch.addGeometry(Part.LineSegment(
    App.Vector(x + width, y + height, 0),
    App.Vector(x, y + height, 0)
))
sketch.addGeometry(Part.LineSegment(
    App.Vector(x, y + height, 0),
    App.Vector(x, y, 0)
))
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "sketch_circle": '''"""Create a sketch with a circle.
Parameters:
    radius: Circle radius (default: 5)
    x: X position of center (default: 0)
    y: Y position of center (default: 0)
"""
import FreeCAD as App
import Part
import Sketcher

radius = {radius}
x = {x}
y = {y}

doc = App.ActiveDocument or App.newDocument("Sketch")
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
sketch.addGeometry(Part.Circle(
    App.Vector(x, y, 0),
    App.Vector(0, 0, 1),
    radius
))
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "extrude_profile": '''"""Create a rectangular sketch and extrude it.
Parameters:
    width: Rectangle width (default: 10)
    height: Rectangle height (default: 10)
    extrude_length: Extrusion length (default: 20)
"""
import FreeCAD as App
import Part
import Sketcher

width = {width}
height = {height}
extrude_length = {extrude_length}

doc = App.ActiveDocument or App.newDocument("Extrude")
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
sketch.addGeometry(Part.LineSegment(
    App.Vector(0, 0, 0),
    App.Vector(width, 0, 0)
))
sketch.addGeometry(Part.LineSegment(
    App.Vector(width, 0, 0),
    App.Vector(width, height, 0)
))
sketch.addGeometry(Part.LineSegment(
    App.Vector(width, height, 0),
    App.Vector(0, height, 0)
))
sketch.addGeometry(Part.LineSegment(
    App.Vector(0, height, 0),
    App.Vector(0, 0, 0)
))
doc.recompute()

pad = doc.addObject("PartDesign::Pad", "Pad")
pad.Profile = sketch
pad.Length = extrude_length
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "revolve_profile": '''"""Create a sketch profile and revolve it.
Parameters:
    radius: Profile radius (default: 5)
    height: Profile height (default: 10)
    angle: Revolve angle in degrees (default: 360)
"""
import FreeCAD as App
import Part
import Sketcher

radius = {radius}
height = {height}
angle = {angle}

doc = App.ActiveDocument or App.newDocument("Revolve")
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")
sketch.addGeometry(Part.LineSegment(
    App.Vector(radius, 0, 0),
    App.Vector(radius, height, 0)
))
sketch.addGeometry(Part.LineSegment(
    App.Vector(radius, height, 0),
    App.Vector(radius + 2, height, 0)
))
sketch.addGeometry(Part.LineSegment(
    App.Vector(radius + 2, height, 0),
    App.Vector(radius + 2, 0, 0)
))
sketch.addGeometry(Part.LineSegment(
    App.Vector(radius + 2, 0, 0),
    App.Vector(radius, 0, 0)
))
doc.recompute()

revolve = doc.addObject("PartDesign::Revolution", "Revolve")
revolve.Profile = sketch
revolve.Angle = angle
revolve.Axis = (0.0, 1.0, 0.0)
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "loft_profiles": '''"""Create loft between multiple circular sketches.
Parameters:
    radius1: First circle radius (default: 5)
    radius2: Second circle radius (default: 10)
    radius3: Third circle radius (default: 3)
    spacing: Vertical spacing between circles (default: 10)
"""
import FreeCAD as App
import Part
import Sketcher

radius1 = {radius1}
radius2 = {radius2}
radius3 = {radius3}
spacing = {spacing}

doc = App.ActiveDocument or App.newDocument("Loft")

sketch1 = doc.addObject("Sketcher::SketchObject", "Sketch1")
sketch1.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())
sketch1.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), radius1))

sketch2 = doc.addObject("Sketcher::SketchObject", "Sketch2")
sketch2.Placement = App.Placement(App.Vector(0, 0, spacing), App.Rotation())
sketch2.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), radius2))

sketch3 = doc.addObject("Sketcher::SketchObject", "Sketch3")
sketch3.Placement = App.Placement(App.Vector(0, 0, spacing * 2), App.Rotation())
sketch3.addGeometry(Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), radius3))

doc.recompute()

loft = doc.addObject("Part::Loft", "Loft")
loft.Sections = [sketch1, sketch2, sketch3]
loft.Solid = True
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "boolean_union": '''"""Create union of two boxes.
Parameters:
    box1_length: First box length (default: 10)
    box1_width: First box width (default: 10)
    box1_height: First box height (default: 10)
    box2_length: Second box length (default: 8)
    box2_width: Second box width (default: 8)
    box2_height: Second box height (default: 15)
    offset_x: X offset for second box (default: 5)
    offset_y: Y offset for second box (default: 5)
    offset_z: Z offset for second box (default: 5)
"""
import FreeCAD as App
import Part

box1_length = {box1_length}
box1_width = {box1_width}
box1_height = {box1_height}
box2_length = {box2_length}
box2_width = {box2_width}
box2_height = {box2_height}
offset_x = {offset_x}
offset_y = {offset_y}
offset_z = {offset_z}

doc = App.ActiveDocument or App.newDocument("Union")

box1 = doc.addObject("Part::Box", "Box1")
box1.Length = box1_length
box1.Width = box1_width
box1.Height = box1_height

box2 = doc.addObject("Part::Box", "Box2")
box2.Length = box2_length
box2.Width = box2_width
box2.Height = box2_height
box2.Placement = App.Placement(
    App.Vector(offset_x, offset_y, offset_z),
    App.Rotation()
)

doc.recompute()

union = doc.addObject("Part::Fuse", "Union")
union.Base = box1
union.Tool = box2
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "boolean_difference": '''"""Create difference of two boxes (first minus second).
Parameters:
    box1_length: First box length (default: 20)
    box1_width: First box width (default: 20)
    box1_height: First box height (default: 20)
    box2_length: Second box length (default: 10)
    box2_width: Second box width (default: 10)
    box2_height: Second box height (default: 25)
    offset_x: X offset for second box (default: 5)
    offset_y: Y offset for second box (default: 5)
    offset_z: Z offset for second box (default: -2)
"""
import FreeCAD as App
import Part

box1_length = {box1_length}
box1_width = {box1_width}
box1_height = {box1_height}
box2_length = {box2_length}
box2_width = {box2_width}
box2_height = {box2_height}
offset_x = {offset_x}
offset_y = {offset_y}
offset_z = {offset_z}

doc = App.ActiveDocument or App.newDocument("Difference")

box1 = doc.addObject("Part::Box", "Box1")
box1.Length = box1_length
box1.Width = box1_width
box1.Height = box1_height

box2 = doc.addObject("Part::Box", "Box2")
box2.Length = box2_length
box2.Width = box2_width
box2.Height = box2_height
box2.Placement = App.Placement(
    App.Vector(offset_x, offset_y, offset_z),
    App.Rotation()
)

doc.recompute()

difference = doc.addObject("Part::Cut", "Difference")
difference.Base = box1
difference.Tool = box2
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "array_linear": '''"""Create linear array of boxes.
Parameters:
    box_length: Box length (default: 5)
    box_width: Box width (default: 5)
    box_height: Box height (default: 5)
    count: Number of copies (default: 5)
    spacing_x: X spacing between copies (default: 10)
    spacing_y: Y spacing between copies (default: 0)
    spacing_z: Z spacing between copies (default: 0)
"""
import FreeCAD as App
import Part
import Draft

box_length = {box_length}
box_width = {box_width}
box_height = {box_height}
count = {count}
spacing_x = {spacing_x}
spacing_y = {spacing_y}
spacing_z = {spacing_z}

doc = App.ActiveDocument or App.newDocument("LinearArray")

box = doc.addObject("Part::Box", "Box")
box.Length = box_length
box.Width = box_width
box.Height = box_height
doc.recompute()

array = Draft.makeArray(
    box,
    App.Vector(spacing_x, spacing_y, spacing_z),
    App.Vector(0, 0, 0),
    count,
    1,
    1
)
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',

    "array_polar": '''"""Create polar array of boxes around Z axis.
Parameters:
    box_length: Box length (default: 5)
    box_width: Box width (default: 5)
    box_height: Box height (default: 5)
    count: Number of copies (default: 8)
    radius: Array radius (default: 20)
    angle: Total angle in degrees (default: 360)
"""
import FreeCAD as App
import Part
import Draft
import math

box_length = {box_length}
box_width = {box_width}
box_height = {box_height}
count = {count}
radius = {radius}
angle = {angle}

doc = App.ActiveDocument or App.newDocument("PolarArray")

box = doc.addObject("Part::Box", "Box")
box.Length = box_length
box.Width = box_width
box.Height = box_height
box.Placement = App.Placement(
    App.Vector(radius, 0, 0),
    App.Rotation()
)
doc.recompute()

array = Draft.makeArray(
    box,
    App.Vector(0, 0, 0),
    App.Vector(0, 0, 1),
    1,
    1,
    count,
    angle
)
doc.recompute()
App.Gui.ActiveDocument.ActiveView.fitAll()
''',
}

# Default parameter values for each template
DEFAULT_PARAMS = {
    "parametric_box": {
        "length": 10,
        "width": 10,
        "height": 10,
    },
    "parametric_cylinder": {
        "radius": 5,
        "height": 10,
    },
    "sketch_rectangle": {
        "width": 10,
        "height": 10,
        "x": 0,
        "y": 0,
    },
    "sketch_circle": {
        "radius": 5,
        "x": 0,
        "y": 0,
    },
    "extrude_profile": {
        "width": 10,
        "height": 10,
        "extrude_length": 20,
    },
    "revolve_profile": {
        "radius": 5,
        "height": 10,
        "angle": 360,
    },
    "loft_profiles": {
        "radius1": 5,
        "radius2": 10,
        "radius3": 3,
        "spacing": 10,
    },
    "boolean_union": {
        "box1_length": 10,
        "box1_width": 10,
        "box1_height": 10,
        "box2_length": 8,
        "box2_width": 8,
        "box2_height": 15,
        "offset_x": 5,
        "offset_y": 5,
        "offset_z": 5,
    },
    "boolean_difference": {
        "box1_length": 20,
        "box1_width": 20,
        "box1_height": 20,
        "box2_length": 10,
        "box2_width": 10,
        "box2_height": 25,
        "offset_x": 5,
        "offset_y": 5,
        "offset_z": -2,
    },
    "array_linear": {
        "box_length": 5,
        "box_width": 5,
        "box_height": 5,
        "count": 5,
        "spacing_x": 10,
        "spacing_y": 0,
        "spacing_z": 0,
    },
    "array_polar": {
        "box_length": 5,
        "box_width": 5,
        "box_height": 5,
        "count": 8,
        "radius": 20,
        "angle": 360,
    },
}


def get_template(name: str, params: dict = None) -> str:
    """
    Get a template with parameters filled in.

    Args:
        name: Template name from TEMPLATES dict
        params: Dict of parameters to inject (uses defaults if not provided)

    Returns:
        Template string with parameters filled in

    Raises:
        KeyError: If template name not found
    """
    if name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise KeyError(f"Template '{name}' not found. Available: {available}")

    # Get defaults and merge with provided params
    template_params = DEFAULT_PARAMS.get(name, {}).copy()
    if params:
        template_params.update(params)

    # Fill in template
    template = TEMPLATES[name]
    return template.format(**template_params)


def list_templates() -> list:
    """
    Get list of available template names.

    Returns:
        List of template names
    """
    return list(TEMPLATES.keys())


def get_template_info(name: str) -> dict:
    """
    Get information about a template including parameters and defaults.

    Args:
        name: Template name

    Returns:
        Dict with 'name', 'params', and 'docstring' keys

    Raises:
        KeyError: If template name not found
    """
    if name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise KeyError(f"Template '{name}' not found. Available: {available}")

    template = TEMPLATES[name]
    params = DEFAULT_PARAMS.get(name, {})

    # Extract docstring from template
    docstring = ""
    if '"""' in template:
        start = template.find('"""') + 3
        end = template.find('"""', start)
        docstring = template[start:end].strip()

    return {
        "name": name,
        "params": params,
        "docstring": docstring,
    }
