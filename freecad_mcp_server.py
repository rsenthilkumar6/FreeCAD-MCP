import os
import FreeCAD as App
import FreeCADGui as Gui
import json
import socket
import traceback
import time
import sys
import ast
from PySide2.QtCore import QTimer, QCoreApplication
from PySide2.QtWidgets import QMessageBox, QTextEdit, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide2.QtGui import QIcon

# Ensure module path
mod_dir = os.path.join(App.getUserAppDataDir(), "Mod", "freecad_mcp")
if mod_dir not in sys.path:
    sys.path.append(mod_dir)

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
    # Note: hasattr, getattr removed - safe and needed for FreeCAD API
    'setattr', 'delattr'
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

def log_message(message):
    message = f"[{time.ctime()}] {message}"
    App.Console.PrintMessage(message + "\n")
    if panel_instance and panel_instance.report_browser:
        current_text = panel_instance.report_browser.toPlainText().splitlines()
        current_text.append(message)
        if len(current_text) > FreeCADMCPServer().max_log_lines:
            current_text = current_text[-FreeCADMCPServer().max_log_lines:]
        panel_instance.report_browser.setPlainText("\n".join(current_text))
        panel_instance.report_browser.verticalScrollBar().setValue(
            panel_instance.report_browser.verticalScrollBar().maximum()
        )
    try:
        with open(FreeCADMCPServer().log_file, "a", encoding='utf-8', newline='\n') as f:
            f.write(f"{message}\n")
    except Exception as e:
        App.Console.PrintError(f"Log file write error: {str(e)}\n")

def log_error(message):
    message = f"[{time.ctime()}] ERROR: {message}"
    App.Console.PrintError(message + "\n")
    if panel_instance and panel_instance.report_browser:
        current_text = panel_instance.report_browser.toPlainText().splitlines()
        current_text.append(message)  # Fix: Use plain text format consistently
        if len(current_text) > FreeCADMCPServer().max_log_lines:
            current_text = current_text[-FreeCADMCPServer().max_log_lines:]
        panel_instance.report_browser.setPlainText("\n".join(current_text))
        panel_instance.report_browser.verticalScrollBar().setValue(
            panel_instance.report_browser.verticalScrollBar().maximum()
        )
    try:
        with open(FreeCADMCPServer().log_file, "a", encoding='utf-8', newline='\n') as f:
            f.write(f"{message}\n")
    except Exception as e:
        App.Console.PrintError(f"Log file write error: {str(e)}\n")

def capture_screenshot_base64(view_name="Isometric", width=None, height=None, focus_object=None):
    """
    Capture current FreeCAD view as base64-encoded PNG.

    Args:
        view_name: View orientation (Isometric, Front, Top, Right, Back, Left, Bottom)
        width: Screenshot width in pixels (optional)
        height: Screenshot height in pixels (optional)
        focus_object: Object name to focus on (optional, otherwise fits all)

    Returns:
        Base64-encoded PNG string or None if screenshot not available
    """
    import tempfile
    import base64

    # Check if GUI and view are available
    if not App.GuiUp or not Gui.ActiveDocument:
        log_error("Cannot capture screenshot: GUI or document not available")
        return None

    view = Gui.ActiveDocument.ActiveView
    if not view or not hasattr(view, 'saveImage'):
        log_error("Cannot capture screenshot: View does not support screenshots (e.g., TechDraw, Spreadsheet)")
        return None

    try:
        # Set view orientation
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
        else:
            log_error(f"Invalid view name: {view_name}, using current view")

        # Focus on specific object or fit all
        if focus_object and App.ActiveDocument:
            obj = App.ActiveDocument.getObject(focus_object)
            if obj:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(obj)
                Gui.SendMsgToActiveView("ViewSelection")
            else:
                view.fitAll()
        else:
            view.fitAll()

        # Create temporary file for screenshot
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

        try:
            # Save screenshot
            if width and height:
                view.saveImage(tmp_path, width, height)
            else:
                view.saveImage(tmp_path)

            # Read and encode as base64
            with open(tmp_path, "rb") as f:
                image_bytes = f.read()
                encoded = base64.b64encode(image_bytes).decode("utf-8")

            return encoded

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        log_error(f"Error capturing screenshot: {str(e)}")
        return None

class FreeCADMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.clients = []
        self.buffer = {}
        self.timer = None
        # Fix: Use more universal temporary directory path
        import tempfile
        self.log_file = os.path.join(tempfile.gettempdir(), "freecad_mcp_log.txt")
        self.max_log_lines = 100
        self.connection_timeout = 30  # Connection timeout setting
        self.max_clients = 5  # Maximum client connections
        self.buffer_size = 32768  # Buffer size
        self.max_buffer_size = 1024 * 1024  # Maximum buffer size (1MB)
        self.client_timeouts = {}  # Client timeout tracking

    def start(self):
        if not App.GuiUp:
            QMessageBox.critical(None, "Error", "FreeCAD GUI not initialized, please run FreeCAD in graphical interface")
            log_error("FreeCAD GUI not initialized, server failed to start")
            return
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.socket.setblocking(False)
            self.timer = QTimer()
            self.timer.timeout.connect(self._process_server)
            self.timer.start(50)
            log_message(f"FreeCAD MCP server started at {self.host}:{self.port}")
        except Exception as e:
            QMessageBox.critical(None, "Server Error", f"Server failed to start: {str(e)}\nPlease check if port {self.port} is already in use.")
            log_error(f"Server failed to start: {str(e)}")
            self.stop()

    def stop(self):
        self.running = False
        if self.timer:
            self.timer.stop()
            self.timer = None
        if self.socket:
            self.socket.close()
        for client in self.clients:
            client.close()
        self.socket = None
        self.clients = []
        self.buffer = {}
        log_message("FreeCAD MCP server stopped")

    def _process_server(self):
        if not self.running:
            return
        try:
            # Accept new connection
            try:
                client, address = self.socket.accept()
                # Check maximum connection limit
                if len(self.clients) >= self.max_clients:
                    log_message(f"Maximum connection limit reached, rejecting connection: {address}")
                    client.close()
                else:
                    client.setblocking(False)
                    client.settimeout(self.connection_timeout)  # Set timeout
                    self.clients.append(client)
                    self.buffer[client] = b''
                    self.client_timeouts[client] = time.time()  # Record connection time
                    log_message(f"Connected to client: {address}")
            except BlockingIOError:
                pass

            # Handle existing clients
            for client in self.clients[:]:
                try:
                    data = client.recv(self.buffer_size)
                    if data:
                        self.buffer[client] += data
                        # Check buffer size, prevent memory overflow
                        if len(self.buffer[client]) > self.max_buffer_size:
                            log_error("Client data too large, disconnecting")
                            self._cleanup_client(client)
                            continue

                        # Update client activity time
                        self.client_timeouts[client] = time.time()

                        try:
                            command = json.loads(self.buffer[client].decode('utf-8'))
                            self.buffer[client] = b''
                            response = self.execute_command(command)
                            response_json = json.dumps(response, ensure_ascii=False)
                            client.sendall(response_json.encode('utf-8'))
                        except json.JSONDecodeError:
                            # Data may be incomplete, continue waiting
                            pass
                        except UnicodeDecodeError as e:
                            log_error(f"Encoding error: {str(e)}")
                            self._cleanup_client(client)
                    else:
                        log_message("Client disconnected")
                        self._cleanup_client(client)
                except BlockingIOError:
                    pass
                except Exception as e:
                    log_error(f"Error processing client data: {str(e)}")
                    self._cleanup_client(client)

            # Check client timeout
            self._check_client_timeouts()
        except Exception as e:
            log_error(f"Server processing error: {str(e)}")

    def _cleanup_client(self, client):
        """Helper method to clean up client connections"""
        try:
            if client in self.clients:
                self.clients.remove(client)
            if client in self.buffer:
                del self.buffer[client]
            if client in self.client_timeouts:
                del self.client_timeouts[client]
            client.close()
        except Exception as e:
            log_error(f"Error cleaning up client connection: {str(e)}")

    def _check_client_timeouts(self):
        """Check and clean up timed out client connections"""
        current_time = time.time()
        timeout_clients = []

        for client, last_activity in self.client_timeouts.items():
            if current_time - last_activity > self.connection_timeout:
                timeout_clients.append(client)

        for client in timeout_clients:
            log_message("Client connection timed out, disconnecting")
            self._cleanup_client(client)

    def execute_command(self, command):
        command_type = command.get("type")
        params = command.get("params", {})
        if command_type == "create_macro":
            return self.handle_create_macro(params.get("macro_name"), params.get("template_type"))
        elif command_type == "update_macro":
            return self.handle_update_macro(params.get("macro_name"), params.get("code"))
        elif command_type == "run_macro":
            return self.handle_run_macro(params.get("macro_path"), params.get("params"))
        elif command_type == "validate_macro_code":
            return self.handle_validate_macro_code(params.get("macro_name"), params.get("code"))
        elif command_type == "set_view":
            return self.handle_set_view(params.get("view_type"))
        elif command_type == "get_report":
            return self.handle_get_report()
        elif command_type == "list_documents":
            return self.handle_list_documents()
        elif command_type == "get_active_document":
            return self.handle_get_active_document()
        elif command_type == "create_document":
            return self.handle_create_document(params.get("name"))
        elif command_type == "save_document":
            return self.handle_save_document(params.get("filename"))
        elif command_type == "close_document":
            return self.handle_close_document(params.get("name"))
        elif command_type == "list_objects":
            return self.handle_list_objects(params.get("document_name"))
        elif command_type == "get_object_properties":
            return self.handle_get_object_properties(params.get("object_name"), params.get("document_name"))
        elif command_type == "delete_object":
            return self.handle_delete_object(params.get("object_name"), params.get("document_name"))
        elif command_type == "export_stl":
            return self.handle_export_stl(params.get("object_name"), params.get("filepath"), params.get("mesh_deviation", 0.1))
        elif command_type == "export_step":
            return self.handle_export_step(params.get("filepath"), params.get("objects"))
        elif command_type == "export_iges":
            return self.handle_export_iges(params.get("filepath"), params.get("objects"))
        elif command_type == "export_obj":
            return self.handle_export_obj(params.get("object_name"), params.get("filepath"), params.get("mesh_deviation", 0.1))
        elif command_type == "export_svg":
            return self.handle_export_svg(params.get("filepath"), params.get("page_name"))
        elif command_type == "export_pdf":
            return self.handle_export_pdf(params.get("filepath"), params.get("page_name"))
        elif command_type == "get_bounding_box":
            return self.handle_get_bounding_box(params.get("object_name"), params.get("document_name"))
        elif command_type == "measure_distance":
            return self.handle_measure_distance(params.get("obj1_name"), params.get("obj2_name"), params.get("document_name"))
        elif command_type == "get_volume":
            return self.handle_get_volume(params.get("object_name"), params.get("document_name"))
        elif command_type == "get_surface_area":
            return self.handle_get_surface_area(params.get("object_name"), params.get("document_name"))
        elif command_type == "get_center_of_mass":
            return self.handle_get_center_of_mass(params.get("object_name"), params.get("document_name"))
        elif command_type == "get_mass_properties":
            return self.handle_get_mass_properties(params.get("object_name"), params.get("density", 1.0), params.get("document_name"))
        elif command_type == "check_solid_valid":
            return self.handle_check_solid_valid(params.get("object_name"), params.get("document_name"))
        elif command_type == "analyze_shape":
            return self.handle_analyze_shape(params.get("object_name"), params.get("document_name"))
        # Part Design operations
        elif command_type == "create_body":
            return self.handle_create_body(params.get("name"), params.get("document_name"))
        elif command_type == "create_sketch":
            return self.handle_create_sketch(params.get("body_name"), params.get("sketch_name"), params.get("plane"), params.get("document_name"))
        elif command_type == "add_circle":
            return self.handle_add_circle(params.get("sketch_name"), params.get("center_x"), params.get("center_y"), params.get("radius"), params.get("document_name"))
        elif command_type == "add_rectangle":
            return self.handle_add_rectangle(params.get("sketch_name"), params.get("x1"), params.get("y1"), params.get("x2"), params.get("y2"), params.get("document_name"))
        elif command_type == "add_line":
            return self.handle_add_line(params.get("sketch_name"), params.get("x1"), params.get("y1"), params.get("x2"), params.get("y2"), params.get("document_name"))
        elif command_type == "add_arc":
            return self.handle_add_arc(params.get("sketch_name"), params.get("center_x"), params.get("center_y"), params.get("radius"), params.get("start_angle"), params.get("end_angle"), params.get("document_name"))
        elif command_type == "add_constraint":
            return self.handle_add_constraint(params.get("sketch_name"), params.get("constraint_type"), params.get("constraint_params"), params.get("document_name"))
        elif command_type == "extrude_sketch":
            return self.handle_extrude_sketch(params.get("sketch_name"), params.get("length"), params.get("reversed"), params.get("document_name"))
        elif command_type == "revolve_sketch":
            return self.handle_revolve_sketch(params.get("sketch_name"), params.get("axis"), params.get("angle"), params.get("document_name"))
        elif command_type == "pocket_sketch":
            return self.handle_pocket_sketch(params.get("sketch_name"), params.get("length"), params.get("document_name"))
        elif command_type == "create_fillet":
            return self.handle_create_fillet(params.get("edge_indices"), params.get("radius"), params.get("base_object"), params.get("document_name"))
        elif command_type == "create_chamfer":
            return self.handle_create_chamfer(params.get("edge_indices"), params.get("size"), params.get("base_object"), params.get("document_name"))
        elif command_type == "create_pattern_linear":
            return self.handle_create_pattern_linear(params.get("feature_name"), params.get("direction"), params.get("length"), params.get("occurrences"), params.get("document_name"))
        elif command_type == "create_pattern_polar":
            return self.handle_create_pattern_polar(params.get("feature_name"), params.get("axis"), params.get("angle"), params.get("occurrences"), params.get("document_name"))
        # View management operations
        elif command_type == "set_camera_position":
            return self.handle_set_camera_position(params)
        elif command_type == "set_view_direction":
            return self.handle_set_view_direction(params.get("direction"))
        elif command_type == "zoom_to_fit":
            return self.handle_zoom_to_fit()
        elif command_type == "zoom_to_selection":
            return self.handle_zoom_to_selection(params.get("object_names"))
        elif command_type == "set_perspective":
            return self.handle_set_perspective(params.get("enabled"))
        elif command_type == "capture_screenshot":
            return self.handle_capture_screenshot(params)
        elif command_type == "rotate_view":
            return self.handle_rotate_view(params.get("axis"), params.get("angle"))
        elif command_type == "set_render_style":
            return self.handle_set_render_style(params.get("style"))
        elif command_type == "toggle_axis":
            return self.handle_toggle_axis(params.get("visible"))
        elif command_type == "set_background_color":
            return self.handle_set_background_color(params)
        # Phase 1: Visual feedback tools
        elif command_type == "get_view":
            return self.handle_get_view(params)
        elif command_type == "get_screenshot":
            return self.handle_get_screenshot(params)
        # Phase 2: Parts library
        elif command_type == "get_parts_list":
            return self.handle_get_parts_list()
        elif command_type == "insert_part_from_library":
            return self.handle_insert_part_from_library(params.get("relative_path"))
        # Phase 3: Flexible code execution
        elif command_type == "execute_code":
            return self.handle_execute_code(params.get("code"), params.get("validate", True))
        return {"result": "error", "message": f"Unknown command: {command_type}"}

    def handle_create_macro(self, macro_name, template_type="default"):
        try:
            macro_dir = App.getUserMacroDir()
            macro_path = os.path.join(macro_dir, f"{macro_name}.FCMacro")
            template_map = {
                "default": "# FreeCAD Macro\n",
                "basic": "import FreeCAD as App\nimport FreeCADGui as Gui\n\n",
                "part": "import FreeCAD as App\nimport FreeCADGui as Gui\nimport Part\n\n",
                "sketch": "import FreeCAD as App\nimport FreeCADGui as Gui\nimport Sketcher\n\n"
            }
            template = template_map.get(template_type, "# FreeCAD Macro\n")
            with open(macro_path, "w", encoding='utf-8') as f:
                f.write(template)
            log_message(f"Macro file created successfully: {macro_path}")
            return {"result": "success", "message": f"Macro file created successfully: {macro_path}"}
        except Exception as e:
            log_error(f"Error creating macro file: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_update_macro(self, macro_name, code):
        try:
            macro_dir = App.getUserMacroDir()
            macro_path = os.path.join(macro_dir, f"{macro_name}.FCMacro")
            with open(macro_path, "w", encoding='utf-8') as f:
                f.write(code)
            log_message(f"Macro file updated successfully: {macro_path}")
            return {"result": "success", "message": f"Macro file updated successfully: {macro_path}"}
        except Exception as e:
            log_error(f"Error updating macro file: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_run_macro(self, macro_path, params):
        try:
            # Smart path handling - support relative and absolute paths
            original_macro_path = macro_path
            resolved_path = None

            # Path resolution strategy
            search_paths = []

            if os.path.isabs(macro_path):
                # Use absolute path directly
                search_paths.append(macro_path)
            else:
                # Multiple search strategy for relative paths
                macro_dir = App.getUserMacroDir()

                # 1. Search in FreeCAD macro directory
                search_paths.append(os.path.join(macro_dir, macro_path))

                # 2. If no .FCMacro extension, automatically add it
                if not macro_path.endswith('.FCMacro'):
                    search_paths.append(os.path.join(macro_dir, f"{macro_path}.FCMacro"))

                # 3. Search in current working directory
                search_paths.append(os.path.abspath(macro_path))

                # 4. Search in project directory
                project_dir = os.path.dirname(__file__)
                search_paths.append(os.path.join(project_dir, macro_path))

            # Search files by priority
            for path in search_paths:
                if os.path.exists(path):
                    resolved_path = path
                    log_message(f"Found macro file: {resolved_path}")
                    break

            # Validate macro file path
            if not resolved_path:
                search_info = "\n".join([f"  - {path}" for path in search_paths])
                log_error(f"Macro file does not exist: {original_macro_path}\nSearch paths:\n{search_info}")
                return {"result": "error", "message": f"Macro file does not exist: {original_macro_path}"}

            macro_path = resolved_path

            if not macro_path.endswith('.FCMacro'):
                log_error(f"Invalid macro file extension: {macro_path}")
                return {"result": "error", "message": "Macro file must end with .FCMacro"}

            # Get and validate document name
            doc_name = self._get_document_name(macro_path, params)

            # Document management
            doc_created = False
            try:
                existing_doc = App.getDocument(doc_name) if doc_name in App.listDocuments() else None

                if existing_doc:
                    App.setActiveDocument(doc_name)
                    log_message(f"Using existing document: {doc_name}")
                else:
                    App.newDocument(doc_name)
                    App.setActiveDocument(doc_name)
                    doc_created = True
                    log_message(f"Created new document: {doc_name}")

                # Ensure active document is valid
                if not App.ActiveDocument:
                    raise Exception("Unable to set active document")
                
                # Execute macro file with parameter injection
                self._execute_macro_file(macro_path, params)
                
                # Recompute and update view
                self._update_document_view()
                
                log_message(f"Macro file {macro_path} executed successfully in document {doc_name}")
                return {"result": "success", "message": f"Macro executed successfully in document {doc_name}", "document": doc_name}
                
            except Exception as e:
                # If newly created document and execution failed, clean up document
                if doc_created and App.ActiveDocument and App.ActiveDocument.Name == doc_name:
                    try:
                        App.closeDocument(doc_name)
                        log_message(f"Cleaned up failed document: {doc_name}")
                    except:
                        pass
                raise e
                
        except Exception as e:
            log_error(f"Error running macro: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def _get_document_name(self, macro_path, params):
        """Get and validate document name"""
        import re
        
        if params and "doc_name" in params and params["doc_name"]:
            doc_name = params["doc_name"]
        elif params is None and App.ActiveDocument:
            # GUI call, use current active document
            doc_name = App.ActiveDocument.Name
        else:
            # Use macro file name
            doc_name = os.path.splitext(os.path.basename(macro_path))[0]
        
        # Ensure document name is legal
        doc_name = re.sub(r'[^\w\-]', '_', doc_name)
        if not doc_name or doc_name.isdigit():
            doc_name = f"Document_{doc_name}"
        
        return doc_name

    def _execute_macro_file(self, macro_path, params=None):
        """Safely execute macro file with parameter injection"""
        try:
            with open(macro_path, 'r', encoding='utf-8') as f:
                macro_code = f.read()

            # Inject parameters into code if provided
            if params:
                # Filter out special parameters (doc_name, etc)
                user_params = {k: v for k, v in params.items() if k not in ['doc_name']}
                if user_params:
                    param_code = "\n".join([
                        f"{key} = {repr(value)}" for key, value in user_params.items()
                    ])
                    macro_code = param_code + "\n\n" + macro_code
                    log_message(f"Injected parameters: {list(user_params.keys())}")

            # Validate code safety before execution
            is_safe, error_message = validate_code_safety(macro_code)
            if not is_safe:
                log_error(f"Code validation failed: {error_message}")
                raise Exception(f"Code validation failed: {error_message}")

            log_message("Code validation passed")

            # Create safe execution environment
            safe_globals = {
                "App": App,
                "Gui": Gui,
                "__name__": "__main__",
                "__file__": macro_path
            }

            # Add common modules
            import Part, Draft, Sketcher, math
            safe_globals.update({
                "Part": Part,
                "Draft": Draft,
                "Sketcher": Sketcher,
                "math": math
            })

            # Add params dict to globals for direct access
            if params:
                safe_globals["params"] = {k: v for k, v in params.items() if k not in ['doc_name']}

            exec(macro_code, safe_globals)

        except Exception as e:
            raise Exception(f"Macro execution failed: {str(e)}")

    def _update_document_view(self):
        """Update document view"""
        try:
            if App.ActiveDocument:
                App.ActiveDocument.recompute()
            
            if App.GuiUp and Gui.ActiveDocument and hasattr(Gui.ActiveDocument, 'ActiveView') and Gui.ActiveDocument.ActiveView:
                Gui.ActiveDocument.ActiveView.viewAxometric()
                Gui.ActiveDocument.ActiveView.fitAll()
                Gui.updateGui()
        except Exception as e:
            log_error(f"Failed to update view: {str(e)}")

    def handle_validate_macro_code(self, macro_name=None, code=None):
        try:
            if not code:
                if not macro_name or not os.path.exists(os.path.join(App.getUserMacroDir(), f"{macro_name}.FCMacro")):
                    log_error("Macro file name invalid or file does not exist")
                    return {"result": "error", "message": "Macro file name invalid or file does not exist"}
                with open(os.path.join(App.getUserMacroDir(), f"{macro_name}.FCMacro"), 'r', encoding='utf-8') as f:
                    code = f.read()

            # Validate code safety
            is_safe, error_message = validate_code_safety(code)
            if not is_safe:
                log_error(f"Code validation failed: {error_message}")
                return {"result": "error", "message": f"Code validation failed: {error_message}"}

            # If validation passes, do a test execution
            temp_doc = App.newDocument("TempValidateDoc")
            try:
                exec(code, {"App": App, "Gui": Gui})
                log_message("Macro code validation successful")
                return {"result": "success", "message": "Macro code validation successful"}
            finally:
                App.closeDocument("TempValidateDoc")
        except Exception as e:
            log_error(f"Error validating macro code: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_set_view(self, view_type):
        try:
            # Check GUI and document status
            if not App.GuiUp:
                log_error("FreeCAD GUI not started")
                return {"result": "error", "message": "FreeCAD GUI not started, cannot adjust view"}

            if not App.ActiveDocument:
                log_error("No active document")
                return {"result": "error", "message": "No active document, please create or open a document first"}
            
            if not Gui.ActiveDocument:
                log_error("GUI document not initialized")
                return {"result": "error", "message": "GUI document not initialized"}
            
            if not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                log_error("No active view")
                return {"result": "error", "message": "No active view"}
            view = Gui.ActiveDocument.ActiveView
            view_map = {
                "1": ("front", view.viewFront),
                "2": ("top", view.viewTop),
                "3": ("right", view.viewRight),
                "7": ("isometric", view.viewIsometric)
            }
            if view_type not in view_map:
                log_error(f"Invalid view type: {view_type}")
                return {"result": "error", "message": f"Invalid view type: {view_type}"}
            view_name, view_func = view_map[view_type]
            def set_view_in_main_thread():
                try:
                    log_message(f"Attempting to adjust to {view_name} view (view_type: {view_type})")
                    view_func()
                    view.fitAll()
                    Gui.updateGui()
                    log_message(f"Successfully adjusted to {view_name} view")
                except Exception as e:
                    log_error(f"View adjustment failed: {str(e)}")
                    raise
            QTimer.singleShot(100, set_view_in_main_thread)
            return {"result": "success", "view_name": view_name}
        except Exception as e:
            log_error(f"Error adjusting view: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_get_report(self):
        try:
            if not panel_instance or not panel_instance.report_browser:
                show_panel()
            report = panel_instance.report_browser.toPlainText()
            log_message("Get report")
            return {"result": "success", "report": report}
        except Exception as e:
            log_error(f"Error getting report: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_export_stl(self, object_name, filepath, mesh_deviation):
        try:
            if not App.ActiveDocument:
                return {"result": "error", "message": "No active document"}
            if not os.path.isabs(filepath):
                return {"result": "error", "message": "filepath must be an absolute path"}

            obj = App.ActiveDocument.getObject(object_name)
            if not obj:
                return {"result": "error", "message": f"Object '{object_name}' not found"}
            if not hasattr(obj, 'Shape') or not obj.Shape:
                return {"result": "error", "message": f"Object '{object_name}' has no shape to export"}

            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            import Mesh
            mesh = Mesh.Mesh()
            mesh.addFacets(obj.Shape.tessellate(mesh_deviation))
            mesh.write(filepath)

            log_message(f"Exported '{object_name}' to STL: {filepath}")
            return {"result": "success", "filepath": filepath, "message": f"Exported to {filepath}"}
        except Exception as e:
            log_error(f"Error exporting STL: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_export_step(self, filepath, objects):
        try:
            if not App.ActiveDocument:
                return {"result": "error", "message": "No active document"}
            if not os.path.isabs(filepath):
                return {"result": "error", "message": "filepath must be an absolute path"}

            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            if objects:
                object_list = [obj.strip() for obj in objects.split(',')]
                export_objects = []
                for obj_name in object_list:
                    obj = App.ActiveDocument.getObject(obj_name)
                    if not obj:
                        return {"result": "error", "message": f"Object '{obj_name}' not found"}
                    export_objects.append(obj)
            else:
                export_objects = App.ActiveDocument.Objects

            if not export_objects:
                return {"result": "error", "message": "No objects to export"}

            import Import
            Import.export(export_objects, filepath)

            log_message(f"Exported {len(export_objects)} objects to STEP: {filepath}")
            return {"result": "success", "filepath": filepath, "message": f"Exported to {filepath}"}
        except Exception as e:
            log_error(f"Error exporting STEP: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_export_iges(self, filepath, objects):
        try:
            if not App.ActiveDocument:
                return {"result": "error", "message": "No active document"}
            if not os.path.isabs(filepath):
                return {"result": "error", "message": "filepath must be an absolute path"}

            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            if objects:
                object_list = [obj.strip() for obj in objects.split(',')]
                export_objects = []
                for obj_name in object_list:
                    obj = App.ActiveDocument.getObject(obj_name)
                    if not obj:
                        return {"result": "error", "message": f"Object '{obj_name}' not found"}
                    export_objects.append(obj)
            else:
                export_objects = App.ActiveDocument.Objects

            if not export_objects:
                return {"result": "error", "message": "No objects to export"}

            import Import
            Import.export(export_objects, filepath)

            log_message(f"Exported {len(export_objects)} objects to IGES: {filepath}")
            return {"result": "success", "filepath": filepath, "message": f"Exported to {filepath}"}
        except Exception as e:
            log_error(f"Error exporting IGES: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_export_obj(self, object_name, filepath, mesh_deviation):
        try:
            if not App.ActiveDocument:
                return {"result": "error", "message": "No active document"}
            if not os.path.isabs(filepath):
                return {"result": "error", "message": "filepath must be an absolute path"}

            obj = App.ActiveDocument.getObject(object_name)
            if not obj:
                return {"result": "error", "message": f"Object '{object_name}' not found"}
            if not hasattr(obj, 'Shape') or not obj.Shape:
                return {"result": "error", "message": f"Object '{object_name}' has no shape to export"}

            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            import Mesh
            mesh = Mesh.Mesh()
            mesh.addFacets(obj.Shape.tessellate(mesh_deviation))
            mesh.write(filepath)

            log_message(f"Exported '{object_name}' to OBJ: {filepath}")
            return {"result": "success", "filepath": filepath, "message": f"Exported to {filepath}"}
        except Exception as e:
            log_error(f"Error exporting OBJ: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_export_svg(self, filepath, page_name):
        try:
            if not App.ActiveDocument:
                return {"result": "error", "message": "No active document"}
            if not os.path.isabs(filepath):
                return {"result": "error", "message": "filepath must be an absolute path"}

            pages = [obj for obj in App.ActiveDocument.Objects if obj.TypeId == 'TechDraw::DrawPage']
            if not pages:
                return {"result": "error", "message": "No TechDraw pages found in document"}

            if page_name:
                page = App.ActiveDocument.getObject(page_name)
                if not page or page.TypeId != 'TechDraw::DrawPage':
                    return {"result": "error", "message": f"TechDraw page '{page_name}' not found"}
            else:
                page = pages[0]

            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            import TechDraw
            page.ViewObject.saveAsSvg(filepath)

            log_message(f"Exported TechDraw page '{page.Name}' to SVG: {filepath}")
            return {"result": "success", "filepath": filepath, "message": f"Exported to {filepath}"}
        except Exception as e:
            log_error(f"Error exporting SVG: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_export_pdf(self, filepath, page_name):
        try:
            if not App.ActiveDocument:
                return {"result": "error", "message": "No active document"}
            if not os.path.isabs(filepath):
                return {"result": "error", "message": "filepath must be an absolute path"}

            pages = [obj for obj in App.ActiveDocument.Objects if obj.TypeId == 'TechDraw::DrawPage']
            if not pages:
                return {"result": "error", "message": "No TechDraw pages found in document"}

            if page_name:
                page = App.ActiveDocument.getObject(page_name)
                if not page or page.TypeId != 'TechDraw::DrawPage':
                    return {"result": "error", "message": f"TechDraw page '{page_name}' not found"}
            else:
                page = pages[0]

            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            import TechDraw
            page.ViewObject.saveAsPdf(filepath)

            log_message(f"Exported TechDraw page '{page.Name}' to PDF: {filepath}")
            return {"result": "success", "filepath": filepath, "message": f"Exported to {filepath}"}
        except Exception as e:
            log_error(f"Error exporting PDF: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    # View management handlers
    def handle_set_camera_position(self, params):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            view = Gui.ActiveDocument.ActiveView
            from FreeCAD import Base

            x, y, z = params.get("x"), params.get("y"), params.get("z")
            look_at_x = params.get("look_at_x", 0.0)
            look_at_y = params.get("look_at_y", 0.0)
            look_at_z = params.get("look_at_z", 0.0)

            camera_pos = Base.Vector(x, y, z)
            look_at = Base.Vector(look_at_x, look_at_y, look_at_z)
            direction = (look_at - camera_pos).normalize()

            view.viewPosition(camera_pos, direction)
            log_message(f"Set camera position to ({x}, {y}, {z}) looking at ({look_at_x}, {look_at_y}, {look_at_z})")
            return {"result": "success", "message": "Camera position set"}
        except Exception as e:
            log_error(f"Error setting camera position: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_set_view_direction(self, direction):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            view = Gui.ActiveDocument.ActiveView
            view_map = {
                "front": view.viewFront,
                "back": view.viewBack,
                "top": view.viewTop,
                "bottom": view.viewBottom,
                "left": view.viewLeft,
                "right": view.viewRight,
                "iso": view.viewIsometric
            }

            if direction not in view_map:
                return {"result": "error", "message": f"Invalid direction: {direction}"}

            view_map[direction]()
            view.fitAll()
            Gui.updateGui()
            log_message(f"Set view direction to {direction}")
            return {"result": "success", "message": f"View set to {direction}"}
        except Exception as e:
            log_error(f"Error setting view direction: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_zoom_to_fit(self):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            view = Gui.ActiveDocument.ActiveView
            view.fitAll()
            Gui.updateGui()
            log_message("Zoomed to fit all objects")
            return {"result": "success", "message": "Zoomed to fit"}
        except Exception as e:
            log_error(f"Error zooming to fit: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_zoom_to_selection(self, object_names):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not App.ActiveDocument:
                return {"result": "error", "message": "No active document"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            names = [name.strip() for name in object_names.split(",")]
            objects = []
            for name in names:
                obj = App.ActiveDocument.getObject(name)
                if obj:
                    objects.append(obj)

            if not objects:
                return {"result": "error", "message": "No valid objects found"}

            Gui.Selection.clearSelection()
            for obj in objects:
                Gui.Selection.addSelection(obj)

            Gui.SendMsgToActiveView("ViewSelection")
            Gui.updateGui()
            log_message(f"Zoomed to selection: {object_names}")
            return {"result": "success", "message": f"Zoomed to {len(objects)} objects"}
        except Exception as e:
            log_error(f"Error zooming to selection: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_set_perspective(self, enabled):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            view = Gui.ActiveDocument.ActiveView
            camera_type = "Perspective" if enabled else "Orthographic"
            view.setCameraType(camera_type)
            Gui.updateGui()
            log_message(f"Set camera type to {camera_type}")
            return {"result": "success", "message": f"Camera set to {camera_type}"}
        except Exception as e:
            log_error(f"Error setting perspective: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_capture_screenshot(self, params):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            filepath = params.get("filepath")
            width = params.get("width", 800)
            height = params.get("height", 600)
            transparent = params.get("transparent_background", False)

            view = Gui.ActiveDocument.ActiveView

            if transparent and filepath.lower().endswith('.png'):
                view.saveImage(filepath, width, height, 'Transparent')
            else:
                view.saveImage(filepath, width, height)

            log_message(f"Screenshot saved to {filepath}")
            return {"result": "success", "filepath": filepath, "message": f"Screenshot saved to {filepath}"}
        except Exception as e:
            log_error(f"Error capturing screenshot: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_rotate_view(self, axis, angle):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            view = Gui.ActiveDocument.ActiveView
            from FreeCAD import Base
            import math

            angle_rad = math.radians(angle)

            if axis == "x":
                rotation = Base.Rotation(Base.Vector(1, 0, 0), angle_rad)
            elif axis == "y":
                rotation = Base.Rotation(Base.Vector(0, 1, 0), angle_rad)
            elif axis == "z":
                rotation = Base.Rotation(Base.Vector(0, 0, 1), angle_rad)
            else:
                return {"result": "error", "message": f"Invalid axis: {axis}"}

            camera = view.getCameraNode()
            orientation = camera.orientation.getValue()
            q = Base.Rotation(orientation[0], orientation[1], orientation[2], orientation[3])
            q = q.multiply(rotation)
            camera.orientation.setValue(q.Q)

            Gui.updateGui()
            log_message(f"Rotated view {angle} degrees around {axis} axis")
            return {"result": "success", "message": f"View rotated {angle} degrees around {axis} axis"}
        except Exception as e:
            log_error(f"Error rotating view: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_set_render_style(self, style):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            view = Gui.ActiveDocument.ActiveView
            view.setRenderType(style)
            Gui.updateGui()
            log_message(f"Set render style to {style}")
            return {"result": "success", "message": f"Render style set to {style}"}
        except Exception as e:
            log_error(f"Error setting render style: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_toggle_axis(self, visible):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            view = Gui.ActiveDocument.ActiveView
            view.setAxisCross(visible)
            Gui.updateGui()
            status = "shown" if visible else "hidden"
            log_message(f"Coordinate axis {status}")
            return {"result": "success", "message": f"Axis {status}"}
        except Exception as e:
            log_error(f"Error toggling axis: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_set_background_color(self, params):
        try:
            if not App.GuiUp:
                return {"result": "error", "message": "FreeCAD GUI not started"}
            if not Gui.ActiveDocument or not hasattr(Gui.ActiveDocument, 'ActiveView') or not Gui.ActiveDocument.ActiveView:
                return {"result": "error", "message": "No active view"}

            r = params.get("r") / 255.0
            g = params.get("g") / 255.0
            b = params.get("b") / 255.0

            view = Gui.ActiveDocument.ActiveView
            view.setBackgroundColor(r, g, b)
            Gui.updateGui()
            log_message(f"Set background color to RGB({params.get('r')}, {params.get('g')}, {params.get('b')})")
            return {"result": "success", "message": "Background color set"}
        except Exception as e:
            log_error(f"Error setting background color: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    # ============================================================================
    # Part Design Operations Handlers
    # ============================================================================

    def _get_document(self, document_name):
        """Helper to get document by name or active document"""
        if document_name and document_name in App.listDocuments():
            return App.getDocument(document_name)
        return App.ActiveDocument

    def handle_create_body(self, name, document_name=None):
        """Create a PartDesign Body container"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            body = doc.addObject('PartDesign::Body', name)
            doc.recompute()
            log_message(f"Created Body: {name}")
            return {"result": "success", "body_name": body.Name, "message": f"Body '{body.Name}' created"}
        except Exception as e:
            log_error(f"Error creating body: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_create_sketch(self, body_name, sketch_name, plane, document_name=None):
        """Create a sketch on a body attached to a plane"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            body = doc.getObject(body_name)
            if not body or body.TypeId != 'PartDesign::Body':
                return {"result": "error", "message": f"Body '{body_name}' not found"}

            sketch = body.newObject('Sketcher::SketchObject', sketch_name)

            # Map plane to attachment
            plane_map = {
                'XY': ('XY_Plane', App.Placement()),
                'XZ': ('XZ_Plane', App.Placement(App.Vector(0,0,0), App.Rotation(App.Vector(1,0,0), -90))),
                'YZ': ('YZ_Plane', App.Placement(App.Vector(0,0,0), App.Rotation(App.Vector(0,1,0), 90)))
            }

            if plane in plane_map:
                _, placement = plane_map[plane]
                sketch.Placement = placement
                sketch.MapMode = 'FlatFace'

            doc.recompute()
            log_message(f"Created Sketch: {sketch_name} on {plane} plane")
            return {"result": "success", "sketch_name": sketch.Name, "message": f"Sketch '{sketch.Name}' created"}
        except Exception as e:
            log_error(f"Error creating sketch: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_add_circle(self, sketch_name, center_x, center_y, radius, document_name=None):
        """Add a circle to a sketch"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            sketch = doc.getObject(sketch_name)
            if not sketch or sketch.TypeId != 'Sketcher::SketchObject':
                return {"result": "error", "message": f"Sketch '{sketch_name}' not found"}

            import Part
            circle = Part.Circle(App.Vector(center_x, center_y, 0), App.Vector(0, 0, 1), radius)
            sketch.addGeometry(circle, False)
            doc.recompute()

            log_message(f"Added circle to sketch '{sketch_name}'")
            return {"result": "success", "message": f"Circle added to sketch '{sketch_name}'"}
        except Exception as e:
            log_error(f"Error adding circle: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_add_rectangle(self, sketch_name, x1, y1, x2, y2, document_name=None):
        """Add a rectangle to a sketch"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            sketch = doc.getObject(sketch_name)
            if not sketch or sketch.TypeId != 'Sketcher::SketchObject':
                return {"result": "error", "message": f"Sketch '{sketch_name}' not found"}

            import Part, Sketcher
            # Create rectangle as 4 lines
            p1 = App.Vector(x1, y1, 0)
            p2 = App.Vector(x2, y1, 0)
            p3 = App.Vector(x2, y2, 0)
            p4 = App.Vector(x1, y2, 0)

            l1 = Part.LineSegment(p1, p2)
            l2 = Part.LineSegment(p2, p3)
            l3 = Part.LineSegment(p3, p4)
            l4 = Part.LineSegment(p4, p1)

            g1 = sketch.addGeometry(l1, False)
            g2 = sketch.addGeometry(l2, False)
            g3 = sketch.addGeometry(l3, False)
            g4 = sketch.addGeometry(l4, False)

            # Add coincident constraints
            sketch.addConstraint(Sketcher.Constraint('Coincident', g1, 2, g2, 1))
            sketch.addConstraint(Sketcher.Constraint('Coincident', g2, 2, g3, 1))
            sketch.addConstraint(Sketcher.Constraint('Coincident', g3, 2, g4, 1))
            sketch.addConstraint(Sketcher.Constraint('Coincident', g4, 2, g1, 1))

            doc.recompute()
            log_message(f"Added rectangle to sketch '{sketch_name}'")
            return {"result": "success", "message": f"Rectangle added to sketch '{sketch_name}'"}
        except Exception as e:
            log_error(f"Error adding rectangle: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_add_line(self, sketch_name, x1, y1, x2, y2, document_name=None):
        """Add a line to a sketch"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            sketch = doc.getObject(sketch_name)
            if not sketch or sketch.TypeId != 'Sketcher::SketchObject':
                return {"result": "error", "message": f"Sketch '{sketch_name}' not found"}

            import Part
            line = Part.LineSegment(App.Vector(x1, y1, 0), App.Vector(x2, y2, 0))
            sketch.addGeometry(line, False)
            doc.recompute()

            log_message(f"Added line to sketch '{sketch_name}'")
            return {"result": "success", "message": f"Line added to sketch '{sketch_name}'"}
        except Exception as e:
            log_error(f"Error adding line: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_add_arc(self, sketch_name, center_x, center_y, radius, start_angle, end_angle, document_name=None):
        """Add an arc to a sketch"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            sketch = doc.getObject(sketch_name)
            if not sketch or sketch.TypeId != 'Sketcher::SketchObject':
                return {"result": "error", "message": f"Sketch '{sketch_name}' not found"}

            import Part, math
            center = App.Vector(center_x, center_y, 0)
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)

            arc = Part.ArcOfCircle(
                Part.Circle(center, App.Vector(0, 0, 1), radius),
                start_rad, end_rad
            )
            sketch.addGeometry(arc, False)
            doc.recompute()

            log_message(f"Added arc to sketch '{sketch_name}'")
            return {"result": "success", "message": f"Arc added to sketch '{sketch_name}'"}
        except Exception as e:
            log_error(f"Error adding arc: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_add_constraint(self, sketch_name, constraint_type, constraint_params, document_name=None):
        """Add a constraint to a sketch"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            sketch = doc.getObject(sketch_name)
            if not sketch or sketch.TypeId != 'Sketcher::SketchObject':
                return {"result": "error", "message": f"Sketch '{sketch_name}' not found"}

            import Sketcher

            # Map constraint types to Sketcher constraints
            if constraint_type.lower() == 'horizontal':
                geo_idx = constraint_params.get('geometry_index', 0)
                sketch.addConstraint(Sketcher.Constraint('Horizontal', geo_idx))
            elif constraint_type.lower() == 'vertical':
                geo_idx = constraint_params.get('geometry_index', 0)
                sketch.addConstraint(Sketcher.Constraint('Vertical', geo_idx))
            elif constraint_type.lower() == 'radius':
                geo_idx = constraint_params.get('geometry_index', 0)
                value = constraint_params.get('value', 0)
                sketch.addConstraint(Sketcher.Constraint('Radius', geo_idx, value))
            elif constraint_type.lower() == 'distance':
                geo_idx1 = constraint_params.get('geometry_index1', 0)
                geo_idx2 = constraint_params.get('geometry_index2', 1)
                value = constraint_params.get('value', 0)
                sketch.addConstraint(Sketcher.Constraint('Distance', geo_idx1, geo_idx2, value))
            else:
                return {"result": "error", "message": f"Unsupported constraint type: {constraint_type}"}

            doc.recompute()
            log_message(f"Added {constraint_type} constraint to sketch '{sketch_name}'")
            return {"result": "success", "message": f"Constraint added to sketch '{sketch_name}'"}
        except Exception as e:
            log_error(f"Error adding constraint: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_extrude_sketch(self, sketch_name, length, reversed, document_name=None):
        """Create a pad (extrusion) from a sketch"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            sketch = doc.getObject(sketch_name)
            if not sketch or sketch.TypeId != 'Sketcher::SketchObject':
                return {"result": "error", "message": f"Sketch '{sketch_name}' not found"}

            pad = doc.addObject('PartDesign::Pad', 'Pad')
            pad.Profile = sketch
            pad.Length = length
            pad.Reversed = reversed if reversed else False
            doc.recompute()

            log_message(f"Extruded sketch '{sketch_name}' with length {length}")
            return {"result": "success", "pad_name": pad.Name, "message": f"Pad '{pad.Name}' created"}
        except Exception as e:
            log_error(f"Error extruding sketch: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_revolve_sketch(self, sketch_name, axis, angle, document_name=None):
        """Create a revolution from a sketch"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            sketch = doc.getObject(sketch_name)
            if not sketch or sketch.TypeId != 'Sketcher::SketchObject':
                return {"result": "error", "message": f"Sketch '{sketch_name}' not found"}

            revolution = doc.addObject('PartDesign::Revolution', 'Revolution')
            revolution.Profile = sketch
            revolution.Angle = angle

            # Set axis
            axis_map = {
                'X': (App.Vector(1, 0, 0), App.Vector(0, 0, 0)),
                'Y': (App.Vector(0, 1, 0), App.Vector(0, 0, 0)),
                'Z': (App.Vector(0, 0, 1), App.Vector(0, 0, 0))
            }
            if axis in axis_map:
                axis_dir, axis_base = axis_map[axis]
                revolution.ReferenceAxis = (sketch, [axis])

            doc.recompute()
            log_message(f"Revolved sketch '{sketch_name}' around {axis} axis by {angle} degrees")
            return {"result": "success", "revolution_name": revolution.Name, "message": f"Revolution '{revolution.Name}' created"}
        except Exception as e:
            log_error(f"Error revolving sketch: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_pocket_sketch(self, sketch_name, length, document_name=None):
        """Create a pocket (cut) from a sketch"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            sketch = doc.getObject(sketch_name)
            if not sketch or sketch.TypeId != 'Sketcher::SketchObject':
                return {"result": "error", "message": f"Sketch '{sketch_name}' not found"}

            pocket = doc.addObject('PartDesign::Pocket', 'Pocket')
            pocket.Profile = sketch
            pocket.Length = length
            doc.recompute()

            log_message(f"Created pocket from sketch '{sketch_name}' with depth {length}")
            return {"result": "success", "pocket_name": pocket.Name, "message": f"Pocket '{pocket.Name}' created"}
        except Exception as e:
            log_error(f"Error creating pocket: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_create_fillet(self, edge_indices, radius, base_object, document_name=None):
        """Add fillet to edges"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            obj = doc.getObject(base_object)
            if not obj:
                return {"result": "error", "message": f"Object '{base_object}' not found"}

            fillet = doc.addObject('PartDesign::Fillet', 'Fillet')
            fillet.Base = obj

            # Parse edge indices
            edges = [int(idx.strip()) for idx in edge_indices.split(',')]
            fillet.Edges = [(obj, f'Edge{idx}') for idx in edges]
            fillet.Radius = radius

            doc.recompute()
            log_message(f"Created fillet on edges {edge_indices} with radius {radius}")
            return {"result": "success", "fillet_name": fillet.Name, "message": f"Fillet '{fillet.Name}' created"}
        except Exception as e:
            log_error(f"Error creating fillet: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_create_chamfer(self, edge_indices, size, base_object, document_name=None):
        """Add chamfer to edges"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            obj = doc.getObject(base_object)
            if not obj:
                return {"result": "error", "message": f"Object '{base_object}' not found"}

            chamfer = doc.addObject('PartDesign::Chamfer', 'Chamfer')
            chamfer.Base = obj

            # Parse edge indices
            edges = [int(idx.strip()) for idx in edge_indices.split(',')]
            chamfer.Edges = [(obj, f'Edge{idx}') for idx in edges]
            chamfer.Size = size

            doc.recompute()
            log_message(f"Created chamfer on edges {edge_indices} with size {size}")
            return {"result": "success", "chamfer_name": chamfer.Name, "message": f"Chamfer '{chamfer.Name}' created"}
        except Exception as e:
            log_error(f"Error creating chamfer: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_create_pattern_linear(self, feature_name, direction, length, occurrences, document_name=None):
        """Create a linear pattern of a feature"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            feature = doc.getObject(feature_name)
            if not feature:
                return {"result": "error", "message": f"Feature '{feature_name}' not found"}

            pattern = doc.addObject('PartDesign::LinearPattern', 'LinearPattern')
            pattern.Originals = [feature]
            pattern.Length = length
            pattern.Occurrences = occurrences

            # Parse direction vector
            dir_parts = [float(x.strip()) for x in direction.split(',')]
            if len(dir_parts) == 3:
                pattern.Direction = (App.Vector(*dir_parts), 0.0)

            doc.recompute()
            log_message(f"Created linear pattern of '{feature_name}' with {occurrences} occurrences")
            return {"result": "success", "pattern_name": pattern.Name, "message": f"Linear pattern '{pattern.Name}' created"}
        except Exception as e:
            log_error(f"Error creating linear pattern: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_create_pattern_polar(self, feature_name, axis, angle, occurrences, document_name=None):
        """Create a polar pattern of a feature"""
        try:
            doc = self._get_document(document_name)
            if not doc:
                return {"result": "error", "message": "No active document"}

            feature = doc.getObject(feature_name)
            if not feature:
                return {"result": "error", "message": f"Feature '{feature_name}' not found"}

            pattern = doc.addObject('PartDesign::PolarPattern', 'PolarPattern')
            pattern.Originals = [feature]
            pattern.Angle = angle
            pattern.Occurrences = occurrences

            # Set axis
            axis_map = {
                'X': App.Vector(1, 0, 0),
                'Y': App.Vector(0, 1, 0),
                'Z': App.Vector(0, 0, 1)
            }
            if axis in axis_map:
                pattern.Axis = (doc.getObject('Origin'), [f'{axis}_Axis'])

            doc.recompute()
            log_message(f"Created polar pattern of '{feature_name}' with {occurrences} occurrences")
            return {"result": "success", "pattern_name": pattern.Name, "message": f"Polar pattern '{pattern.Name}' created"}
        except Exception as e:
            log_error(f"Error creating polar pattern: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    # ============================================================================
    # Phase 1: Visual Feedback Handlers
    # ============================================================================

    def handle_get_view(self, params):
        """Get screenshot from specific view"""
        try:
            view_name = params.get("view_name", "Isometric")
            width = params.get("width")
            height = params.get("height")
            focus_object = params.get("focus_object")

            screenshot = capture_screenshot_base64(view_name, width, height, focus_object)

            if screenshot:
                log_message(f"Captured screenshot from {view_name} view")
                return {
                    "result": "success",
                    "view_name": view_name,
                    "screenshot": screenshot,
                    "message": f"Screenshot captured from {view_name} view"
                }
            else:
                return {
                    "result": "error",
                    "message": "Cannot capture screenshot in current view (e.g., TechDraw, Spreadsheet)"
                }
        except Exception as e:
            log_error(f"Error getting view: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_get_screenshot(self, params):
        """Alias for handle_get_view"""
        return self.handle_get_view(params)

    # ============================================================================
    # Phase 2: Parts Library Handlers
    # ============================================================================

    def handle_get_parts_list(self):
        """Get list of parts in FreeCAD parts library"""
        try:
            parts = self._scan_parts_library()
            log_message(f"Found {len(parts)} parts in library")
            return {
                "result": "success",
                "parts": parts,
                "count": len(parts),
                "message": f"Found {len(parts)} parts in library"
            }
        except Exception as e:
            log_error(f"Error getting parts list: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def handle_insert_part_from_library(self, relative_path):
        """Insert part from library into active document"""
        try:
            if not relative_path:
                return {"result": "error", "message": "relative_path parameter required"}

            lib_path = self._get_parts_library_path()
            if not lib_path:
                return {
                    "result": "error",
                    "message": "Parts library not found. Please install the FreeCAD parts_library addon."
                }

            full_path = os.path.join(lib_path, relative_path)
            if not os.path.exists(full_path):
                return {"result": "error", "message": f"Part not found: {relative_path}"}

            doc = App.ActiveDocument
            if not doc:
                return {"result": "error", "message": "No active document"}

            # Import the part
            import Import
            Import.insert(full_path, doc.Name)
            doc.recompute()

            # Capture screenshot
            screenshot = capture_screenshot_base64()

            log_message(f"Inserted part from library: {relative_path}")
            return {
                "result": "success",
                "part_path": relative_path,
                "screenshot": screenshot,
                "message": f"Inserted part: {relative_path}"
            }
        except Exception as e:
            log_error(f"Error inserting part from library: {str(e)}")
            return {"result": "error", "message": str(e), "traceback": traceback.format_exc()}

    def _get_parts_library_path(self):
        """Find FreeCAD parts library addon path"""
        # Common mod paths
        mod_paths = [
            os.path.join(App.getUserAppDataDir(), "Mod"),
            "/Applications/FreeCAD.app/Contents/Resources/Mod",  # macOS
            "C:\\Program Files\\FreeCAD\\Mod",  # Windows
            "/usr/share/freecad/Mod",  # Linux
        ]

        for mod_path in mod_paths:
            lib_path = os.path.join(mod_path, "parts_library")
            if os.path.exists(lib_path):
                return lib_path

        return None

    def _scan_parts_library(self):
        """Recursively scan parts library for .FCStd files"""
        lib_path = self._get_parts_library_path()
        if not lib_path:
            return []

        parts = []
        for root, dirs, files in os.walk(lib_path):
            for file in files:
                if file.endswith(".FCStd"):
                    rel_path = os.path.relpath(os.path.join(root, file), lib_path)
                    parts.append(rel_path)

        return sorted(parts)

    # ============================================================================
    # Phase 3: Flexible Code Execution Handler
    # ============================================================================

    def handle_execute_code(self, code, validate=True):
        """Execute arbitrary Python code with validation"""
        import io
        import contextlib

        try:
            if not code:
                return {"result": "error", "message": "code parameter required"}

            # Validate code safety
            if validate:
                is_safe, error_msg = validate_code_safety(code)
                if not is_safe:
                    log_error(f"Code validation failed: {error_msg}")
                    return {
                        "result": "error",
                        "message": f"Security validation failed: {error_msg}",
                        "help": (
                            "For safety, code must:\n"
                            "- Only use allowed modules (FreeCAD, Part, Draft, Sketcher, etc.)\n"
                            "- Not use dangerous builtins (eval, exec, open, etc.)\n"
                            "- Not access file system outside FreeCAD API"
                        )
                    }

            # Execute in safe environment
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
                "math": math,
                "FreeCAD": App,
                "FreeCADGui": Gui
            })

            # Execute code with output capture
            with contextlib.redirect_stdout(output_buffer):
                exec(code, safe_globals)

            output = output_buffer.getvalue()

            # Recompute and capture screenshot
            if App.ActiveDocument:
                App.ActiveDocument.recompute()

            screenshot = capture_screenshot_base64()

            log_message("Python code executed successfully")
            return {
                "result": "success",
                "output": output,
                "screenshot": screenshot,
                "message": "Code executed successfully"
            }

        except Exception as e:
            log_error(f"Error executing code: {str(e)}")
            return {
                "result": "error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }

class FreeCADMCPPanel:
    def __init__(self):
        from PySide2.QtWidgets import QWidget
        self.form = QWidget()
        self.form.setWindowTitle("FreeCAD MCP Control Panel")
        layout = QVBoxLayout(self.form)
        self.status_label = QLabel("Server Status: Stopped")
        layout.addWidget(self.status_label)
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Server")
        self.stop_button = QPushButton("Stop Server")
        self.clear_button = QPushButton("Clear Logs")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_server)
        self.stop_button.clicked.connect(self.stop_server)
        self.clear_button.clicked.connect(self.clear_logs)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_button)
        layout.addLayout(button_layout)
        self.report_browser = QTextEdit()
        self.report_browser.setReadOnly(True)
        self.report_browser.setPlaceholderText("Code execution and validation results will be displayed here")
        layout.addWidget(QLabel("Report Browser:"))
        layout.addWidget(self.report_browser)
        view_layout = QHBoxLayout()
        view_buttons = [
            ("Front View (1)", lambda: self.set_view("1")),
            ("Top View (2)", lambda: self.set_view("2")),
            ("Right View (3)", lambda: self.set_view("3")),
            ("Axonometric View (7)", lambda: self.set_view("7"))
        ]
        for label, callback in view_buttons:
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            view_layout.addWidget(btn)
        layout.addLayout(view_layout)
        self.server = None

    def start_server(self):
        if not self.server:
            self.server = FreeCADMCPServer()
            self.server.start()
            if self.server.running:
                self.status_label.setText("Server Status: Running")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.report_browser.append("Server started")

    def stop_server(self):
        if self.server:
            self.server.stop()
            self.server = None
            self.status_label.setText("Server Status: Stopped")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.report_browser.append("Server stopped")

    def set_view(self, view_type):
        if self.server:
            result = self.server.handle_set_view(view_type)
            if result["result"] == "success":
                self.report_browser.append(f"Adjusted to {result['view_name']} view")
            else:
                self.report_browser.append(f"Error adjusting view: {result['message']}")

    def clear_logs(self):
        self.report_browser.clear()
        log_message("Logs cleared")

panel_instance = None

def show_panel():
    global panel_instance
    try:
        panel_instance = FreeCADMCPPanel()
        Gui.Control.showDialog(panel_instance)
        App.Console.PrintMessage("MCP panel displayed\n")
    except Exception as e:
        App.Console.PrintError(f"Error displaying panel: {str(e)}\n")