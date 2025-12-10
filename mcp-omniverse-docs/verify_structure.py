"""Verify MCP server structure without dependencies."""

import os
from pathlib import Path

def check_structure():
    """Check if all required files exist."""
    print("=" * 60)
    print("MCP OMNIVERSE DOCS - STRUCTURE VERIFICATION")
    print("=" * 60 + "\n")
    
    root = Path(__file__).parent
    
    required_files = {
        "Core Files": [
            "README.md",
            "INSTALL.md",
            "USAGE.md",
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            ".gitignore",
        ],
        "Source Files": [
            "src/__init__.py",
            "src/__main__.py",
            "src/server.py",
            "src/config.py",
            "src/cache.py",
            "src/fetcher.py",
        ],
        "Configuration": [
            "mcp_config.example.json",
            ".cursorrules",
        ],
        "Testing": [
            "test_mcp.py",
            "verify_structure.py",
        ],
    }
    
    all_good = True
    
    for category, files in required_files.items():
        print(f"\n{category}:")
        for file in files:
            filepath = root / file
            exists = filepath.exists()
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {file}")
            if not exists:
                all_good = False
    
    # Check for cache directory (should be created on first run)
    cache_dir = root / ".cache"
    print(f"\nCache Directory:")
    print(f"  {'[OK]' if cache_dir.exists() else '[PENDING]'} .cache/ (created on first use)")
    
    # Count source lines
    total_lines = 0
    for file in (root / "src").glob("*.py"):
        with open(file, 'r', encoding='utf-8') as f:
            total_lines += len(f.readlines())
    
    print(f"\nStatistics:")
    print(f"  • Total source files: {len(list((root / 'src').glob('*.py')))}")
    print(f"  • Total source lines: ~{total_lines}")
    
    print("\n" + "=" * 60)
    if all_good:
        print("[SUCCESS] ALL REQUIRED FILES PRESENT")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure Cursor (see INSTALL.md)")
        print("  3. Test the server: python test_mcp.py")
    else:
        print("[ERROR] SOME FILES ARE MISSING")
        print("\nPlease ensure all files are created.")
    print("=" * 60 + "\n")
    
    return all_good


if __name__ == "__main__":
    success = check_structure()
    exit(0 if success else 1)

