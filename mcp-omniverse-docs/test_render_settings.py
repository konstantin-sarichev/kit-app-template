"""Test script to fetch Omniverse render settings documentation."""

import asyncio
from src.server import call_tool
from src.fetcher import DocFetcher


async def test_render_settings():
    """Test fetching render settings documentation."""
    print("=" * 80)
    print("TESTING MCP SERVER - RENDER SETTINGS DOCUMENTATION")
    print("=" * 80 + "\n")
    
    # Test 1: Search for render settings
    print("TEST 1: Searching for 'render settings' documentation...\n")
    
    args = {
        "query": "render settings design",
        "doc_type": "all",
        "include_code": True
    }
    
    try:
        results = await call_tool("search_omniverse_docs", args)
        
        if results and len(results) > 0:
            print("SUCCESS: Retrieved render settings documentation\n")
            print("-" * 80)
            print("OVERVIEW SECTION:")
            print("-" * 80 + "\n")
            
            # Extract and print the overview
            content = results[0].text
            
            # Try to find and extract overview section
            lines = content.split('\n')
            in_overview = False
            overview_lines = []
            
            for i, line in enumerate(lines):
                # Look for overview-related headers
                if any(keyword in line.lower() for keyword in ['overview', 'introduction', 'about', 'what is']):
                    in_overview = True
                    overview_lines.append(line)
                    continue
                
                # If we're in overview section, collect lines until next major section
                if in_overview:
                    if line.strip().startswith('##') and i > 0:
                        # Hit next major section, stop
                        break
                    overview_lines.append(line)
                    
                    # Limit to reasonable length
                    if len(overview_lines) > 50:
                        break
            
            if overview_lines:
                overview_text = '\n'.join(overview_lines)
                print(overview_text[:2000])  # Limit output
            else:
                # If no specific overview section found, show beginning
                print(content[:2000])
            
            print("\n" + "-" * 80)
            print(f"Total content length: {len(content)} characters")
            print("-" * 80 + "\n")
            
        else:
            print("No results found. This could mean:")
            print("  - Documentation URLs need adjustment")
            print("  - Network connectivity issues")
            print("  - Search query needs refinement\n")
            
    except Exception as e:
        print(f"Error during search: {e}\n")
        import traceback
        traceback.print_exc()
    
    # Test 2: Try to get API reference for render settings
    print("\nTEST 2: Searching for RTX render settings API...\n")
    
    args2 = {
        "query": "RTX renderer settings API",
        "doc_type": "kit",
        "include_code": True
    }
    
    try:
        results2 = await call_tool("search_omniverse_docs", args2)
        
        if results2 and len(results2) > 0:
            print("SUCCESS: Found RTX renderer documentation\n")
            print("-" * 80)
            print("RTX RENDERER OVERVIEW:")
            print("-" * 80 + "\n")
            print(results2[0].text[:1500])
            print("\n...")
        else:
            print("No RTX renderer API docs found in initial search")
            
    except Exception as e:
        print(f"Error during RTX API search: {e}\n")
    
    # Test 3: Try best practices for render settings
    print("\nTEST 3: Checking built-in best practices...\n")
    
    # Show what we have for stage organization (which includes render setup)
    args3 = {
        "topic": "stage"
    }
    
    try:
        results3 = await call_tool("search_omniverse_best_practices", args3)
        
        if results3 and len(results3) > 0:
            print("SUCCESS: Retrieved stage organization best practices\n")
            print("-" * 80)
            print("STAGE ORGANIZATION (includes render context):")
            print("-" * 80 + "\n")
            print(results3[0].text[:1000])
            print("\n...")
        
    except Exception as e:
        print(f"Error retrieving best practices: {e}\n")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")
    
    # Show available documentation sources
    print("NOTE: The MCP server attempts to fetch documentation from:")
    print("  - Kit SDK: https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/")
    print("  - USD: https://openusd.org/")
    print("  - Extensions: https://docs.omniverse.nvidia.com/extensions/latest/")
    print("  - Replicator: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/")
    print("\nFor offline/detailed render settings, consider:")
    print("  - Using get_extension_guide with 'settings' topic")
    print("  - Searching for 'omni.rtx' or 'render settings' APIs")
    print("  - Checking carb.settings for render configuration")
    print()


async def test_direct_fetcher():
    """Test the fetcher directly."""
    print("=" * 80)
    print("TESTING DIRECT DOCUMENTATION FETCHER")
    print("=" * 80 + "\n")
    
    fetcher = DocFetcher()
    
    # Try a few common render settings URLs
    test_urls = [
        "https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph.html",
        "https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/",
    ]
    
    for url in test_urls:
        print(f"Attempting to fetch: {url}")
        try:
            content = await fetcher.fetch_url(url, use_cache=False)
            if content:
                print(f"  SUCCESS: Retrieved {len(content)} characters")
                # Parse it
                parsed = fetcher.parse_html_content(content, extract_code=False)
                print(f"  Title: {parsed.get('title', 'N/A')}")
                print(f"  Text length: {len(parsed.get('text', ''))}")
                print(f"  Headings: {len(parsed.get('headings', []))}")
                if parsed.get('headings'):
                    print(f"  First few headings:")
                    for heading in parsed['headings'][:5]:
                        print(f"    - {heading['text']}")
                print()
            else:
                print(f"  FAILED: Could not retrieve content\n")
        except Exception as e:
            print(f"  ERROR: {e}\n")
    
    await fetcher.close()
    
    print("=" * 80 + "\n")


async def main():
    """Main test runner."""
    print("\n" + "=" * 80)
    print("MCP OMNIVERSE DOCS - RENDER SETTINGS TEST")
    print("=" * 80 + "\n")
    
    # Run the MCP tool tests
    await test_render_settings()
    
    # Optionally test the fetcher directly
    print("\n" + "=" * 80)
    print("Would you like to test direct fetcher? (Testing MCP tools first)")
    print("=" * 80 + "\n")
    
    # Uncomment to test fetcher directly
    # await test_direct_fetcher()
    
    print("\nAll tests complete!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()

