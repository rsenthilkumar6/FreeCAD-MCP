import FreeCAD as App
import FreeCADGui as Gui
import os
import sys
from PySide2 import QtWidgets

# Command to show MCP panel
class FreeCADMCPShowCommand:
    def GetResources(self):
        """Define command icon, menu text and tooltip"""
        # Compute icon path inline to avoid scoping issues
        try:
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            plugin_dir = os.path.join(App.getUserAppDataDir(), "Mod", "FreeCAD-MCP")
        icon_path = os.path.join(plugin_dir, "assets", "icon.svg")
        if not os.path.exists(icon_path):
            icon_path = ""

        return {
            'Pixmap': icon_path,
            'MenuText': 'Show FreeCAD MCP Panel',
            'ToolTip': 'Show FreeCAD Model Control Protocol Panel'
        }

    def IsActive(self):
        """Command is always active"""
        return True

    def Activated(self):
        """Show MCP panel when command is triggered"""
        import freecad_mcp_server
        freecad_mcp_server.show_panel()

# Command to start MCP server
class FreeCADMCPStartServerCommand:
    def GetResources(self):
        """Define command icon, menu text and tooltip"""
        # Compute icon path inline to avoid scoping issues
        try:
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            plugin_dir = os.path.join(App.getUserAppDataDir(), "Mod", "FreeCAD-MCP")
        icon_path = os.path.join(plugin_dir, "assets", "icon.svg")
        if not os.path.exists(icon_path):
            icon_path = ""

        return {
            'Pixmap': icon_path,
            'MenuText': 'Start MCP Server',
            'ToolTip': 'Start FreeCAD MCP server to accept external connections'
        }

    def IsActive(self):
        """Command is always active"""
        return True

    def Activated(self):
        """Start MCP server when command is triggered"""
        import freecad_mcp_server
        # Create server instance and start
        server = freecad_mcp_server.FreeCADMCPServer()
        server.start()
        if server.running:
            freecad_mcp_server.log_message("MCP server started")
        else:
            freecad_mcp_server.log_error("MCP server failed to start")

# Register commands
try:
    if not hasattr(Gui, "freecad_mcp_command"):
        Gui.addCommand('FreeCAD_MCP_Show', FreeCADMCPShowCommand())
    if not hasattr(Gui, "freecad_mcp_server_command"):
        Gui.addCommand('FreeCAD_MCP_StartServer', FreeCADMCPStartServerCommand())
except Exception as e:
    App.Console.PrintError(f"Error registering commands: {str(e)}\n")

# Define FreeCAD MCP workbench
class FreeCADMCPWorkbench(Gui.Workbench):
    MenuText = "FreeCAD MCP"
    ToolTip = "FreeCAD Model Control Protocol"

    def GetIcon(self):
        """Return workbench icon"""
        # Compute icon path inline to avoid scoping issues
        try:
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            plugin_dir = os.path.join(App.getUserAppDataDir(), "Mod", "FreeCAD-MCP")
        icon_path = os.path.join(plugin_dir, "assets", "icon.svg")
        if not os.path.exists(icon_path):
            icon_path = ""
        return icon_path

    def Initialize(self):
        """Initialize workbench, add commands to toolbar and menu"""
        # Compute plugin dir inline
        try:
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            plugin_dir = os.path.join(App.getUserAppDataDir(), "Mod", "FreeCAD-MCP")

        if plugin_dir not in sys.path:
            sys.path.append(plugin_dir)
        self.command_list = ["FreeCAD_MCP_Show", "FreeCAD_MCP_StartServer"]
        self.appendToolbar("FreeCAD MCP Tools", self.command_list)
        self.appendMenu("&FreeCAD MCP", self.command_list)
        App.Console.PrintMessage("FreeCAD MCP workbench initialized\n")

    def Activated(self):
        """Called when workbench is activated"""
        pass

    def Deactivated(self):
        """Called when workbench is deactivated"""
        pass

    def GetClassName(self):
        """Return C++ class name"""
        return "Gui::PythonWorkbench"

# Add workbench
try:
    if not hasattr(Gui, "freecad_mcp_workbench"):
        Gui.addWorkbench(FreeCADMCPWorkbench())
        App.Console.PrintMessage("FreeCAD MCP workbench registered\n")
except Exception as e:
    App.Console.PrintError(f"Error registering workbench: {str(e)}\n")