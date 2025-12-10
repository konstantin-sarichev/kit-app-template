# Install MCP Omniverse Docs in Cursor

**Quick Installation Guide for End Users**

---

## 📋 Prerequisites

- **Python 3.10 or higher** installed
- **Cursor IDE** installed
- **Internet connection** (for initial setup)

---

## 🚀 Installation Steps

### **Step 1: Extract the Package**

Extract the `mcp-omniverse-docs.zip` file to a permanent location on your computer.

**Recommended locations:**
- **Windows:** `C:\Tools\mcp-omniverse-docs`
- **Mac:** `~/Tools/mcp-omniverse-docs`
- **Linux:** `~/tools/mcp-omniverse-docs`

⚠️ **Important:** Do NOT place it in a temporary folder or Downloads folder!

---

### **Step 2: Install Dependencies**

Open a terminal/command prompt in the extracted folder and run:

**Windows:**
```batch
cd C:\Tools\mcp-omniverse-docs
pip install -r requirements.txt
```

**Mac/Linux:**
```bash
cd ~/Tools/mcp-omniverse-docs
pip install -r requirements.txt
```

You should see packages being installed (mcp, httpx, beautifulsoup4, etc.)

---

### **Step 3: Verify Installation**

Run the verification script:

**Windows:**
```batch
python verify_structure.py
```

**Mac/Linux:**
```bash
python verify_structure.py
```

You should see:
```
[SUCCESS] ALL REQUIRED FILES PRESENT
```

---

### **Step 4: Find Your Python Path**

You need the full path to your Python executable.

**Windows:**
```batch
where python
```
Example output: `C:\Users\YourName\AppData\Local\Programs\Python\Python310\python.exe`

**Mac/Linux:**
```bash
which python3
```
Example output: `/usr/local/bin/python3`

**📝 Write this path down - you'll need it in the next step!**

---

### **Step 5: Configure Cursor**

#### **Option A: Using Cursor Settings UI (Recommended)**

1. Open **Cursor**
2. Press `Ctrl+,` (Windows/Linux) or `Cmd+,` (Mac) to open Settings
3. Search for **"MCP"** in the settings
4. Click **"Edit in settings.json"**
5. Add the configuration (see Step 6 below)

#### **Option B: Manual Configuration**

The MCP configuration file is located at:
- **Windows:** `C:\Users\YourName\.cursor\mcp.json`
- **Mac:** `~/Library/Application Support/Cursor/User/globalStorage/mcp.json`
- **Linux:** `~/.config/Cursor/User/globalStorage/mcp.json`

---

### **Step 6: Add the Configuration**

Copy this configuration and paste it into your `mcp.json` file:

**⚠️ IMPORTANT: You MUST update TWO paths:**
1. Replace `YOUR_PYTHON_PATH` with your Python path from Step 4
2. Replace `YOUR_INSTALLATION_PATH` with where you extracted the files

```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "YOUR_PYTHON_PATH",
      "args": ["-m", "src.server"],
      "cwd": "YOUR_INSTALLATION_PATH",
      "env": {
        "OMNIVERSE_DOCS_CACHE_HOURS": "24",
        "OMNIVERSE_DOCS_DEBUG": "0"
      }
    }
  }
}
```

#### **Example for Windows:**
```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "C:/Users/John/AppData/Local/Programs/Python/Python310/python.exe",
      "args": ["-m", "src.server"],
      "cwd": "C:/Tools/mcp-omniverse-docs",
      "env": {
        "OMNIVERSE_DOCS_CACHE_HOURS": "24",
        "OMNIVERSE_DOCS_DEBUG": "0"
      }
    }
  }
}
```

#### **Example for Mac:**
```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "/usr/local/bin/python3",
      "args": ["-m", "src.server"],
      "cwd": "/Users/john/Tools/mcp-omniverse-docs",
      "env": {
        "OMNIVERSE_DOCS_CACHE_HOURS": "24",
        "OMNIVERSE_DOCS_DEBUG": "0"
      }
    }
  }
}
```

#### **Example for Linux:**
```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "/usr/bin/python3",
      "args": ["-m", "src.server"],
      "cwd": "/home/john/tools/mcp-omniverse-docs",
      "env": {
        "OMNIVERSE_DOCS_CACHE_HOURS": "24",
        "OMNIVERSE_DOCS_DEBUG": "0"
      }
    }
  }
}
```

**💡 Tips for Paths:**
- Use **forward slashes** `/` even on Windows
- Make sure paths **don't have spaces** (or they're properly quoted)
- **No trailing slashes** at the end of paths

---

### **Step 7: Restart Cursor**

**⚠️ IMPORTANT:** You MUST completely restart Cursor for MCP changes to take effect.

1. Close **all** Cursor windows
2. Reopen Cursor

---

### **Step 8: Verify It's Working**

After Cursor restarts, open the **Developer Console** to check:

1. In Cursor, go to **Help** → **Toggle Developer Tools**
2. Click the **Console** tab
3. Look for messages about "omniverse-docs" MCP server

**Success messages:**
- `MCP server 'omniverse-docs' started`
- `Connected to MCP server`
- `5 tools detected`

**If you see errors**, see the Troubleshooting section below.

---

### **Step 9: Test It!**

In a Cursor chat, ask:

```
Show me the Omniverse extension lifecycle guide
```

or

```
What are best practices for handling millimeter units in Omniverse?
```

You should get detailed documentation with code examples!

---

## 🔧 Troubleshooting

### **Problem: "No server info found"**

**Solution:**
1. Check that Python path is correct (Step 4)
2. Check that installation path is correct (Step 6)
3. Make sure paths use forward slashes `/`
4. Completely restart Cursor (close all windows)

### **Problem: Dependencies not installed**

**Solution:**
```bash
cd YOUR_INSTALLATION_PATH
pip install -r requirements.txt --upgrade
```

### **Problem: Python not found**

**Solution:**
Use the full path to Python in the configuration:
- Windows: `C:/Users/YourName/AppData/Local/Programs/Python/Python310/python.exe`
- Mac: `/usr/local/bin/python3` or `/opt/homebrew/bin/python3`
- Linux: `/usr/bin/python3`

### **Problem: Module not found errors**

**Solution:**
1. Make sure you're in the correct directory
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Try using `python -m pip` instead of just `pip`

### **Problem: Permission denied (Mac/Linux)**

**Solution:**
```bash
chmod +x verify_structure.py
sudo pip install -r requirements.txt
```

### **Enable Debug Mode**

If you're still having issues, enable debug mode in your `mcp.json`:

```json
"env": {
  "OMNIVERSE_DOCS_DEBUG": "1"
}
```

Then check the Cursor Developer Console for detailed error messages.

---

## 🎯 What You Get

Once installed, you'll have access to **5 MCP tools** in Cursor:

1. **search_omniverse_docs** - Search across Omniverse documentation
2. **get_api_reference** - Get specific API documentation
3. **get_extension_guide** - Extension development guides (6 topics)
4. **search_code_examples** - Find code examples
5. **search_omniverse_best_practices** - Vision DT best practices (4 topics)

---

## 📚 Example Queries to Try

Once working, try these queries in Cursor:

### **Extension Development:**
- "Show me the extension lifecycle pattern"
- "How do I create UI in Omniverse extensions?"
- "How do I handle stage events?"

### **Best Practices:**
- "What are best practices for millimeter units?"
- "How should I handle transforms without scaling?"
- "How do I manage metadata in USD prims?"

### **Configuration:**
- "How do I configure render settings in Omniverse?"
- "Show me how to use the settings system"

---

## 🆘 Getting Help

If you encounter issues:

1. **Check Prerequisites**: Python 3.10+, Cursor installed
2. **Run Verification**: `python verify_structure.py`
3. **Check Console**: Cursor → Help → Toggle Developer Tools → Console
4. **Enable Debug**: Set `OMNIVERSE_DOCS_DEBUG` to `"1"`
5. **Check Paths**: Verify both Python and installation paths are correct

---

## ✅ Success Checklist

- [ ] Extracted to permanent location
- [ ] Dependencies installed
- [ ] Verification script passed
- [ ] Python path found
- [ ] Configuration added to `mcp.json`
- [ ] Paths updated in configuration
- [ ] Cursor completely restarted
- [ ] No errors in Developer Console
- [ ] Test query works

---

## 🎉 You're Done!

Once you see "5 tools detected" and test queries work, you're successfully using the MCP Omniverse Documentation Server in Cursor!

Enjoy instant access to Omniverse documentation right in your IDE! 🚀

---

**Version:** 0.1.0  
**Updated:** November 2025



