# Measurement and analysis handler methods to be added to FreeCADMCPServer class

def _get_document(self, document_name=None):
    """Helper method to get document"""
    if document_name:
        if document_name not in App.listDocuments():
            raise Exception(f"Document '{document_name}' not found")
        return App.getDocument(document_name)
    else:
        if not App.ActiveDocument:
            raise Exception("No active document")
        return App.ActiveDocument

def _get_object(self, object_name, document_name=None):
    """Helper method to get object from document"""
    doc = self._get_document(document_name)
    obj = doc.getObject(object_name)
    if not obj:
        raise Exception(f"Object '{object_name}' not found in document '{doc.Name}'")
    return obj

def handle_list_documents(self):
    try:
        docs = []
        for doc_name in App.listDocuments():
            doc = App.getDocument(doc_name)
            docs.append({
                "name": doc.Name,
                "label": doc.Label,
                "object_count": len(doc.Objects)
            })
        log_message(f"Listed {len(docs)} documents")
        return {"result": "success", "documents": docs}
    except Exception as e:
        log_error(f"Error listing documents: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_get_active_document(self):
    try:
        if not App.ActiveDocument:
            return {"result": "error", "message": "No active document"}
        doc = App.ActiveDocument
        objects = []
        for obj in doc.Objects:
            objects.append({
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId
            })
        log_message(f"Got active document: {doc.Name}")
        return {
            "result": "success",
            "name": doc.Name,
            "label": doc.Label,
            "objects": objects
        }
    except Exception as e:
        log_error(f"Error getting active document: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_create_document(self, name):
    try:
        doc = App.newDocument(name)
        log_message(f"Created document: {doc.Name}")
        return {"result": "success", "name": doc.Name}
    except Exception as e:
        log_error(f"Error creating document: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_save_document(self, filename):
    try:
        if not App.ActiveDocument:
            return {"result": "error", "message": "No active document"}
        App.ActiveDocument.saveAs(filename)
        log_message(f"Saved document to: {filename}")
        return {"result": "success", "filepath": filename}
    except Exception as e:
        log_error(f"Error saving document: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_close_document(self, name):
    try:
        App.closeDocument(name)
        log_message(f"Closed document: {name}")
        return {"result": "success"}
    except Exception as e:
        log_error(f"Error closing document: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_list_objects(self, document_name=None):
    try:
        doc = self._get_document(document_name)
        objects = []
        for obj in doc.Objects:
            obj_data = {
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId
            }
            if hasattr(obj, "Shape"):
                obj_data["has_shape"] = True
            objects.append(obj_data)
        log_message(f"Listed {len(objects)} objects in document '{doc.Name}'")
        return {"result": "success", "objects": objects}
    except Exception as e:
        log_error(f"Error listing objects: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_get_object_properties(self, object_name, document_name=None):
    try:
        obj = self._get_object(object_name, document_name)
        props = {
            "name": obj.Name,
            "label": obj.Label,
            "type": obj.TypeId
        }
        if hasattr(obj, "Placement"):
            placement = obj.Placement
            props["placement"] = {
                "position": [placement.Base.x, placement.Base.y, placement.Base.z],
                "rotation": [placement.Rotation.Axis.x, placement.Rotation.Axis.y, placement.Rotation.Axis.z, placement.Rotation.Angle]
            }
        if hasattr(obj, "Shape"):
            shape = obj.Shape
            props["shape_info"] = {
                "vertices": len(shape.Vertexes),
                "edges": len(shape.Edges),
                "faces": len(shape.Faces),
                "solids": len(shape.Solids)
            }
        log_message(f"Got properties for object '{object_name}'")
        return {"result": "success", "properties": props}
    except Exception as e:
        log_error(f"Error getting object properties: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_delete_object(self, object_name, document_name=None):
    try:
        doc = self._get_document(document_name)
        doc.removeObject(object_name)
        log_message(f"Deleted object '{object_name}'")
        return {"result": "success"}
    except Exception as e:
        log_error(f"Error deleting object: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_get_bounding_box(self, object_name, document_name=None):
    try:
        obj = self._get_object(object_name, document_name)
        if not hasattr(obj, "Shape"):
            return {"result": "error", "message": f"Object '{object_name}' does not have a shape"}
        bbox = obj.Shape.BoundBox
        result = {
            "result": "success",
            "object_name": object_name,
            "bounding_box": {
                "xmin": bbox.XMin,
                "xmax": bbox.XMax,
                "ymin": bbox.YMin,
                "ymax": bbox.YMax,
                "zmin": bbox.ZMin,
                "zmax": bbox.ZMax,
                "center": [bbox.Center.x, bbox.Center.y, bbox.Center.z],
                "diagonal_length": bbox.DiagonalLength,
                "x_length": bbox.XLength,
                "y_length": bbox.YLength,
                "z_length": bbox.ZLength
            }
        }
        log_message(f"Got bounding box for '{object_name}'")
        return result
    except Exception as e:
        log_error(f"Error getting bounding box: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_measure_distance(self, obj1_name, obj2_name, document_name=None):
    try:
        obj1 = self._get_object(obj1_name, document_name)
        obj2 = self._get_object(obj2_name, document_name)
        if not hasattr(obj1, "Shape") or not hasattr(obj2, "Shape"):
            return {"result": "error", "message": "Both objects must have shapes"}
        distance_info = obj1.Shape.distToShape(obj2.Shape)
        distance = distance_info[0]
        result = {
            "result": "success",
            "obj1_name": obj1_name,
            "obj2_name": obj2_name,
            "distance": distance,
            "unit": "mm"
        }
        log_message(f"Measured distance between '{obj1_name}' and '{obj2_name}': {distance} mm")
        return result
    except Exception as e:
        log_error(f"Error measuring distance: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_get_volume(self, object_name, document_name=None):
    try:
        obj = self._get_object(object_name, document_name)
        if not hasattr(obj, "Shape"):
            return {"result": "error", "message": f"Object '{object_name}' does not have a shape"}
        volume = obj.Shape.Volume
        result = {
            "result": "success",
            "object_name": object_name,
            "volume": volume,
            "unit": "mm³"
        }
        log_message(f"Got volume for '{object_name}': {volume} mm³")
        return result
    except Exception as e:
        log_error(f"Error getting volume: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_get_surface_area(self, object_name, document_name=None):
    try:
        obj = self._get_object(object_name, document_name)
        if not hasattr(obj, "Shape"):
            return {"result": "error", "message": f"Object '{object_name}' does not have a shape"}
        area = obj.Shape.Area
        result = {
            "result": "success",
            "object_name": object_name,
            "surface_area": area,
            "unit": "mm²"
        }
        log_message(f"Got surface area for '{object_name}': {area} mm²")
        return result
    except Exception as e:
        log_error(f"Error getting surface area: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_get_center_of_mass(self, object_name, document_name=None):
    try:
        obj = self._get_object(object_name, document_name)
        if not hasattr(obj, "Shape"):
            return {"result": "error", "message": f"Object '{object_name}' does not have a shape"}
        com = obj.Shape.CenterOfMass
        result = {
            "result": "success",
            "object_name": object_name,
            "center_of_mass": {
                "x": com.x,
                "y": com.y,
                "z": com.z
            },
            "unit": "mm"
        }
        log_message(f"Got center of mass for '{object_name}': ({com.x}, {com.y}, {com.z})")
        return result
    except Exception as e:
        log_error(f"Error getting center of mass: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_get_mass_properties(self, object_name, density=1.0, document_name=None):
    try:
        obj = self._get_object(object_name, document_name)
        if not hasattr(obj, "Shape"):
            return {"result": "error", "message": f"Object '{object_name}' does not have a shape"}

        volume = obj.Shape.Volume
        # Convert mm³ to cm³ for mass calculation
        volume_cm3 = volume / 1000.0
        mass = volume_cm3 * density

        com = obj.Shape.CenterOfMass
        matrix = obj.Shape.MatrixOfInertia

        result = {
            "result": "success",
            "object_name": object_name,
            "density": density,
            "density_unit": "g/cm³",
            "volume": volume,
            "volume_unit": "mm³",
            "mass": mass,
            "mass_unit": "g",
            "center_of_mass": {
                "x": com.x,
                "y": com.y,
                "z": com.z
            },
            "inertia_tensor": {
                "A11": matrix.A11, "A12": matrix.A12, "A13": matrix.A13, "A14": matrix.A14,
                "A21": matrix.A21, "A22": matrix.A22, "A23": matrix.A23, "A24": matrix.A24,
                "A31": matrix.A31, "A32": matrix.A32, "A33": matrix.A33, "A34": matrix.A34,
                "A41": matrix.A41, "A42": matrix.A42, "A43": matrix.A43, "A44": matrix.A44
            }
        }
        log_message(f"Got mass properties for '{object_name}': mass={mass}g")
        return result
    except Exception as e:
        log_error(f"Error getting mass properties: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_check_solid_valid(self, object_name, document_name=None):
    try:
        obj = self._get_object(object_name, document_name)
        if not hasattr(obj, "Shape"):
            return {"result": "error", "message": f"Object '{object_name}' does not have a shape"}

        is_valid = obj.Shape.isValid()
        result = {
            "result": "success",
            "object_name": object_name,
            "is_valid": is_valid
        }

        if not is_valid:
            # Try to get error info
            check_result = obj.Shape.check()
            if check_result:
                result["error_info"] = check_result

        log_message(f"Checked solid validity for '{object_name}': {is_valid}")
        return result
    except Exception as e:
        log_error(f"Error checking solid validity: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

def handle_analyze_shape(self, object_name, document_name=None):
    try:
        obj = self._get_object(object_name, document_name)
        if not hasattr(obj, "Shape"):
            return {"result": "error", "message": f"Object '{object_name}' does not have a shape"}

        shape = obj.Shape
        bbox = shape.BoundBox
        com = shape.CenterOfMass

        result = {
            "result": "success",
            "object_name": object_name,
            "type": obj.TypeId,
            "geometry": {
                "vertices": len(shape.Vertexes),
                "edges": len(shape.Edges),
                "wires": len(shape.Wires),
                "faces": len(shape.Faces),
                "shells": len(shape.Shells),
                "solids": len(shape.Solids),
                "compounds": len(shape.Compounds)
            },
            "measurements": {
                "volume": shape.Volume,
                "volume_unit": "mm³",
                "surface_area": shape.Area,
                "surface_area_unit": "mm²"
            },
            "bounding_box": {
                "xmin": bbox.XMin,
                "xmax": bbox.XMax,
                "ymin": bbox.YMin,
                "ymax": bbox.YMax,
                "zmin": bbox.ZMin,
                "zmax": bbox.ZMax,
                "center": [bbox.Center.x, bbox.Center.y, bbox.Center.z],
                "x_length": bbox.XLength,
                "y_length": bbox.YLength,
                "z_length": bbox.ZLength,
                "diagonal_length": bbox.DiagonalLength
            },
            "center_of_mass": {
                "x": com.x,
                "y": com.y,
                "z": com.z
            },
            "validity": {
                "is_valid": shape.isValid(),
                "is_null": shape.isNull(),
                "is_closed": shape.isClosed() if hasattr(shape, 'isClosed') else None
            }
        }

        log_message(f"Analyzed shape for '{object_name}'")
        return result
    except Exception as e:
        log_error(f"Error analyzing shape: {str(e)}")
        return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}
