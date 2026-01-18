# FreeCAD MCP Development Guide

## Setup Development Environment

### Prerequisites
- Python 3.10 or higher
- FreeCAD 0.21 or higher
- uv (recommended) or pip

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ATOI-Ming/FreeCAD-MCP.git
   cd FreeCAD-MCP
   ```

2. **Create virtual environment**:
   ```bash
   # Using uv (recommended)
   uv venv .venv --python 3.12

   # Or using standard venv
   python -m venv .venv
   ```

3. **Activate virtual environment**:
   ```bash
   # macOS/Linux
   source .venv/bin/activate

   # Windows
   .venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   # Production dependencies
   uv pip install mcp-server httpx

   # Development dependencies
   uv pip install pytest pytest-asyncio pytest-cov black isort mypy
   ```

## Project Structure

```
FreeCAD-MCP/
├── InitGui.py              # FreeCAD workbench integration
├── freecad_mcp_server.py   # MCP server implementation
├── src/
│   └── freecad_mcp_client.py   # MCP client tools
├── templates.py            # Macro templates library
├── config.py               # Configuration loader
├── config.json             # Configuration file
├── tests/                  # Unit tests
│   ├── test_client.py
│   └── test_utils.py
├── docs/                   # Documentation
│   ├── API.md
│   └── DEVELOPMENT.md
├── assets/                 # Icons and images
├── pyproject.toml          # Project metadata
├── pytest.ini              # Pytest configuration
└── README.md               # User documentation
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_client.py

# Run specific test
pytest tests/test_client.py::TestNormalizeMacroCode::test_adds_missing_imports

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s
```

## Code Style

We use Black for code formatting and isort for import sorting.

```bash
# Format code
black src/ tests/ *.py

# Sort imports
isort src/ tests/ *.py

# Check types
mypy src/
```

### Code Style Guidelines

- **Line length**: 100 characters
- **Docstrings**: Google style
- **Type hints**: Use for function signatures
- **Naming**:
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`

### Example Function

```python
def create_parametric_box(length: float, width: float, height: float) -> Dict[str, Any]:
    """Create a parametric box in FreeCAD.

    Args:
        length: Box length in mm
        width: Box width in mm
        height: Box height in mm

    Returns:
        Dict containing status and object name

    Raises:
        ValueError: If dimensions are invalid
    """
    if length <= 0 or width <= 0 or height <= 0:
        raise ValueError("All dimensions must be positive")

    # Implementation...
    return {"status": "success", "object": "Box"}
```

## Adding New MCP Tools

### 1. Add Tool to Client

In `src/freecad_mcp_client.py`:

```python
@mcp.tool()
async def my_new_tool(param1: str, param2: int = 10) -> Dict[str, Any]:
    """Description of what the tool does.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)

    Returns:
        Dict with result and status
    """
    return await send_command_to_freecad({
        "command": "my_new_command",
        "params": {
            "param1": param1,
            "param2": param2
        }
    })
```

### 2. Add Handler to Server

In `freecad_mcp_server.py`:

```python
# Add to dispatch_command method
elif command_type == "my_new_command":
    return self.handle_my_new_command(
        params.get("param1"),
        params.get("param2")
    )

# Add handler method
def handle_my_new_command(self, param1, param2=10):
    """Handle my_new_command."""
    try:
        # FreeCAD API calls
        doc = App.ActiveDocument
        # ... implementation ...

        log_message(f"Successfully executed my_new_command")
        return {
            "result": "success",
            "data": result_data
        }
    except Exception as e:
        log_error(f"Error in my_new_command: {str(e)}")
        return {
            "result": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }
```

### 3. Add Tests

In `tests/test_my_feature.py`:

```python
def test_my_new_tool():
    """Test my_new_tool functionality."""
    # Test implementation
    result = my_new_tool("test", 20)
    assert result["status"] == "success"
```

### 4. Update Documentation

Add to `docs/API.md`:

```markdown
### my_new_tool

Description of the tool.

**Parameters**:
- `param1` (str): Description
- `param2` (int, optional): Description (default: 10)

**Returns**: Dict with status and data

**Example**:
\```python
result = await my_new_tool("example", 15)
\```
```

## Debugging

### Server Debugging

1. **Enable debug logging**:
   Edit `config.json`:
   ```json
   {
     "logging": {
       "level": "DEBUG"
     }
   }
   ```

2. **Check logs**:
   ```bash
   # macOS/Linux
   tail -f /tmp/freecad_mcp_log.txt

   # Windows
   type %TEMP%\freecad_mcp_log.txt
   ```

3. **Use FreeCAD console**:
   ```python
   import FreeCAD as App
   App.Console.PrintMessage("Debug message\n")
   ```

### Client Debugging

1. **Run client directly**:
   ```bash
   python src/freecad_mcp_client.py --get-report
   ```

2. **Add print statements**:
   ```python
   print(f"Sending command: {command}")
   ```

3. **Use Python debugger**:
   ```python
   import pdb; pdb.set_trace()
   ```

## Contributing

### Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and test**:
   ```bash
   # Make changes
   # Run tests
   pytest
   # Format code
   black .
   isort .
   ```

3. **Commit changes**:
   ```bash
   git add .
   git commit -m "Add my feature"
   ```

4. **Push and create PR**:
   ```bash
   git push origin feature/my-feature
   ```

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

**Example**:
```
feat: Add parametric cylinder template

- Add cylinder template with radius and height params
- Update template library documentation
- Add tests for cylinder template

Closes #123
```

## Release Process

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md**
3. **Run all tests**: `pytest`
4. **Create git tag**: `git tag v0.2.0`
5. **Push tag**: `git push --tags`
6. **Create GitHub release**

## Common Issues

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'mcp'`

**Solution**:
```bash
uv pip install mcp-server httpx
```

### Path Issues

**Problem**: Icon not found

**Solution**: Ensure icon.svg exists in `assets/` directory

### FreeCAD GUI Not Available

**Problem**: `App.GuiUp` is False

**Solution**: Run FreeCAD with GUI, not in console mode

## Resources

- [FreeCAD Python API](https://freecad-python-api.readthedocs.io/)
- [FreeCAD Scripting Guide](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/FreeCAD_Scripting_Basics.md)
- [MCP Documentation](https://github.com/anthropics/mcp)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/ATOI-Ming/FreeCAD-MCP/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ATOI-Ming/FreeCAD-MCP/discussions)
- **Email**: 1757772673@qq.com
