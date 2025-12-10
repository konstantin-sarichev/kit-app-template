# Installation Guide - MCP Omniverse Documentation Server

## Prerequisites

- Python 3.10 or higher
- Cursor IDE
- Internet connection (for fetching documentation)

## Step 1: Install Dependencies

Navigate to the MCP server directory:

```bash
cd G:/Vision_Example_1/kit-app-template/mcp-omniverse-docs
```

Install the package:

```bash
# Option A: Install in development mode (recommended)
pip install -e .

# Option B: Install from requirements
pip install -r requirements.txt
```

## Step 2: Configure Cursor

### Option A: Via Cursor Settings UI

1. Open Cursor Settings (Ctrl+, or Cmd+,)
2. Search for "MCP" in settings
3. Click "Edit in settings.json"
4. Add the MCP server configuration:

```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "G:/Vision_Example_1/kit-app-template/mcp-omniverse-docs",
      "env": {
        "OMNIVERSE_DOCS_CACHE_HOURS": "24",
        "OMNIVERSE_DOCS_DEBUG": "0"
      }
    }
  }
}
```

### Option B: Manual Configuration

1. Locate your Cursor MCP configuration file:
   - Windows: `%APPDATA%\Cursor\User\globalStorage\mcp_config.json`
   - Mac: `~/Library/Application Support/Cursor/User/globalStorage/mcp_config.json`
   - Linux: `~/.config/Cursor/User/globalStorage/mcp_config.json`

2. Copy `mcp_config.example.json` content to the file
3. Adjust the `cwd` path to match your installation location

## Step 3: Verify Installation

1. Restart Cursor
2. Open the Command Palette (Ctrl+Shift+P or Cmd+Shift+P)
3. Type "MCP" to see available MCP commands
4. Try querying: "Search Omniverse docs for stage events"

## Step 4: Test the Server

Run the test script:

```bash
python -m src.server
```

The server should start and wait for input via stdio. Press Ctrl+C to stop.

## Troubleshooting

### Server Not Starting

1. **Check Python version:**
   ```bash
   python --version  # Should be 3.10+
   ```

2. **Verify dependencies:**
   ```bash
   pip list | grep mcp
   ```

3. **Enable debug mode:**
   Edit your MCP config and set:
   ```json
   "OMNIVERSE_DOCS_DEBUG": "1"
   ```

### Connection Issues

1. **Check Cursor logs:**
   - Help → Toggle Developer Tools
   - Look for MCP-related errors in Console

2. **Verify path:**
   Make sure `cwd` in config points to the correct directory

3. **Test manually:**
   ```bash
   cd G:/Vision_Example_1/kit-app-template/mcp-omniverse-docs
   python -m src.server
   ```

### Cache Issues

Clear the cache:

```bash
# Windows
rmdir /s .cache

# Mac/Linux
rm -rf .cache
```

## Configuration Options

### Environment Variables

- `OMNIVERSE_DOCS_CACHE_HOURS`: Cache duration (default: 24)
- `OMNIVERSE_DOCS_DEBUG`: Enable debug output (0 or 1)
- `OMNIVERSE_DOCS_KIT_URL`: Custom Kit SDK docs URL
- `OMNIVERSE_DOCS_USD_URL`: Custom USD docs URL

### Example Custom Configuration

```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "G:/Vision_Example_1/kit-app-template/mcp-omniverse-docs",
      "env": {
        "OMNIVERSE_DOCS_CACHE_HOURS": "48",
        "OMNIVERSE_DOCS_DEBUG": "1",
        "OMNIVERSE_DOCS_KIT_URL": "https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/"
      }
    }
  }
}
```

## Next Steps

See [USAGE.md](USAGE.md) for examples of using the MCP server with Cursor.

## Support

For issues specific to this MCP server, check:
- Project change log: `../logs/changes.log`
- MCP server README: `README.md`

