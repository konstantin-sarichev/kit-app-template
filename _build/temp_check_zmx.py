"""Temporary script to inspect the ZMX file contents."""
import sys
sys.path.insert(0, '_build/bootstrap')

import tempfile
import re
from pathlib import Path
from zmxtools import zar

zar_path = '_build/assets/Lenses/ZeMax/58257_002_BB.ZAR'
temp_dir = tempfile.mkdtemp()
zar.extract(zar_path, temp_dir)

zmx_files = list(Path(temp_dir).rglob('*.ZMX'))
print(f"Found {len(zmx_files)} ZMX files")

if zmx_files:
    zmx_file = zmx_files[0]
    print(f"Inspecting: {zmx_file}")

    content = open(zmx_file, 'r', encoding='utf-16').read()
    print(f"File size: {len(content)} chars")

    # Check for key patterns
    print("\n=== Pattern search ===")
    patterns = [
        ('EFFL', r'EFFL\s+[-\d.eE+]+'),
        ('ENPD', r'ENPD\s+[-\d.eE+]+'),
        ('FNUM', r'FNUM\s+[-\d.eE+]+'),
        ('ENPP', r'ENPP\s+[-\d.eE+]+'),
        ('EXPP', r'EXPP\s+[-\d.eE+]+'),
        ('TOTR', r'TOTR\s+[-\d.eE+]+'),
        ('MAGI', r'MAGI\s+[-\d.eE+]+'),
        ('MAGN', r'MAGN\s+[-\d.eE+]+'),
        ('IMNA', r'IMNA\s+[-\d.eE+]+'),
        ('OBJN', r'OBJN\s+[-\d.eE+]+'),
        ('NA', r'\sNA\s+[-\d.eE+]+'),
        ('DISZ', r'DISZ\s+[-\d.eE+]+'),  # Surface thickness
        ('FLAP', r'FLAP\s+\d+\s+[-\d.eE+]+'),  # Float aperture
    ]

    for name, pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"{name}: {matches[:5]}")
        else:
            print(f"{name}: NOT FOUND")

    # Show first 3500 chars
    print("\n=== First 3500 chars ===")
    print(content[:3500])

    # Also show the SURF section to understand the structure
    print("\n=== Surface 0-2 data ===")
    surf_matches = re.findall(r'SURF\s+[012].*?(?=SURF\s+[3-9]|$)', content, re.DOTALL)
    for match in surf_matches[:3]:
        print(match[:500])
        print("---")
