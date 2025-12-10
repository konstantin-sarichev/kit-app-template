"""Test if MCP server can access live Omniverse documentation."""

import asyncio
import sys
import io

# Fix unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from src.fetcher import DocFetcher

async def test_documentation_access():
    """Test access to various documentation sources."""
    
    print("=" * 80)
    print("TESTING LIVE DOCUMENTATION ACCESS")
    print("=" * 80 + "\n")
    
    fetcher = DocFetcher()
    
    test_urls = [
        ("Kit SDK Main", "https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/"),
        ("USD Main", "https://openusd.org/"),
        ("USD API", "https://openusd.org/release/api/usd_page_front.html"),
        ("Extensions", "https://docs.omniverse.nvidia.com/extensions/latest/"),
        ("Kit GitHub", "https://github.com/NVIDIA-Omniverse/kit-extension-template"),
    ]
    
    results = []
    
    for name, url in test_urls:
        print(f"Testing: {name}")
        print(f"URL: {url}")
        
        try:
            content = await fetcher.fetch_url(url, use_cache=False)
            
            if content:
                print(f"  [OK] SUCCESS - Retrieved {len(content)} characters")
                
                # Try to parse
                parsed = fetcher.parse_html_content(content, extract_code=False)
                print(f"  [OK] Title: {parsed.get('title', 'N/A')[:60]}")
                print(f"  [OK] Content: {len(parsed.get('text', ''))} characters")
                print(f"  [OK] Headings: {len(parsed.get('headings', []))} found")
                
                results.append({
                    "name": name,
                    "url": url,
                    "status": "SUCCESS",
                    "size": len(content),
                    "title": parsed.get('title', 'N/A')
                })
            else:
                print(f"  [FAIL] FAILED - No content retrieved")
                results.append({
                    "name": name,
                    "url": url,
                    "status": "FAILED",
                    "error": "No content"
                })
                
        except Exception as e:
            print(f"  [ERROR] ERROR - {str(e)}")
            results.append({
                "name": name,
                "url": url,
                "status": "ERROR",
                "error": str(e)
            })
        
        print()
    
    await fetcher.close()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80 + "\n")
    
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    total_count = len(results)
    
    print(f"Successful: {success_count}/{total_count}")
    print()
    
    for result in results:
        status_icon = "[OK]" if result["status"] == "SUCCESS" else "[FAIL]"
        print(f"  {status_icon} {result['name']}: {result['status']}")
        if result["status"] == "SUCCESS":
            print(f"      Size: {result.get('size', 0):,} bytes")
        elif "error" in result:
            print(f"      Error: {result['error']}")
    
    print("\n" + "=" * 80)
    
    if success_count == 0:
        print("\n[WARNING] No documentation sources are accessible.")
        print("This means the MCP server can only use built-in content.")
        print("\nPossible causes:")
        print("  - Network connectivity issues")
        print("  - Documentation sites require authentication")
        print("  - Sites blocking automated access")
        print("  - URLs have changed")
    elif success_count < total_count:
        print(f"\n[WARNING] PARTIAL ACCESS: {success_count}/{total_count} sources accessible.")
        print("Some documentation is available, but not all sources work.")
    else:
        print("\n[SUCCESS] FULL ACCESS: All documentation sources accessible!")
        print("The MCP server can fetch live documentation.")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_documentation_access())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()

