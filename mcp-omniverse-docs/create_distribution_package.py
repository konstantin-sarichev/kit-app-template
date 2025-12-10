"""Create a distribution package of the MCP server."""

import shutil
import zipfile
import sys
import io
from pathlib import Path
from datetime import datetime

# Fix unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def create_distribution():
    """Create a clean distribution package."""
    
    print("=" * 80)
    print("CREATING MCP OMNIVERSE DOCS DISTRIBUTION PACKAGE")
    print("=" * 80 + "\n")
    
    # Get root directory
    root = Path(__file__).parent
    
    # Files and folders to include
    include_files = [
        # Core source code
        "src/__init__.py",
        "src/__main__.py",
        "src/server.py",
        "src/config.py",
        "src/cache.py",
        "src/fetcher.py",
        
        # Dependencies and setup
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        
        # Documentation
        "README_DISTRIBUTION.md",  # Main README for users
        "INSTALL_FOR_USERS.md",  # Detailed installation guide
        "USAGE.md",  # Usage guide
        
        # Configuration examples
        "mcp_config_TEMPLATE.json",
        "mcp_config_WINDOWS_EXAMPLE.json",
        "mcp_config_MAC_EXAMPLE.json",
        "mcp_config_LINUX_EXAMPLE.json",
        
        # Verification and utilities
        "verify_structure.py",
        
        # License and metadata
        ".gitignore",
    ]
    
    # Optional files (include if they exist)
    optional_files = [
        "LICENSE",
        "CHANGELOG.md",
    ]
    
    # Files to explicitly exclude
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        ".cache",
        "test_*.py",
        ".git",
        ".gitignore",
        "MCP_SUMMARY.md",  # Internal documentation
        "DISTRIBUTION.md",  # Developer documentation
        "SESSION_*.md",  # Internal session files
    ]
    
    # Create distribution name
    version = "0.1.0"
    timestamp = datetime.now().strftime("%Y%m%d")
    dist_name = f"mcp-omniverse-docs-v{version}"
    dist_dir = root.parent / f"{dist_name}"
    zip_name = root.parent / f"{dist_name}.zip"
    
    # Clean up old distribution if exists
    if dist_dir.exists():
        print(f"Removing old distribution directory: {dist_dir.name}")
        shutil.rmtree(dist_dir)
    
    if zip_name.exists():
        print(f"Removing old zip file: {zip_name.name}")
        zip_name.unlink()
    
    # Create fresh distribution directory
    print(f"\nCreating distribution directory: {dist_dir.name}")
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Create src directory
    (dist_dir / "src").mkdir(exist_ok=True)
    
    # Copy files
    print("\nCopying files:")
    copied_count = 0
    
    for file_path in include_files:
        src_file = root / file_path
        if src_file.exists():
            dest_file = dist_dir / file_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest_file)
            print(f"  [OK] {file_path}")
            copied_count += 1
        else:
            print(f"  [SKIP] {file_path} (not found)")
    
    # Copy optional files
    for file_path in optional_files:
        src_file = root / file_path
        if src_file.exists():
            shutil.copy2(src_file, dist_dir / file_path)
            print(f"  [OK] {file_path} (optional)")
            copied_count += 1
    
    print(f"\nCopied {copied_count} files")
    
    # Create README.md (symlink to distribution readme)
    readme_dist = dist_dir / "README_DISTRIBUTION.md"
    readme_main = dist_dir / "README.md"
    if readme_dist.exists() and not readme_main.exists():
        shutil.copy2(readme_dist, readme_main)
        print("  [OK] Created README.md from README_DISTRIBUTION.md")
    
    # Create .gitignore for the distribution
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*.so
.Python

# Cache
.cache/
*.cache

# Virtual environments
venv/
env/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
    (dist_dir / ".gitignore").write_text(gitignore_content)
    print("  [OK] Created .gitignore")
    
    # Create the zip file
    print(f"\nCreating zip archive: {zip_name.name}")
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in dist_dir.rglob('*'):
            if file_path.is_file():
                # Get relative path
                arcname = file_path.relative_to(dist_dir.parent)
                zipf.write(file_path, arcname)
    
    zip_size = zip_name.stat().st_size
    zip_size_mb = zip_size / (1024 * 1024)
    
    print(f"[OK] Created: {zip_name.name} ({zip_size_mb:.2f} MB)")
    
    # Summary
    print("\n" + "=" * 80)
    print("DISTRIBUTION PACKAGE CREATED")
    print("=" * 80)
    print(f"\nPackage: {zip_name.name}")
    print(f"Size: {zip_size_mb:.2f} MB")
    print(f"Files: {copied_count}")
    print(f"Location: {zip_name}")
    
    print("\n" + "=" * 80)
    print("READY TO DISTRIBUTE")
    print("=" * 80)
    print(f"\nShare this file: {zip_name.name}")
    print("\nRecipients should:")
    print("  1. Extract the zip file")
    print("  2. Read README.md")
    print("  3. Follow INSTALL_FOR_USERS.md")
    print("  4. Use the appropriate mcp_config example for their OS")
    print("\nInstallation takes ~5 minutes")
    print("=" * 80 + "\n")
    
    # Clean up temporary directory
    print(f"Cleaning up temporary directory: {dist_dir.name}")
    shutil.rmtree(dist_dir)
    
    return zip_name


if __name__ == "__main__":
    try:
        zip_file = create_distribution()
        print(f"\n[SUCCESS] Distribution package ready: {zip_file.name}")
    except Exception as e:
        print(f"\n[ERROR] Error creating distribution: {e}")
        import traceback
        traceback.print_exc()

