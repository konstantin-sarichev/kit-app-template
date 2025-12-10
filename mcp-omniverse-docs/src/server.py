"""Main MCP server implementation for Omniverse documentation."""

import json
from typing import Any, List, Optional

from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)
from pydantic import AnyUrl

from .config import DEBUG, EXTENSION_TOPICS
from .fetcher import DocFetcher


# Create MCP server
app = Server("omniverse-docs")

# Global fetcher instance
_fetcher: Optional[DocFetcher] = None


def get_fetcher() -> DocFetcher:
    """Get or create fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = DocFetcher()
    return _fetcher


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_omniverse_docs",
            description=(
                "Search across Omniverse documentation including Kit SDK, USD API, and "
                "extension development guides. Returns relevant documentation excerpts "
                "with links to full documentation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query - can be a concept, API name, or question. "
                            "Examples: 'stage events', 'USD prim creation', 'extension lifecycle'"
                        ),
                    },
                    "doc_type": {
                        "type": "string",
                        "enum": ["kit", "usd", "extension", "all"],
                        "description": "Type of documentation to search (default: 'all')",
                        "default": "all",
                    },
                    "include_code": {
                        "type": "boolean",
                        "description": "Include code examples in results (default: true)",
                        "default": True,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_api_reference",
            description=(
                "Get detailed API documentation for a specific Omniverse Kit or USD API. "
                "Returns comprehensive information including parameters, return types, "
                "and usage examples."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "api_path": {
                        "type": "string",
                        "description": (
                            "Full API path. Examples: 'omni.usd.get_context', "
                            "'pxr.Usd.Stage', 'omni.kit.commands.execute'"
                        ),
                    },
                    "api_type": {
                        "type": "string",
                        "enum": ["kit", "usd"],
                        "description": "'kit' for Omniverse Kit APIs, 'usd' for USD APIs",
                    },
                },
                "required": ["api_path", "api_type"],
            },
        ),
        Tool(
            name="get_extension_guide",
            description=(
                "Get extension development guides and best practices. Covers topics like "
                "extension lifecycle, UI development, stage manipulation, and event handling."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": list(EXTENSION_TOPICS.keys()),
                        "description": f"Extension development topic. Available: {', '.join(EXTENSION_TOPICS.keys())}",
                    }
                },
                "required": ["topic"],
            },
        ),
        Tool(
            name="search_code_examples",
            description=(
                "Find code examples from Omniverse documentation. Searches for practical "
                "implementation examples related to your query."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "What you want to accomplish. Examples: 'create USD prim', "
                            "'subscribe to stage events', 'create UI window'"
                        ),
                    },
                    "language": {
                        "type": "string",
                        "enum": ["python", "cpp"],
                        "description": "Programming language (default: 'python')",
                        "default": "python",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_omniverse_best_practices",
            description=(
                "Search for Omniverse best practices and common patterns. Covers topics "
                "like unit handling, transform normalization, metadata management, and "
                "physical accuracy."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "Best practice topic. Examples: 'unit conversion', 'metadata', "
                            "'transforms', 'stage organization'"
                        ),
                    }
                },
                "required": ["topic"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls."""
    fetcher = get_fetcher()

    try:
        if name == "search_omniverse_docs":
            return await handle_search_docs(fetcher, arguments)
        elif name == "get_api_reference":
            return await handle_api_reference(fetcher, arguments)
        elif name == "get_extension_guide":
            return await handle_extension_guide(fetcher, arguments)
        elif name == "search_code_examples":
            return await handle_code_examples(fetcher, arguments)
        elif name == "search_omniverse_best_practices":
            return await handle_best_practices(fetcher, arguments)
        else:
            return [
                TextContent(
                    type="text",
                    text=f"Unknown tool: {name}",
                )
            ]
    except Exception as e:
        if DEBUG:
            import traceback

            traceback.print_exc()
        return [
            TextContent(
                type="text",
                text=f"Error executing tool {name}: {str(e)}",
            )
        ]


async def handle_search_docs(fetcher: DocFetcher, args: dict) -> List[TextContent]:
    """Handle search_omniverse_docs tool."""
    query = args["query"]
    doc_type = args.get("doc_type", "all")
    include_code = args.get("include_code", True)

    results = []

    # Search based on doc_type
    if doc_type in ["kit", "all"]:
        kit_results = await fetcher.search_kit_docs(query)
        results.extend(kit_results)

    if doc_type in ["usd", "all"]:
        usd_results = await fetcher.search_usd_docs(query)
        results.extend(usd_results)

    if not results:
        return [
            TextContent(
                type="text",
                text=f"No results found for query: {query}\n\n"
                f"Try:\n"
                f"- Using more specific terms\n"
                f"- Searching for API names (e.g., 'Usd.Stage', 'omni.usd')\n"
                f"- Using common concepts (e.g., 'stage events', 'extension lifecycle')",
            )
        ]

    # Format results
    output = f"# Search Results for: {query}\n\n"
    output += f"Found {len(results)} result(s)\n\n"

    for i, result in enumerate(results[:5], 1):  # Limit to top 5
        output += f"## Result {i}: {result.get('title', 'Documentation')}\n\n"
        output += f"**Source:** {result['source']}\n"
        output += f"**URL:** {result['url']}\n\n"
        output += f"### Excerpt:\n{result['excerpt']}\n\n"

        if include_code and "code_examples" in result and result["code_examples"]:
            output += "### Code Examples:\n\n"
            for j, example in enumerate(result["code_examples"][:2], 1):
                output += f"**Example {j}** ({example.get('language', 'python')}):\n"
                output += f"```{example.get('language', 'python')}\n"
                output += f"{example['code']}\n"
                output += "```\n\n"

        output += "---\n\n"

    return [TextContent(type="text", text=output)]


async def handle_api_reference(fetcher: DocFetcher, args: dict) -> List[TextContent]:
    """Handle get_api_reference tool."""
    api_path = args["api_path"]
    api_type = args["api_type"]

    result = await fetcher.get_api_docs(api_path, api_type)

    if not result:
        return [
            TextContent(
                type="text",
                text=f"Could not find API documentation for: {api_path}\n\n"
                f"Make sure the API path is correct. Examples:\n"
                f"- Kit: 'omni.usd.get_context', 'omni.kit.commands.execute'\n"
                f"- USD: 'pxr.Usd.Stage', 'pxr.UsdGeom.Xformable'",
            )
        ]

    output = f"# API Reference: {api_path}\n\n"
    output += f"**Type:** {api_type.upper()}\n"
    output += f"**Source:** {result['url']}\n\n"

    if result.get("headings"):
        output += "## Sections:\n"
        for heading in result["headings"][:10]:
            indent = "  " * (heading["level"] - 1)
            output += f"{indent}- {heading['text']}\n"
        output += "\n"

    output += "## Documentation:\n\n"
    output += result["content"][:2000]  # Limit content length
    if len(result["content"]) > 2000:
        output += "\n\n... (truncated, see full documentation at URL above)\n"

    if result.get("code_examples"):
        output += "\n\n## Code Examples:\n\n"
        for i, example in enumerate(result["code_examples"][:3], 1):
            output += f"### Example {i}:\n"
            output += f"```{example.get('language', 'python')}\n"
            output += f"{example['code']}\n"
            output += "```\n\n"

    return [TextContent(type="text", text=output)]


async def handle_extension_guide(fetcher: DocFetcher, args: dict) -> List[TextContent]:
    """Handle get_extension_guide tool."""
    topic = args["topic"]

    # Provide built-in guide information
    guides = {
        "lifecycle": """# Extension Lifecycle

## Basic Extension Structure

```python
import omni.ext

class MyExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        '''Called when extension starts.'''
        print(f"[{ext_id}] MyExtension startup")
        
        # Initialize your extension here
        # Subscribe to events
        # Create UI
        # Register commands
        
    def on_shutdown(self):
        '''Called when extension shuts down.'''
        print("MyExtension shutdown")
        
        # Clean up resources
        # Unsubscribe from events
        # Destroy UI
```

## Key Points

1. **Startup Order**: Extensions load based on dependencies
2. **Shutdown**: Always clean up resources in on_shutdown
3. **Extension ID**: Unique identifier passed to on_startup
4. **Dependencies**: Declare in extension.toml

## Best Practices

- Keep startup fast (< 100ms if possible)
- Defer heavy initialization to first use
- Always pair subscriptions with unsubscriptions
- Use weak references for event handlers when possible
""",
        "ui": """# UI Development with omni.ui

## Basic Window Creation

```python
import omni.ui as ui

class MyWindow:
    def __init__(self):
        self._window = ui.Window("My Window", width=400, height=300)
        with self._window.frame:
            with ui.VStack():
                ui.Label("Hello Omniverse!")
                ui.Button("Click Me", clicked_fn=self._on_click)
    
    def _on_click(self):
        print("Button clicked!")
    
    def destroy(self):
        if self._window:
            self._window.destroy()
            self._window = None
```

## Common Patterns

- Use VStack/HStack for layout
- Store window reference to prevent garbage collection
- Always destroy windows in extension shutdown
- Use clicked_fn for button callbacks
""",
        "stage": """# Stage Manipulation

## Getting the Stage

```python
import omni.usd

# Get the current USD stage
context = omni.usd.get_context()
stage = context.get_stage()
```

## Creating Prims

```python
from pxr import UsdGeom, Sdf

# Create a cube
cube_path = Sdf.Path("/World/Cube")
cube_prim = UsdGeom.Cube.Define(stage, cube_path)

# Set transform
cube_prim.AddTranslateOp().Set((100, 0, 0))
```

## Stage Events

```python
def on_stage_event(event):
    if event.type == int(omni.usd.StageEventType.OPENED):
        print("Stage opened")

# Subscribe
events = context.get_stage_event_stream()
subscription = events.create_subscription_to_pop(
    on_stage_event,
    name="my_stage_event"
)

# Unsubscribe in shutdown
subscription = None
```
""",
        "events": """# Event System

## Stage Events

```python
import omni.usd

context = omni.usd.get_context()
events = context.get_stage_event_stream()

def on_event(event):
    event_type = event.type
    if event_type == int(omni.usd.StageEventType.OPENED):
        print("Stage opened")
    elif event_type == int(omni.usd.StageEventType.CLOSED):
        print("Stage closed")

subscription = events.create_subscription_to_pop(on_event)
```

## Selection Events

```python
import omni.usd

def on_selection_changed(event):
    context = omni.usd.get_context()
    selection = context.get_selection()
    paths = selection.get_selected_prim_paths()
    print(f"Selected: {paths}")

selection_events = context.get_stage_event_stream()
sub = selection_events.create_subscription_to_pop(on_selection_changed)
```

## Cleanup

Always unsubscribe in on_shutdown:
```python
def on_shutdown(self):
    self._subscription = None  # Clears subscription
```
""",
        "settings": """# Settings and Configuration

## Reading Settings

```python
import carb.settings

settings = carb.settings.get_settings()
value = settings.get("/app/window/title")
```

## Writing Settings

```python
settings.set("/my_extension/my_setting", "value")
```

## Persistent Settings

Define in extension.toml:

```toml
[[python.module]]
name = "my_company.my_extension"

[settings]
my_setting = "default_value"
```

## Best Practices

- Use namespaced settings: /my_extension/setting_name
- Define defaults in extension.toml
- Use typed getters: get_as_int, get_as_bool
""",
        "tests": """# Testing Extensions

## Basic Test Structure

```python
import omni.kit.test

class TestMyExtension(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        '''Runs before each test.'''
        pass
    
    async def tearDown(self):
        '''Runs after each test.'''
        pass
    
    async def test_basic(self):
        '''Test basic functionality.'''
        self.assertTrue(True)
```

## Running Tests

```bash
# Run all tests
./repo.sh test

# Run specific test
./repo.sh test -s my_extension.tests.test_basic
```

## Best Practices

- Use AsyncTestCase for async tests
- Test with real USD stages when possible
- Clean up in tearDown
- Use meaningful test names
""",
    }

    if topic not in guides:
        return [
            TextContent(
                type="text",
                text=f"Unknown extension topic: {topic}\n\n"
                f"Available topics: {', '.join(EXTENSION_TOPICS.keys())}",
            )
        ]

    return [TextContent(type="text", text=guides[topic])]


async def handle_code_examples(fetcher: DocFetcher, args: dict) -> List[TextContent]:
    """Handle search_code_examples tool."""
    query = args["query"]
    language = args.get("language", "python")

    # Search for code examples
    results = await fetcher.search_kit_docs(query)
    results.extend(await fetcher.search_usd_docs(query))

    # Filter for code examples
    examples = []
    for result in results:
        if "code_examples" in result:
            for example in result["code_examples"]:
                if example.get("language") == language:
                    examples.append(
                        {
                            "code": example["code"],
                            "source": result.get("title", "Documentation"),
                            "url": result.get("url", ""),
                        }
                    )

    if not examples:
        return [
            TextContent(
                type="text",
                text=f"No {language} code examples found for: {query}\n\n"
                f"Try searching in documentation or being more specific.",
            )
        ]

    output = f"# Code Examples: {query}\n\n"
    output += f"Language: {language}\n\n"

    for i, example in enumerate(examples[:5], 1):
        output += f"## Example {i} - {example['source']}\n\n"
        output += f"```{language}\n"
        output += f"{example['code']}\n"
        output += "```\n\n"
        if example["url"]:
            output += f"Source: {example['url']}\n\n"
        output += "---\n\n"

    return [TextContent(type="text", text=output)]


async def handle_best_practices(fetcher: DocFetcher, args: dict) -> List[TextContent]:
    """Handle search_omniverse_best_practices tool."""
    topic = args["topic"]

    # Built-in best practices relevant to Vision Digital Twin
    practices = {
        "units": """# Unit Handling Best Practices

## Setting Stage Units to Millimeters

```python
from pxr import Usd, UsdGeom

stage = omni.usd.get_context().get_stage()

# Set meters per unit to 0.001 (millimeters)
UsdGeom.SetStageMetersPerUnit(stage, 0.001)

# Verify
meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
print(f"Meters per unit: {meters_per_unit}")  # Should be 0.001
```

## Working with Millimeter Units

- All translation values are in mm when metersPerUnit = 0.001
- Camera sensor sizes should be in mm
- Working distances should be in mm
- Keep consistent across entire stage

## Checking Existing Units

```python
def check_stage_units(stage):
    meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
    if meters_per_unit != 0.001:
        print(f"Warning: Stage units are {meters_per_unit}, expected 0.001 (mm)")
        return False
    return True
```
""",
        "transforms": """# Transform Best Practices

## No Scaling - Use Actual Dimensions

```python
from pxr import UsdGeom, Gf

# GOOD: Set actual size in geometry
cube = UsdGeom.Cube.Define(stage, "/World/Cube")
cube.GetSizeAttr().Set(100.0)  # 100mm cube

# BAD: Don't use scale transforms
# cube.AddScaleOp().Set((100, 100, 100))
```

## Normalize Transforms

```python
def normalize_prim_transforms(prim):
    '''Remove scale from transform stack.'''
    xformable = UsdGeom.Xformable(prim)
    
    # Reset transform ops
    xformable.ClearXformOpOrder()
    
    # Add only translate and rotate (no scale)
    xformable.AddTranslateOp()
    xformable.AddRotateXYZOp()
```

## Physical Accuracy

- Use real-world measurements
- No arbitrary scaling
- Match hardware specifications exactly
""",
        "metadata": """# Metadata Management

## Custom Metadata for Assets

```python
from pxr import Sdf

prim = stage.GetPrimAtPath("/World/Camera")

# Set custom data
prim.SetCustomDataByKey("id:model", "Basler_acA1920")
prim.SetCustomDataByKey("id:type", "camera")
prim.SetCustomDataByKey("id:version", "1.0.0")
prim.SetCustomDataByKey("id:author", "Industrial Dynamics")

# Read custom data
model = prim.GetCustomDataByKey("id:model")
print(f"Camera model: {model}")
```

## Metadata for Physical Parameters

```python
# Store optical parameters
prim.SetCustomDataByKey("sensor_width_mm", 11.264)
prim.SetCustomDataByKey("sensor_height_mm", 7.104)
prim.SetCustomDataByKey("pixel_size_um", 5.86)
prim.SetCustomDataByKey("focal_length_mm", 16.0)
```

## Validation

```python
def validate_asset_metadata(prim):
    '''Check required metadata exists.'''
    required = ["id:model", "id:type", "id:version"]
    
    for key in required:
        if not prim.HasCustomDataKey(key):
            print(f"Missing metadata: {key}")
            return False
    return True
```
""",
        "stage": """# Stage Organization Best Practices

## Hierarchical Structure

```
/World
├── /Cameras
│   ├── /Camera_Main
│   └── /Camera_Inspection
├── /Lights
│   ├── /Light_Ring
│   └── /Light_Back
├── /Parts
│   └── /Part_001
└── /Fixtures
    └── /Bracket_001
```

## Create Organized Hierarchy

```python
from pxr import Usd, UsdGeom

def create_project_hierarchy(stage):
    '''Create standard hierarchy.'''
    root = stage.GetPrimAtPath("/World")
    if not root:
        root = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    
    # Create organizational prims
    for name in ["Cameras", "Lights", "Parts", "Fixtures"]:
        path = f"/World/{name}"
        if not stage.GetPrimAtPath(path):
            UsdGeom.Scope.Define(stage, path)
```

## Reference Assets

```python
# Reference instead of copying
asset_path = "assets/Cameras/Camera_Basler_1x.usd"
prim = stage.DefinePrim("/World/Cameras/Camera_Main")
prim.GetReferences().AddReference(asset_path)
```
""",
    }

    # Try to match topic to practices
    matched_key = None
    topic_lower = topic.lower()

    for key in practices.keys():
        if key in topic_lower or topic_lower in key:
            matched_key = key
            break

    if not matched_key:
        # Provide general guidance
        return [
            TextContent(
                type="text",
                text=f"# Best Practices for: {topic}\n\n"
                f"No specific best practices found for this topic.\n\n"
                f"Available topics:\n"
                + "\n".join(f"- {k}: {v.split('##')[0].strip()}" for k, v in practices.items())
                + "\n\nTry searching documentation for more specific information.",
            )
        ]

    return [TextContent(type="text", text=practices[matched_key])]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

