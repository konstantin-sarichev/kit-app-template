# MCP Omniverse Documentation Server

**Instant Omniverse Documentation Access in Cursor**

---

## 🎯 What This Is

A Model Context Protocol (MCP) server that gives you instant access to NVIDIA Omniverse documentation directly in Cursor IDE. Ask questions about Omniverse development and get detailed answers with code examples!

---

## ⚡ Quick Start

### **1. Extract Files**
Extract this folder to a permanent location (e.g., `C:\Tools\mcp-omniverse-docs`)

### **2. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **3. Configure Cursor**
- Open the appropriate example file for your OS:
  - **Windows:** `mcp_config_WINDOWS_EXAMPLE.json`
  - **Mac:** `mcp_config_MAC_EXAMPLE.json`
  - **Linux:** `mcp_config_LINUX_EXAMPLE.json`
- Update the two paths (Python path and installation path)
- Copy the configuration to your Cursor `mcp.json` file
- Restart Cursor

### **4. Test**
Ask Cursor: *"Show me the Omniverse extension lifecycle guide"*

📖 **Full instructions:** See `INSTALL_FOR_USERS.md`

---

## 🛠️ What You Get

**5 Powerful Tools:**

1. **search_omniverse_docs** - Search all Omniverse documentation
2. **get_api_reference** - Get specific API docs (Kit/USD)
3. **get_extension_guide** - 6 extension development guides
4. **search_code_examples** - Find practical code examples
5. **search_omniverse_best_practices** - Vision DT best practices

**Built-in Content (Works Offline):**
- Extension lifecycle patterns
- UI development guides
- Stage manipulation examples
- Event system documentation
- Settings management
- Testing strategies
- Best practices for units, transforms, metadata, stage organization

---

## 📚 Example Queries

Try these in Cursor after installation:

### **Extension Development**
- *"Show me the extension lifecycle pattern"*
- *"How do I create UI in Omniverse?"*
- *"How do I handle stage events?"*

### **Best Practices**
- *"What are best practices for millimeter units?"*
- *"How should I handle transforms?"*
- *"How do I manage metadata?"*

### **Configuration**
- *"How do I configure render settings?"*
- *"Show me the settings system"*

---

## 📦 Package Contents

```
mcp-omniverse-docs/
├── src/                          # MCP server source code
│   ├── server.py                 # Main MCP server (5 tools)
│   ├── fetcher.py                # Documentation fetching
│   ├── cache.py                  # Caching system
│   └── config.py                 # Configuration
├── requirements.txt              # Python dependencies
├── INSTALL_FOR_USERS.md          # Complete installation guide
├── README_DISTRIBUTION.md        # This file
├── mcp_config_TEMPLATE.json      # Configuration template
├── mcp_config_WINDOWS_EXAMPLE.json  # Windows example
├── mcp_config_MAC_EXAMPLE.json   # macOS example
├── mcp_config_LINUX_EXAMPLE.json # Linux example
└── verify_structure.py           # Installation verification
```

---

## ✅ Installation Checklist

- [ ] Extracted to permanent location
- [ ] Ran `pip install -r requirements.txt`
- [ ] Ran `python verify_structure.py` (should show SUCCESS)
- [ ] Found Python path (`where python` or `which python3`)
- [ ] Updated example config with your paths
- [ ] Added config to Cursor `mcp.json`
- [ ] Restarted Cursor completely
- [ ] Tested with a query

---

## 🔧 Troubleshooting

### **"No server info found" error**
✅ Check that paths in `mcp.json` are correct  
✅ Use forward slashes `/` in paths  
✅ Make sure Python path points to actual python.exe  
✅ Restart Cursor completely (close all windows)

### **Dependencies not installed**
```bash
pip install -r requirements.txt --upgrade
```

### **Need help finding Python path**
**Windows:**
```batch
where python
```

**Mac/Linux:**
```bash
which python3
```

### **Still having issues?**
1. Enable debug mode: Set `"OMNIVERSE_DOCS_DEBUG": "1"` in config
2. Open Cursor Developer Tools (Help → Toggle Developer Tools)
3. Check Console tab for error messages

---

## 📍 Cursor MCP Config Location

Your `mcp.json` file is located at:

- **Windows:** `C:\Users\YourName\.cursor\mcp.json`
- **Mac:** `~/Library/Application Support/Cursor/User/globalStorage/mcp.json`
- **Linux:** `~/.config/Cursor/User/globalStorage/mcp.json`

Or access via: Cursor Settings (Ctrl+,) → Search "MCP" → Edit in settings.json

---

## 🎓 Features

### **Extension Development Guides**
- Lifecycle (startup/shutdown)
- UI development with omni.ui
- Stage manipulation
- Event system
- Settings management
- Testing

### **Best Practices**
- Millimeter unit handling
- Transform management (no scaling)
- Metadata management
- Stage organization

### **Live Documentation**
- Kit SDK documentation
- USD API reference
- Extension patterns
- Code examples

---

## 🚀 Getting Started

1. **Read:** `INSTALL_FOR_USERS.md` for detailed instructions
2. **Configure:** Use the example config for your platform
3. **Verify:** Run `python verify_structure.py`
4. **Test:** Ask Cursor an Omniverse question
5. **Enjoy:** Instant documentation access!

---

## 📊 System Requirements

- **Python:** 3.10 or higher
- **Cursor IDE:** Latest version
- **Internet:** For initial setup and live docs
- **Disk Space:** ~10MB for package + cache

---

## 🌟 What Makes This Useful

✅ **Instant Answers** - No need to search documentation websites  
✅ **Code Examples** - Get working code snippets instantly  
✅ **Best Practices** - Vision DT specific guidance included  
✅ **Offline Content** - Built-in guides work without internet  
✅ **Always Available** - Documentation in your IDE 24/7  

---

## 📞 Support

If you encounter issues:

1. Check `INSTALL_FOR_USERS.md` troubleshooting section
2. Run `python verify_structure.py` to check installation
3. Check Cursor Developer Console for errors
4. Enable debug mode in configuration

---

## 📄 License

Part of the Industrial Dynamics Vision Digital Twin project.

---

## 🎉 Ready to Install?

Open `INSTALL_FOR_USERS.md` and follow the step-by-step guide!

**Installation time: ~5 minutes**  
**Complexity: Easy** (copy, paste, restart)

---

**Version:** 0.1.0  
**Compatible with:** Cursor IDE with MCP support  
**Documentation Sources:** NVIDIA Omniverse Kit SDK, USD, Extensions



