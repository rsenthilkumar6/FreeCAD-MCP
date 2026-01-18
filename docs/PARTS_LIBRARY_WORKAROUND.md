# Parts Library Installation Workaround

## Problem
The FreeCAD-library repository is very large (several GB), causing git clone to fail with "fatal: early EOF".

## Solution 1: Skip Parts Library (RECOMMENDED)

**FreeCAD MCP v0.3.0 works fine WITHOUT parts library!**

**What works without it:**
- ✅ All 54 tools
- ✅ Visual feedback (get_view)
- ✅ execute_code
- ✅ Part Design, measurement, export

**What doesn't work:**
- ❌ get_parts_list() - Returns empty
- ❌ insert_part_from_library() - Returns error

**For most use cases, you don't need the parts library.**

---

## Solution 2: Install via FreeCAD Addon Manager

**Recommended approach:**

1. Open FreeCAD
2. Tools → Addon Manager
3. Search for "parts_library"
4. Click Install
5. Wait (this will take 10-30 minutes for the large download)
6. Restart FreeCAD

**Pros:** Official method, handles large download
**Cons:** Takes a long time

---

## Solution 3: Manual Partial Download

Download only the parts you need:

```bash
# Create parts_library directory
mkdir -p ~/Library/Application\ Support/FreeCAD/Mod/parts_library

# Download only fasteners (much smaller)
cd ~/Library/Application\ Support/FreeCAD/Mod/parts_library
svn export https://github.com/FreeCAD/FreeCAD-library/trunk/Fasteners
```

**Pros:** Much faster, only downloads what you need
**Cons:** Requires svn (install via `brew install subversion`)

---

## Solution 4: Alternative - Use execute_code to create parts

Instead of using the parts library, use execute_code() to create standard parts:

```python
# Create M6 bolt programmatically
execute_code('''
import FreeCAD as App
import Part

doc = App.ActiveDocument

# M6 bolt parameters (ISO 4017)
diameter = 6.0
length = 20.0
head_diameter = 10.0
head_height = 4.0

# Create shank
shank = Part.makeCylinder(diameter/2, length)

# Create hex head
head = Part.makeCylinder(head_diameter/2, head_height)
head.translate(App.Vector(0, 0, length))

# Union
bolt = shank.fuse(head)
doc.addObject("Part::Feature", "M6_Bolt").Shape = bolt
doc.recompute()
''', validate=True)
```

**Pros:** No parts library needed, fully customizable
**Cons:** More code, need to know dimensions

---

## Recommendation

**For v0.3.0 testing: Skip parts library (Solution 1)**

The visual feedback (get_view) and execute_code features are the game changers, not the parts library. You can test those immediately without waiting for the large download.

**For production use: Install via Addon Manager (Solution 2)**

If you need standard parts frequently, use FreeCAD's Addon Manager to install properly.

---

## Testing v0.3.0 WITHOUT Parts Library

```python
# This works perfectly:
create_document("Test")
create_body("Base")
create_sketch("Base", "Sketch", "XY")
add_circle("Sketch", 0, 0, 10)
extrude_sketch("Sketch", 20)

# NEW in v0.3.0: Visual feedback!
get_view("Isometric")  # Returns screenshot

# NEW in v0.3.0: Flexible code execution!
execute_code('''
import Part
box = Part.makeBox(10, 10, 10)
App.ActiveDocument.addObject("Part::Feature", "Box").Shape = box
App.ActiveDocument.recompute()
''')

# This will fail without parts library (expected):
# get_parts_list()  # Returns: {"result": "success", "parts": [], "count": 0}
# insert_part_from_library("...")  # Returns error

# But you can create parts manually:
execute_code('''
# Create M6 bolt manually
''')
```

**Bottom line: v0.3.0 is fully functional without parts library!**
