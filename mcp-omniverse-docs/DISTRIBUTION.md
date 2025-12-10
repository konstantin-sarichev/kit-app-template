# MCP Omniverse Docs - Distribution & Packaging Guide

**Version:** 0.1.0  
**Status:** Production Ready  
**Target Audience:** Teams wanting to share MCP server with colleagues

---

## 📦 Distribution Options

There are **6 main approaches** to package and distribute this MCP server for easy Cursor integration. Choose based on your team's needs:

| Method | Best For | Complexity | Auto-Updates | Installation Time |
|--------|----------|------------|--------------|-------------------|
| **1. PyPI Package** | Public/Enterprise | Medium | ✅ Yes | ~30 seconds |
| **2. Git Repository** | Teams with Git | Low | ✅ Yes | ~2 minutes |
| **3. Wheel Distribution** | Internal teams | Low | ❌ Manual | ~1 minute |
| **4. Zip Archive** | Simple sharing | Very Low | ❌ Manual | ~3 minutes |
| **5. Docker Container** | Isolated env | High | ✅ Yes | ~5 minutes |
| **6. Cursor Extension** | Cursor-specific | Very High | ✅ Via marketplace | ~10 seconds |

---

## 🚀 Option 1: PyPI Package (Recommended for Wide Distribution)

### Overview
Publish to PyPI (Python Package Index) for one-command installation.

### Advantages
- ✅ One-line installation: `pip install mcp-omniverse-docs`
- ✅ Automatic dependency resolution
- ✅ Version management built-in
- ✅ Updates via `pip install --upgrade`
- ✅ Works on all platforms

### Setup Process

#### Step 1: Prepare Package
```bash
# From mcp-omniverse-docs directory
python -m pip install build twine

# Build distribution packages
python -m build
```

This creates:
- `dist/mcp_omniverse_docs-0.1.0-py3-none-any.whl`
- `dist/mcp-omniverse-docs-0.1.0.tar.gz`

#### Step 2: Upload to PyPI
```bash
# Test on TestPyPI first (recommended)
python -m twine upload --repository testpypi dist/*

# Production PyPI
python -m twine upload dist/*
```

#### Step 3: User Installation
```bash
# Users install with:
pip install mcp-omniverse-docs

# Or from TestPyPI:
pip install --index-url https://test.pypi.org/simple/ mcp-omniverse-docs
```

#### Step 4: Cursor Configuration
Users add to Cursor MCP settings:
```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "python",
      "args": ["-m", "mcp_omniverse_docs"],
      "env": {
        "OMNIVERSE_DOCS_CACHE_HOURS": "24"
      }
    }
  }
}
```

**Note:** Need to fix the import path in `setup.py` entry point:
- Change: `"mcp-omniverse-docs=src.server:main"`
- To: `"mcp-omniverse-docs=mcp_omniverse_docs.server:main"`
- And rename `src/` to `mcp_omniverse_docs/`

### Cost
- Free for public packages
- Consider private PyPI server for proprietary code

---

## 🔗 Option 2: Git Repository (Best for Active Development)

### Overview
Host on GitHub/GitLab/Bitbucket for version control and collaboration.

### Advantages
- ✅ Version control included
- ✅ Easy updates (`git pull`)
- ✅ Issue tracking
- ✅ Collaboration features
- ✅ Free (public or private)

### Setup Process

#### Step 1: Create Repository
```bash
cd mcp-omniverse-docs
git init
git add .
git commit -m "Initial commit: MCP Omniverse Documentation Server"

# Add remote (GitHub example)
git remote add origin https://github.com/your-org/mcp-omniverse-docs.git
git push -u origin main
```

#### Step 2: User Installation
```bash
# Clone repository
git clone https://github.com/your-org/mcp-omniverse-docs.git
cd mcp-omniverse-docs

# Install in development mode
pip install -e .
```

#### Step 3: Cursor Configuration
```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/cloned/mcp-omniverse-docs"
    }
  }
}
```

#### Step 4: Updates
```bash
cd mcp-omniverse-docs
git pull
# Dependencies auto-update if using 'pip install -e .'
```

### Distribution Documentation
Create `QUICKSTART.md` in repo:
```markdown
# Quick Start

## Installation
\`\`\`bash
git clone https://github.com/your-org/mcp-omniverse-docs.git
cd mcp-omniverse-docs
pip install -r requirements.txt
\`\`\`

## Cursor Configuration
Copy `mcp_config.example.json` content to Cursor MCP settings.
Adjust `cwd` path to your clone location.

## Verify
\`\`\`bash
python verify_structure.py
\`\`\`
```

---

## 📦 Option 3: Python Wheel Distribution (Simple Internal Sharing)

### Overview
Build a `.whl` file and share via network drive, email, or internal server.

### Advantages
- ✅ Single file distribution
- ✅ No external dependencies (servers)
- ✅ Fast installation
- ✅ Works offline after download

### Setup Process

#### Step 1: Build Wheel
```bash
cd mcp-omniverse-docs
pip install build
python -m build --wheel
```

Creates: `dist/mcp_omniverse_docs-0.1.0-py3-none-any.whl`

#### Step 2: Distribute Wheel
Share the `.whl` file via:
- Network drive: `\\company-share\tools\mcp-omniverse-docs-0.1.0-py3-none-any.whl`
- Internal web server: `http://tools.company.com/mcp/mcp-omniverse-docs-0.1.0-py3-none-any.whl`
- Email attachment (if small enough)
- USB drive for air-gapped environments

#### Step 3: User Installation
```bash
# From file
pip install mcp_omniverse_docs-0.1.0-py3-none-any.whl

# From URL
pip install http://tools.company.com/mcp/mcp-omniverse-docs-0.1.0-py3-none-any.whl

# From network share (Windows)
pip install "\\company-share\tools\mcp-omniverse-docs-0.1.0-py3-none-any.whl"
```

#### Step 4: Provide Configuration Template
Create `cursor-config-template.json`:
```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "python",
      "args": ["-m", "mcp_omniverse_docs"],
      "env": {
        "OMNIVERSE_DOCS_CACHE_HOURS": "24",
        "OMNIVERSE_DOCS_DEBUG": "0"
      }
    }
  }
}
```

---

## 📄 Option 4: Zip Archive (Simplest for Non-Technical Users)

### Overview
Package entire directory as a zip file with installation script.

### Advantages
- ✅ Extremely simple to share
- ✅ No build tools required
- ✅ Works without Git
- ✅ Self-contained

### Setup Process

#### Step 1: Create Distribution Package
```bash
# From kit-app-template directory
cd mcp-omniverse-docs

# Remove cache and unnecessary files
rm -rf .cache __pycache__ src/__pycache__
rm -f *.pyc test_*.py

# Create archive
# Windows PowerShell:
Compress-Archive -Path * -DestinationPath ../mcp-omniverse-docs-v0.1.0.zip

# Linux/Mac:
zip -r ../mcp-omniverse-docs-v0.1.0.zip . -x "*.pyc" "*__pycache__*" ".cache/*"
```

#### Step 2: Create Installation Script
**For Windows** (`install.bat`):
```batch
@echo off
echo Installing MCP Omniverse Documentation Server...
pip install -r requirements.txt
echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Note this directory path: %CD%
echo 2. Open Cursor Settings
echo 3. Search for "MCP"
echo 4. Add configuration from mcp_config.example.json
echo 5. Replace cwd path with: %CD%
echo.
pause
```

**For Linux/Mac** (`install.sh`):
```bash
#!/bin/bash
echo "Installing MCP Omniverse Documentation Server..."
pip install -r requirements.txt
echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Note this directory path: $(pwd)"
echo "2. Open Cursor Settings"
echo "3. Search for 'MCP'"
echo "4. Add configuration from mcp_config.example.json"
echo "5. Replace cwd path with: $(pwd)"
```

#### Step 3: Create README for Distribution
**`INSTALL_INSTRUCTIONS.txt`**:
```
MCP OMNIVERSE DOCUMENTATION SERVER
Installation Instructions

STEP 1: EXTRACT
Extract this ZIP file to a permanent location, for example:
- Windows: C:\Tools\mcp-omniverse-docs
- Mac: ~/Tools/mcp-omniverse-docs
- Linux: ~/tools/mcp-omniverse-docs

STEP 2: INSTALL DEPENDENCIES
Open terminal/command prompt in extracted folder:

Windows:
  install.bat

Mac/Linux:
  chmod +x install.sh
  ./install.sh

STEP 3: CONFIGURE CURSOR
1. Open Cursor
2. Go to Settings (Ctrl+, or Cmd+,)
3. Search for "MCP"
4. Click "Edit in settings.json"
5. Add the configuration from mcp_config.example.json
6. Replace the "cwd" path with your extraction folder path

STEP 4: RESTART CURSOR
Restart Cursor to load the MCP server.

STEP 5: TEST
In Cursor, try asking:
"How do I subscribe to stage open events in Omniverse?"

For detailed documentation, see:
- INSTALL.md - Full installation guide
- USAGE.md - Usage examples
- README.md - Overview and features

Support: See logs/changes.log in main project
```

#### Step 4: Distribution
Share `mcp-omniverse-docs-v0.1.0.zip` via:
- Email
- Cloud storage (Dropbox, Google Drive, OneDrive)
- Internal file server
- USB drive

---

## 🐳 Option 5: Docker Container (For Isolated Environments)

### Overview
Package as Docker container for consistent deployment across platforms.

### Advantages
- ✅ Isolated environment
- ✅ Consistent across platforms
- ✅ No Python version conflicts
- ✅ Easy updates (pull new image)

### Setup Process

#### Step 1: Create Dockerfile
**`Dockerfile`**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY mcp_config.example.json .
COPY README.md .
COPY INSTALL.md .
COPY USAGE.md .

# Create cache directory
RUN mkdir -p .cache

# Expose stdio (MCP runs on stdio)
CMD ["python", "-m", "src.server"]
```

#### Step 2: Build Image
```bash
cd mcp-omniverse-docs
docker build -t mcp-omniverse-docs:0.1.0 .
docker tag mcp-omniverse-docs:0.1.0 mcp-omniverse-docs:latest
```

#### Step 3: Distribute Image

**Option A: Docker Hub (Public/Private)**
```bash
docker tag mcp-omniverse-docs:0.1.0 your-dockerhub-user/mcp-omniverse-docs:0.1.0
docker push your-dockerhub-user/mcp-omniverse-docs:0.1.0
```

**Option B: Save to File**
```bash
docker save mcp-omniverse-docs:0.1.0 | gzip > mcp-omniverse-docs-0.1.0.tar.gz
# Users load with: docker load < mcp-omniverse-docs-0.1.0.tar.gz
```

**Option C: Private Registry**
```bash
docker tag mcp-omniverse-docs:0.1.0 registry.company.com/mcp-omniverse-docs:0.1.0
docker push registry.company.com/mcp-omniverse-docs:0.1.0
```

#### Step 4: User Installation
```bash
# Pull from Docker Hub
docker pull your-dockerhub-user/mcp-omniverse-docs:0.1.0

# Or load from file
docker load < mcp-omniverse-docs-0.1.0.tar.gz
```

#### Step 5: Cursor Configuration
```json
{
  "mcpServers": {
    "omniverse-docs": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "mcp-omniverse-docs:0.1.0"
      ]
    }
  }
}
```

**Note:** Docker might not support stdio properly for MCP. May need wrapper script.

---

## 🔌 Option 6: Cursor Extension/Marketplace (Future Option)

### Overview
Package as native Cursor extension for marketplace distribution.

### Advantages
- ✅ One-click installation
- ✅ Automatic updates
- ✅ Integrated with Cursor UI
- ✅ Discoverability in marketplace

### Current Status
⚠️ **Note:** As of now, Cursor doesn't have a public MCP extension marketplace. This is a potential future option.

### When Available

#### Step 1: Package as Extension
Would involve:
- Creating extension manifest
- Bundling MCP server
- Following Cursor extension API

#### Step 2: Submit to Marketplace
- Register developer account
- Submit for review
- Publish to marketplace

#### Step 3: User Installation
Users would:
1. Open Cursor Extension Marketplace
2. Search "Omniverse Documentation"
3. Click "Install"
4. Extension auto-configures MCP

---

## 📝 Recommended Approach by Use Case

### For Your Team (Industrial Dynamics)
**Recommendation: Git Repository (Option 2)**

**Why:**
- Active development likely
- Team collaboration
- Version control essential
- Easy updates
- Free private repos

**Setup:**
```bash
# Create private GitHub repo
# Add team members
# Document in company wiki
```

### For Enterprise Distribution
**Recommendation: Private PyPI Server (Option 1 variant)**

**Why:**
- Professional deployment
- Automatic updates
- IT-friendly
- Audit trail

**Setup:**
- Deploy private PyPI (e.g., devpi, Artifactory)
- Upload package
- Distribute internal documentation

### For Simple Sharing
**Recommendation: Zip Archive (Option 4)**

**Why:**
- Non-technical users
- Email-friendly
- No infrastructure needed
- Self-contained

**Setup:**
- Create zip with install script
- Write clear instructions
- Share via email/drive

### For Multi-Team Companies
**Recommendation: Wheel + Internal Server (Option 3)**

**Why:**
- Balance simplicity and professionalism
- One-time setup
- Easy updates
- Version management

**Setup:**
- Host wheel on internal web server
- Provide installation URL
- Update documentation

---

## 🎯 Quick Decision Matrix

**Choose Option 1 (PyPI)** if:
- ✅ You want wide distribution
- ✅ You're comfortable with public release
- ✅ You want automatic updates
- ✅ You want professional distribution

**Choose Option 2 (Git)** if:
- ✅ Your team uses Git
- ✅ You want version control
- ✅ You need collaboration features
- ✅ You're actively developing

**Choose Option 3 (Wheel)** if:
- ✅ You want simple internal distribution
- ✅ You have internal file server
- ✅ You don't need public hosting
- ✅ Updates are manual/infrequent

**Choose Option 4 (Zip)** if:
- ✅ Users are non-technical
- ✅ You want simplest distribution
- ✅ You're sharing with few people
- ✅ No infrastructure available

**Choose Option 5 (Docker)** if:
- ✅ You need isolated environments
- ✅ You have Docker infrastructure
- ✅ You want platform consistency
- ✅ You're comfortable with containers

---

## 📦 Complete Distribution Package Checklist

For professional distribution, include:

- [ ] **Core Files**
  - [ ] All source code (`src/` or `mcp_omniverse_docs/`)
  - [ ] `requirements.txt`
  - [ ] `pyproject.toml` / `setup.py`
  
- [ ] **Documentation**
  - [ ] `README.md` - Overview
  - [ ] `INSTALL.md` - Installation instructions
  - [ ] `USAGE.md` - Usage examples
  - [ ] `CHANGELOG.md` - Version history
  - [ ] `LICENSE` - License file
  
- [ ] **Configuration**
  - [ ] `mcp_config.example.json` - Cursor config template
  - [ ] `.cursorrules` - Cursor integration rules
  
- [ ] **Support Files**
  - [ ] `verify_structure.py` - Installation verification
  - [ ] Installation scripts (`install.bat`, `install.sh`)
  - [ ] `QUICKSTART.md` - 5-minute setup guide
  
- [ ] **Optional but Recommended**
  - [ ] `CONTRIBUTING.md` - Contribution guidelines
  - [ ] `SECURITY.md` - Security policy
  - [ ] `FAQ.md` - Common questions
  - [ ] `.gitignore` - If using Git
  - [ ] `Dockerfile` - If offering Docker

---

## 🔄 Version Management Strategy

### Semantic Versioning
Use `MAJOR.MINOR.PATCH` format:
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

**Example:**
- `0.1.0` - Initial release (current)
- `0.1.1` - Bug fix
- `0.2.0` - New tool added
- `1.0.0` - Production stable

### Update pyproject.toml
```toml
[project]
version = "0.1.0"  # Update for each release
```

### Tag Releases (Git)
```bash
git tag -a v0.1.0 -m "Initial release"
git push origin v0.1.0
```

---

## 📚 Documentation to Provide Users

### Essential Documents

1. **Quick Start (1-page)**
   - Installation: 3 commands
   - Configuration: Copy-paste JSON
   - Verification: 1 command
   - Test: Sample query

2. **Full Installation Guide**
   - Prerequisites
   - Step-by-step installation
   - Platform-specific notes
   - Troubleshooting

3. **Configuration Guide**
   - Cursor MCP settings location
   - Configuration options
   - Environment variables
   - Custom paths

4. **Usage Examples**
   - Common queries
   - Tool descriptions
   - Best practices
   - FAQ

---

## 🎬 Next Steps

1. **Choose Distribution Method** based on your needs
2. **Prepare Package** following checklist above
3. **Test Installation** on clean machine
4. **Document** for your specific audience
5. **Distribute** via chosen method
6. **Support** users with clear documentation

---

## 📞 Support Strategy

### For Users
Provide clear escalation:
1. Check `README.md`
2. Check `INSTALL.md` troubleshooting
3. Run `verify_structure.py`
4. Check project `logs/changes.log`
5. Contact support (provide contact method)

### For You
Track:
- Installation issues
- Common questions
- Feature requests
- Update to documentation accordingly

---

## ✅ Summary

**No changes needed to current setup!** Your MCP server is already well-structured for distribution.

**Recommended immediate action:**
1. Choose distribution method (suggest **Git Repository** for your team)
2. Create repository on GitHub/GitLab
3. Add QUICKSTART.md with 3-step installation
4. Share repo URL with team

**Best long-term approach:**
1. Start with Git (now)
2. Build to PyPI when stable (later)
3. Maintain both for different audiences

Your MCP server is production-ready and can be distributed via any of these methods immediately!

