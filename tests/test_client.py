"""Unit tests for FreeCAD MCP client."""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from freecad_mcp_client import normalize_macro_code, get_absolute_macro_path


class TestNormalizeMacroCode:
    """Test macro code normalization."""

    def test_adds_missing_imports(self):
        """Test that missing imports are added."""
        code = "box = Part.makeBox(10, 10, 10)"
        normalized = normalize_macro_code(code)

        assert "import FreeCAD as App" in normalized
        assert "import FreeCADGui as Gui" in normalized
        assert "import Part" in normalized
        assert "import math" in normalized
        assert "box = Part.makeBox(10, 10, 10)" in normalized

    def test_preserves_existing_imports(self):
        """Test that existing imports are not duplicated."""
        code = """import FreeCAD as App
import Part

box = Part.makeBox(10, 10, 10)
"""
        normalized = normalize_macro_code(code)

        # Should not duplicate imports
        assert normalized.count("import FreeCAD as App") == 1
        assert normalized.count("import Part") == 1
        # But should add missing ones
        assert "import FreeCADGui as Gui" in normalized
        assert "import math" in normalized

    def test_handles_empty_code(self):
        """Test handling of empty code."""
        code = ""
        normalized = normalize_macro_code(code)

        assert normalized == "# FreeCAD Macro\n"

    def test_handles_whitespace_only(self):
        """Test handling of whitespace-only code."""
        code = "   \n\n   "
        normalized = normalize_macro_code(code)

        assert normalized == "# FreeCAD Macro\n"

    def test_strips_leading_trailing_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        code = "\n\n  box = Part.makeBox(10, 10, 10)  \n\n"
        normalized = normalize_macro_code(code)

        lines = normalized.splitlines()
        assert lines[-1].strip() == "box = Part.makeBox(10, 10, 10)"


class TestGetAbsoluteMacroPath:
    """Test macro path resolution."""

    def test_adds_extension(self):
        """Test that .FCMacro extension is added if missing."""
        path = get_absolute_macro_path("test_macro")

        assert path.endswith(".FCMacro")
        assert "test_macro.FCMacro" in path

    def test_preserves_extension(self):
        """Test that existing .FCMacro extension is preserved."""
        path = get_absolute_macro_path("test_macro.FCMacro")

        assert path.endswith(".FCMacro")
        assert path.count(".FCMacro") == 1  # Not duplicated

    def test_creates_platform_specific_path(self):
        """Test that path is platform-specific."""
        path = get_absolute_macro_path("test")

        # Should contain platform-specific directory
        import platform
        system = platform.system()

        if system == "Darwin":
            assert "Library/Application Support/FreeCAD/Macro" in path
        elif system == "Windows":
            assert "AppData\\Roaming\\FreeCAD\\Macro" in path
        else:  # Linux
            assert ".local/share/FreeCAD/Macro" in path

    def test_returns_absolute_path(self):
        """Test that returned path is absolute."""
        path = get_absolute_macro_path("test")

        assert os.path.isabs(path)


class TestParameterInjection:
    """Test parameter injection in macros (integration test concept)."""

    def test_params_dict_format(self):
        """Test that params are properly formatted for injection."""
        params = {"radius": 10, "height": 20, "name": "TestObject"}

        # Simulate what the server does
        param_code = "\n".join([
            f"{key} = {repr(value)}" for key, value in params.items()
        ])

        assert "radius = 10" in param_code
        assert "height = 20" in param_code
        assert "name = 'TestObject'" in param_code

    def test_string_values_quoted(self):
        """Test that string values are properly quoted."""
        params = {"name": "My Object"}

        param_code = "\n".join([
            f"{key} = {repr(value)}" for key, value in params.items()
        ])

        assert "name = 'My Object'" in param_code

    def test_numeric_values_unquoted(self):
        """Test that numeric values are not quoted."""
        params = {"count": 5, "radius": 10.5}

        param_code = "\n".join([
            f"{key} = {repr(value)}" for key, value in params.items()
        ])

        assert "count = 5" in param_code
        assert "radius = 10.5" in param_code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
