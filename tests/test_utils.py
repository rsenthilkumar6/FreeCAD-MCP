"""Unit tests for InitGui module."""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import InitGui


class TestInitGuiModule:
    """Test InitGui module functionality."""

    def test_module_imports_successfully(self):
        """Test that InitGui module can be imported."""
        assert InitGui is not None

    def test_show_command_class_exists(self):
        """Test that FreeCADMCPShowCommand class exists."""
        assert hasattr(InitGui, 'FreeCADMCPShowCommand')

    def test_start_server_command_class_exists(self):
        """Test that FreeCADMCPStartServerCommand class exists."""
        assert hasattr(InitGui, 'FreeCADMCPStartServerCommand')

    def test_workbench_class_exists(self):
        """Test that FreeCADMCPWorkbench class exists."""
        assert hasattr(InitGui, 'FreeCADMCPWorkbench')

    def test_show_command_has_get_resources(self):
        """Test that show command has GetResources method."""
        cmd = InitGui.FreeCADMCPShowCommand()
        assert hasattr(cmd, 'GetResources')
        assert callable(cmd.GetResources)

    def test_get_resources_returns_dict(self):
        """Test that GetResources returns a dict with required keys."""
        cmd = InitGui.FreeCADMCPShowCommand()
        resources = cmd.GetResources()

        assert isinstance(resources, dict)
        assert 'MenuText' in resources
        assert 'ToolTip' in resources
        assert 'Pixmap' in resources

    def test_pixmap_is_string(self):
        """Test that Pixmap value is a string."""
        cmd = InitGui.FreeCADMCPShowCommand()
        resources = cmd.GetResources()

        assert isinstance(resources['Pixmap'], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
