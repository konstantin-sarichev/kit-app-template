"""Setup script for mcp-omniverse-docs."""

from setuptools import setup, find_packages

setup(
    name="mcp-omniverse-docs",
    version="0.1.0",
    description="MCP server for Omniverse documentation",
    author="Industrial Dynamics",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "mcp>=0.9.0",
        "httpx>=0.27.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=5.0.0",
        "aiofiles>=24.0.0",
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-omniverse-docs=src.server:main",
        ],
    },
)

