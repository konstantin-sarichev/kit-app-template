"""Test script for MCP Omniverse Documentation Server."""

import asyncio
import json
from src.server import list_tools, call_tool
from src.cache import clear_cache


async def test_list_tools():
    """Test listing available tools."""
    print("=" * 60)
    print("TEST: List Available Tools")
    print("=" * 60)
    
    tools = await list_tools()
    print(f"\nFound {len(tools)} tools:\n")
    
    for tool in tools:
        print(f"  • {tool.name}")
        print(f"    Description: {tool.description[:80]}...")
        print()
    
    return len(tools) == 5  # Should have 5 tools


async def test_search_docs():
    """Test searching documentation."""
    print("=" * 60)
    print("TEST: Search Documentation")
    print("=" * 60)
    
    args = {
        "query": "stage events",
        "doc_type": "all",
        "include_code": True
    }
    
    print(f"\nSearching for: {args['query']}\n")
    
    try:
        results = await call_tool("search_omniverse_docs", args)
        print(f"Results returned: {len(results)} content block(s)")
        
        if results and len(results) > 0:
            preview = results[0].text[:200]
            print(f"\nPreview:\n{preview}...\n")
            return True
        else:
            print("No results returned")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_get_api():
    """Test getting API reference."""
    print("=" * 60)
    print("TEST: Get API Reference")
    print("=" * 60)
    
    args = {
        "api_path": "omni.usd.get_context",
        "api_type": "kit"
    }
    
    print(f"\nGetting API docs for: {args['api_path']}\n")
    
    try:
        results = await call_tool("get_api_reference", args)
        print(f"Results returned: {len(results)} content block(s)")
        
        if results and len(results) > 0:
            preview = results[0].text[:200]
            print(f"\nPreview:\n{preview}...\n")
            return True
        else:
            print("No results returned")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_extension_guide():
    """Test getting extension guide."""
    print("=" * 60)
    print("TEST: Get Extension Guide")
    print("=" * 60)
    
    args = {
        "topic": "lifecycle"
    }
    
    print(f"\nGetting guide for: {args['topic']}\n")
    
    try:
        results = await call_tool("get_extension_guide", args)
        print(f"Results returned: {len(results)} content block(s)")
        
        if results and len(results) > 0:
            preview = results[0].text[:200]
            print(f"\nPreview:\n{preview}...\n")
            return True
        else:
            print("No results returned")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_code_examples():
    """Test searching code examples."""
    print("=" * 60)
    print("TEST: Search Code Examples")
    print("=" * 60)
    
    args = {
        "query": "create USD prim",
        "language": "python"
    }
    
    print(f"\nSearching for examples: {args['query']}\n")
    
    try:
        results = await call_tool("search_code_examples", args)
        print(f"Results returned: {len(results)} content block(s)")
        
        if results and len(results) > 0:
            preview = results[0].text[:200]
            print(f"\nPreview:\n{preview}...\n")
            return True
        else:
            print("No results returned")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_best_practices():
    """Test searching best practices."""
    print("=" * 60)
    print("TEST: Search Best Practices")
    print("=" * 60)
    
    args = {
        "topic": "units"
    }
    
    print(f"\nSearching for best practices: {args['topic']}\n")
    
    try:
        results = await call_tool("search_omniverse_best_practices", args)
        print(f"Results returned: {len(results)} content block(s)")
        
        if results and len(results) > 0:
            preview = results[0].text[:200]
            print(f"\nPreview:\n{preview}...\n")
            return True
        else:
            print("No results returned")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MCP OMNIVERSE DOCUMENTATION SERVER - TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("List Tools", test_list_tools),
        ("Extension Guide", test_extension_guide),
        ("Best Practices", test_best_practices),
        # Network-dependent tests (may fail without internet)
        # ("Search Docs", test_search_docs),
        # ("API Reference", test_get_api),
        # ("Code Examples", test_code_examples),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            passed = await test_func()
            results[test_name] = "PASSED" if passed else "FAILED"
        except Exception as e:
            results[test_name] = f"ERROR: {e}"
        
        await asyncio.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60 + "\n")
    
    for test_name, result in results.items():
        status = "✓" if result == "PASSED" else "✗"
        print(f"  {status} {test_name}: {result}")
    
    passed = sum(1 for r in results.values() if r == "PASSED")
    total = len(results)
    
    print(f"\n  Total: {passed}/{total} tests passed\n")
    
    return passed == total


async def main():
    """Main test runner."""
    try:
        success = await run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

