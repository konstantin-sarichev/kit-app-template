# Usage Guide - MCP Omniverse Documentation Server

## Quick Reference

The MCP server provides 5 main tools for accessing Omniverse documentation:

1. **search_omniverse_docs** - General documentation search
2. **get_api_reference** - Specific API documentation
3. **get_extension_guide** - Extension development guides
4. **search_code_examples** - Find code examples
5. **search_omniverse_best_practices** - Best practices for Vision DT

## Using in Cursor

### Natural Language Queries

Simply ask Cursor questions about Omniverse, and it will automatically use the MCP tools:

**Examples:**

- "How do I subscribe to stage open events in Omniverse?"
- "Show me the USD Stage API documentation"
- "What's the best way to handle units in millimeters?"
- "Give me an example of creating a USD prim"
- "How does the extension lifecycle work?"

### Explicit Tool Usage

You can also explicitly request tool usage:

**Search Documentation:**
```
Use search_omniverse_docs to find information about "stage events"
```

**Get API Reference:**
```
Use get_api_reference for "omni.usd.get_context" (kit API)
```

**Extension Guides:**
```
Use get_extension_guide for "lifecycle"
```

## Common Use Cases

### 1. Bootstrap System Development

**Query:** "How do I listen for stage open events to run my bootstrap code?"

The MCP will provide:
- Event subscription patterns
- StageEventType enumeration
- Example code for stage event handling
- Best practices for event cleanup

### 2. USD Prim Manipulation

**Query:** "Show me how to create a USD prim and set metadata"

Returns:
- USD Stage API reference
- Prim creation examples
- Metadata setting patterns
- CustomData usage

### 3. Extension Development

**Query:** "What's the proper extension lifecycle structure?"

Provides:
- IExt interface documentation
- on_startup/on_shutdown patterns
- Resource management best practices
- Example extension code

### 4. Unit Handling

**Query:** "How do I set stage units to millimeters?"

Returns:
- UsdGeom.SetStageMetersPerUnit usage
- Best practices for millimeter units
- Verification code
- Physical accuracy guidelines

### 5. Transform Management

**Query:** "How should I handle transforms without using scale?"

Provides:
- Transform operation best practices
- Geometry sizing without scale
- Normalization patterns
- Physical accuracy requirements

## Tool Details

### 1. search_omniverse_docs

**Purpose:** General search across all Omniverse documentation

**Parameters:**
- `query` (required): Your search query
- `doc_type` (optional): "kit", "usd", "extension", or "all" (default: "all")
- `include_code` (optional): Include code examples (default: true)

**Example Queries:**
- "stage event subscription"
- "USD prim creation"
- "extension lifecycle"
- "omni.ui window creation"

**Returns:**
- Multiple relevant documentation excerpts
- Links to full documentation
- Code examples (if available)
- Source identification (Kit vs USD)

### 2. get_api_reference

**Purpose:** Get detailed documentation for a specific API

**Parameters:**
- `api_path` (required): Full API path (e.g., "omni.usd.get_context")
- `api_type` (required): "kit" or "usd"

**Example API Paths:**

**Kit APIs:**
- `omni.usd.get_context`
- `omni.kit.commands.execute`
- `omni.ui.Window`
- `omni.timeline.get_timeline_interface`

**USD APIs:**
- `pxr.Usd.Stage`
- `pxr.UsdGeom.Xformable`
- `pxr.Sdf.Path`
- `pxr.Gf.Vec3d`

**Returns:**
- Detailed API documentation
- Parameters and return types
- Usage examples
- Related APIs

### 3. get_extension_guide

**Purpose:** Get comprehensive extension development guides

**Available Topics:**
- `lifecycle` - Extension startup/shutdown
- `ui` - UI development with omni.ui
- `stage` - Stage manipulation and USD
- `events` - Event system and subscriptions
- `settings` - Configuration management
- `tests` - Testing extensions

**Returns:**
- Comprehensive guide for the topic
- Code examples
- Best practices
- Common patterns

### 4. search_code_examples

**Purpose:** Find practical code examples

**Parameters:**
- `query` (required): What you want to accomplish
- `language` (optional): "python" or "cpp" (default: "python")

**Example Queries:**
- "create USD prim"
- "subscribe to selection events"
- "create UI window with buttons"
- "set transform on prim"

**Returns:**
- Relevant code examples
- Source documentation links
- Implementation context

### 5. search_omniverse_best_practices

**Purpose:** Get best practices for Vision Digital Twin development

**Available Topics:**
- `units` - Unit handling (millimeters)
- `transforms` - Transform management without scaling
- `metadata` - Asset metadata management
- `stage` - Stage organization

**Returns:**
- Best practice guidelines
- Example implementations
- Validation code
- Physical accuracy requirements

## Integration with Vision Digital Twin Project

### Bootstrap Development Workflow

1. **Query for stage events:**
   ```
   How do I subscribe to stage open events?
   ```

2. **Query for extension structure:**
   ```
   Show me extension lifecycle best practices
   ```

3. **Query for unit enforcement:**
   ```
   How do I set and verify millimeter units?
   ```

4. **Query for metadata:**
   ```
   How do I add custom metadata to USD prims?
   ```

### Asset Creation Workflow

1. **Query USD basics:**
   ```
   How do I create a USD asset with proper structure?
   ```

2. **Query for references:**
   ```
   How do I use USD references vs composition?
   ```

3. **Query for validation:**
   ```
   How do I check prim metadata and attributes?
   ```

## Tips for Effective Usage

### Be Specific

❌ "How do cameras work?"
✅ "How do I set camera sensor size in USD?"

### Mention Context

❌ "Create a prim"
✅ "Create a camera prim with metadata in Omniverse Kit"

### Request Examples

❌ "What is omni.usd?"
✅ "Show me examples of using omni.usd.get_context()"

### Combine Queries

You can ask multi-part questions:
```
How do I:
1. Subscribe to stage open events
2. Set the stage units to millimeters
3. Validate all prims have required metadata
```

## Performance Notes

- **First query**: May be slower while fetching documentation
- **Cached queries**: Subsequent queries are fast (24-hour cache)
- **Cache location**: `.cache/` directory
- **Clear cache**: Delete `.cache/` folder to force refresh

## Debugging

### Enable Debug Mode

Set in your MCP config:
```json
"OMNIVERSE_DOCS_DEBUG": "1"
```

### Check Cache

```bash
# See cached items
ls .cache/

# Check cache size
du -sh .cache/
```

### Test Manually

```bash
cd mcp-omniverse-docs
python -m src.server
```

## Limitations

1. **Documentation Availability**: Only accesses public Omniverse documentation
2. **Network Required**: Initial queries need internet connection
3. **Cache Expiry**: Cache expires after 24 hours by default
4. **Search Scope**: Focuses on Kit SDK, USD, and extension development

## Next Steps

- See [INSTALL.md](INSTALL.md) for installation troubleshooting
- Check [README.md](README.md) for architecture details
- Review project change log: `../logs/changes.log`

## Support

For Vision Digital Twin project-specific questions, refer to:
- System prompt: `../bootstrap/systemprompt.md`
- Project review: `../logs/project_review_2025-11-12.md`
- Status: `../logs/STATUS.md`

