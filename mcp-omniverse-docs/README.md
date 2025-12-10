# MCP Omniverse Documentation Server

A Model Context Protocol (MCP) server that provides real-time access to NVIDIA Omniverse documentation, including Kit SDK, USD API, and extension development references.

## Features

- 🔍 **Search Omniverse Documentation** - Query Kit SDK, USD, and extension APIs
- 📚 **API Reference Access** - Get detailed Python API documentation
- 🎯 **Context-Aware Retrieval** - Find relevant documentation based on your query
- ⚡ **Cached Results** - Fast responses with intelligent caching
- 🔄 **Real-Time Updates** - Access the latest documentation from Omniverse sources

## Installation

```bash
# Install dependencies
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## Usage with Cursor

Add to your Cursor MCP settings (`.cursor/mcp_config.json` or via Cursor settings):

```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "python",
      "args": [
        "-m",
        "mcp_omniverse_docs"
      ],
      "cwd": "G:/Vision_Example_1/kit-app-template/mcp-omniverse-docs"
    }
  }
}
```

## Available Tools

### 1. `search_omniverse_docs`
Search across all Omniverse documentation sources.

**Parameters:**
- `query` (string): Search query (e.g., "stage events", "USD prim", "extension lifecycle")
- `doc_type` (string, optional): Filter by type: "kit", "usd", "extension", "all" (default: "all")

**Example:**
```
Search for "how to subscribe to stage open events"
```

### 2. `get_api_reference`
Get detailed API documentation for a specific class or module.

**Parameters:**
- `api_path` (string): Full API path (e.g., "omni.usd.get_context", "pxr.Usd.Stage")
- `api_type` (string): "kit" or "usd"

**Example:**
```
Get API reference for omni.usd.get_context
```

### 3. `get_extension_guide`
Retrieve extension development guides and patterns.

**Parameters:**
- `topic` (string): Topic like "extension_lifecycle", "stage_events", "ui_development"

### 4. `search_code_examples`
Find code examples from Omniverse documentation.

**Parameters:**
- `query` (string): What you're trying to accomplish
- `language` (string, optional): "python" or "cpp" (default: "python")

## Documentation Sources

The MCP server accesses documentation from:

1. **Kit SDK Documentation**
   - https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/
   - Python API references
   - Extension development guides

2. **USD Documentation**
   - https://openusd.org/
   - USD Python API
   - USD concepts and best practices

3. **Omniverse Extensions**
   - Extension registry documentation
   - Common patterns and examples

4. **Replicator & Synthetic Data**
   - Replicator API documentation
   - Synthetic data generation guides

## Caching

Documentation is cached locally in `.cache/` to improve performance:
- Cache expires after 24 hours
- Can be cleared by deleting the `.cache` directory
- Configurable cache duration via environment variables

## Environment Variables

```bash
# Cache duration in hours (default: 24)
OMNIVERSE_DOCS_CACHE_HOURS=24

# Enable debug logging
OMNIVERSE_DOCS_DEBUG=1

# Custom documentation URLs (optional)
OMNIVERSE_DOCS_KIT_URL=https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/
OMNIVERSE_DOCS_USD_URL=https://openusd.org/
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/

# Lint
ruff check src/
```

## Integration with Vision Digital Twin Project

This MCP server is specifically designed to support the Industrial Dynamics Vision Digital Twin project by providing:

- Accurate API references for bootstrap system development
- Extension development patterns for standalone capabilities
- USD manipulation best practices
- Stage event handling documentation
- Physical accuracy implementation guidance

## License

Proprietary - Industrial Dynamics Vision Digital Twin Project

## Support

For issues or questions, refer to the project change log at `../logs/changes.log`

