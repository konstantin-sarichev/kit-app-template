# Quick Distribution Guide - Choose Your Path

**🎯 Goal:** Share MCP Omniverse Docs with others so they can use it in Cursor

---

## 🚀 Pick Your Distribution Method (30 Second Decision)

### For Your Dev Team → Use Git
```bash
# 1. Create repo (GitHub/GitLab)
cd mcp-omniverse-docs
git init && git add . && git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main

# 2. Share repo URL with team
# 3. Done! Team clones and installs
```

**Team installs:**
```bash
git clone <repo-url>
cd mcp-omniverse-docs
pip install -r requirements.txt
```

---

### For Non-Technical Users → Use Zip
```bash
# 1. Create zip (from kit-app-template/)
cd mcp-omniverse-docs
# Clean up
rm -rf .cache __pycache__ src/__pycache__

# Windows
Compress-Archive -Path * -DestinationPath ../mcp-omniverse-docs-v0.1.0.zip

# Mac/Linux
zip -r ../mcp-omniverse-docs-v0.1.0.zip . -x "*.pyc" "*__pycache__*"

# 2. Share zip file
# 3. Include INSTALL.md
```

**Users extract and:**
```bash
cd mcp-omniverse-docs
pip install -r requirements.txt
# Add to Cursor per INSTALL.md
```

---

### For Professional Distribution → Use PyPI
```bash
# 1. Build package
pip install build twine
python -m build

# 2. Upload to PyPI
python -m twine upload dist/*

# 3. Share package name
```

**Users install:**
```bash
pip install mcp-omniverse-docs
```

---

### For Enterprise → Use Wheel
```bash
# 1. Build wheel
pip install build
python -m build --wheel

# 2. Copy wheel to shared location
cp dist/*.whl //company-share/tools/

# 3. Share installation command
```

**Users install:**
```bash
pip install \\company-share\tools\mcp-omniverse-docs-0.1.0-py3-none-any.whl
```

---

## 📋 What Users Need After Installation

### 1. Cursor Configuration

Users need to add this to Cursor MCP settings:

```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/mcp-omniverse-docs"
    }
  }
}
```

**Location of Cursor MCP Settings:**
- Open Cursor Settings (Ctrl+, or Cmd+,)
- Search for "MCP"
- Click "Edit in settings.json"
- Add the configuration
- Adjust `cwd` to their installation path

### 2. Verification

Users run:
```bash
cd mcp-omniverse-docs
python verify_structure.py
```

Should see:
```
[SUCCESS] ALL REQUIRED FILES PRESENT
```

### 3. Test

In Cursor, ask:
```
How do I subscribe to stage open events in Omniverse?
```

Should get comprehensive documentation response.

---

## 📦 Recommended Distribution Package Contents

**Minimum (for Zip/Wheel):**
- Source code (`src/` folder)
- `requirements.txt`
- `README.md`
- `INSTALL.md`
- `mcp_config.example.json`

**Professional (add these):**
- `USAGE.md`
- `verify_structure.py`
- `QUICKSTART.md`
- Installation scripts (`install.bat`, `install.sh`)
- `CHANGELOG.md`

**Complete (add these):**
- `DISTRIBUTION.md` (this guide)
- `MCP_SUMMARY.md`
- Test scripts
- `.gitignore` (if using Git)
- `LICENSE`

---

## 🎯 Quick Decisions

| If you want... | Use this method | Time to setup | User install time |
|----------------|-----------------|---------------|-------------------|
| Version control + collaboration | Git Repository | 5 min | 2 min |
| Simplest sharing | Zip Archive | 2 min | 3 min |
| Professional distribution | PyPI Package | 10 min | 30 sec |
| Internal enterprise | Wheel + Server | 5 min | 1 min |
| Isolated environment | Docker | 15 min | 5 min |

---

## ⚡ Super Quick Start (For Your Team Right Now)

### 1. Create GitHub Repo (Private)
```bash
cd mcp-omniverse-docs
git init
git add .
git commit -m "MCP Omniverse Documentation Server v0.1.0"
# Create repo on GitHub, then:
git remote add origin https://github.com/IndustrialDynamics/mcp-omniverse-docs.git
git push -u origin main
```

### 2. Create QUICKSTART.md in Repo
```markdown
# Quick Start - 3 Steps

## 1. Clone & Install
\`\`\`bash
git clone https://github.com/IndustrialDynamics/mcp-omniverse-docs.git
cd mcp-omniverse-docs
pip install -r requirements.txt
\`\`\`

## 2. Configure Cursor
Add to Cursor MCP settings:
\`\`\`json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/YOUR/PATH/TO/mcp-omniverse-docs"
    }
  }
}
\`\`\`

## 3. Test
Ask Cursor: "How do I subscribe to stage events in Omniverse?"

See INSTALL.md for detailed instructions.
\`\`\`

### 3. Share with Team
Send Slack/Email:
```
🎉 New Tool: Omniverse Documentation MCP for Cursor

Gives you instant access to Omniverse docs right in Cursor!

Install: https://github.com/IndustrialDynamics/mcp-omniverse-docs

Takes 2 minutes. See QUICKSTART.md in repo.

Questions? Check INSTALL.md or ask me.
```

---

## 🔒 For Private/Internal Use

### Option A: Private Git Repository
- GitHub (Enterprise or Team plan)
- GitLab (private repos free)
- Bitbucket (private repos free)
- Azure DevOps (private repos free)

**No changes needed!** Just make repo private.

### Option B: Internal File Server
1. Create zip: `mcp-omniverse-docs-v0.1.0.zip`
2. Place on: `\\company-share\tools\`
3. Share location with team

### Option C: Internal PyPI
Use devpi or Artifactory:
```bash
# Upload to internal PyPI
python -m twine upload --repository internal dist/*
```

Team installs:
```bash
pip install mcp-omniverse-docs --index-url http://pypi.company.com/simple/
```

---

## 📞 Support Documentation for Users

### Include This in Your README

```markdown
## Getting Help

1. **Installation issues?** See INSTALL.md troubleshooting section
2. **Configuration issues?** Run `python verify_structure.py`
3. **Not working in Cursor?** 
   - Check Cursor developer console (Help → Toggle Developer Tools)
   - Look for MCP-related errors
4. **Still stuck?** Contact: your-email@company.com
```

---

## ✅ Distribution Checklist

Before sharing:

- [ ] Remove unnecessary files (cache, test outputs)
- [ ] Test installation on clean machine
- [ ] Verify Cursor integration works
- [ ] Check all paths in documentation are correct
- [ ] Include clear installation instructions
- [ ] Provide Cursor configuration example
- [ ] Include verification script
- [ ] Add support contact information

---

## 🎬 Do This Next

1. **Choose method** (recommend: Git for team, Zip for others)
2. **Create package** (5 minutes)
3. **Test on colleague's machine** (verify it works)
4. **Document support process** (where to ask questions)
5. **Share** (send link/file to team)

---

## 💡 Pro Tips

### Make It Easy
- Provide exact copy-paste commands
- Include screenshots in INSTALL.md
- Create video walkthrough (2 minutes)
- Test on Windows, Mac, Linux

### Reduce Support
- Anticipate common issues in FAQ
- Make verification script user-friendly
- Provide multiple contact methods
- Keep documentation updated

### Track Success
- Ask users to confirm installation works
- Collect feedback on pain points
- Update documentation based on questions
- Iterate on installation process

---

**You're ready to share! Choose your method and go. 🚀**

See DISTRIBUTION.md for detailed explanations of each method.

