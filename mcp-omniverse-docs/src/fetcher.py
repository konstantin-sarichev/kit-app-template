"""Documentation fetcher and parser."""

import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .cache import get_cached, set_cached
from .config import DEBUG, DOC_SOURCES


class DocFetcher:
    """Fetches and parses documentation from various sources."""

    def __init__(self):
        """Initialize fetcher."""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def fetch_url(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Fetch content from URL with caching."""
        if use_cache:
            cached = await get_cached(f"url:{url}")
            if cached:
                if DEBUG:
                    print(f"Cache hit: {url}")
                return cached

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            content = response.text

            if use_cache:
                await set_cached(f"url:{url}", content)

            return content
        except httpx.HTTPError as e:
            if DEBUG:
                print(f"Error fetching {url}: {e}")
            return None

    def parse_html_content(self, html: str, extract_code: bool = True) -> Dict[str, any]:
        """Parse HTML documentation content."""
        soup = BeautifulSoup(html, "lxml")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Extract main content
        main_content = soup.find("main") or soup.find("article") or soup.find("body")
        if not main_content:
            main_content = soup

        # Extract text
        text = main_content.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        result = {"text": text, "title": soup.title.string if soup.title else ""}

        # Extract code examples if requested
        if extract_code:
            code_blocks = []
            for code in main_content.find_all(["code", "pre"]):
                code_text = code.get_text(strip=True)
                if len(code_text) > 10:  # Only meaningful code blocks
                    language = "python"  # Default
                    # Try to detect language from class
                    classes = code.get("class", [])
                    for cls in classes:
                        if "python" in str(cls).lower():
                            language = "python"
                        elif "cpp" in str(cls).lower() or "c++" in str(cls).lower():
                            language = "cpp"

                    code_blocks.append({"code": code_text, "language": language})

            result["code_examples"] = code_blocks

        # Extract headings for structure
        headings = []
        for heading in main_content.find_all(["h1", "h2", "h3", "h4"]):
            headings.append(
                {"level": int(heading.name[1]), "text": heading.get_text(strip=True)}
            )

        result["headings"] = headings

        return result

    async def search_kit_docs(self, query: str) -> List[Dict[str, str]]:
        """Search Kit SDK documentation."""
        base_url = DOC_SOURCES["kit"]["base_url"]

        # Try to construct search URL or fetch main docs
        # Note: Actual implementation may need to adapt to real docs structure
        search_urls = [
            urljoin(base_url, "source/extensions/omni.kit.commands/docs/index.html"),
            urljoin(base_url, "source/extensions/omni.usd/docs/index.html"),
            urljoin(base_url, "guide/extensions_basic.html"),
        ]

        results = []
        query_lower = query.lower()

        for url in search_urls:
            html = await self.fetch_url(url)
            if not html:
                continue

            parsed = self.parse_html_content(html)
            text_lower = parsed["text"].lower()

            # Check if query matches content
            if query_lower in text_lower:
                # Extract relevant section
                lines = parsed["text"].split("\n")
                relevant_lines = []

                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        # Get context: 3 lines before and after
                        start = max(0, i - 3)
                        end = min(len(lines), i + 4)
                        relevant_lines.extend(lines[start:end])

                results.append(
                    {
                        "url": url,
                        "title": parsed["title"],
                        "excerpt": "\n".join(relevant_lines[:500]),  # Limit length
                        "source": "kit",
                    }
                )

        return results

    async def search_usd_docs(self, query: str) -> List[Dict[str, str]]:
        """Search USD documentation."""
        base_url = DOC_SOURCES["usd"]["base_url"]

        # Common USD API pages
        search_urls = [
            urljoin(base_url, "release/api/usd_page_front.html"),
            urljoin(base_url, "release/api/class_usd_stage.html"),
            urljoin(base_url, "release/api/class_usd_prim.html"),
        ]

        results = []
        query_lower = query.lower()

        for url in search_urls:
            html = await self.fetch_url(url)
            if not html:
                continue

            parsed = self.parse_html_content(html)
            text_lower = parsed["text"].lower()

            if query_lower in text_lower:
                results.append(
                    {
                        "url": url,
                        "title": parsed["title"],
                        "excerpt": parsed["text"][:1000],
                        "source": "usd",
                        "code_examples": parsed.get("code_examples", [])[:3],
                    }
                )

        return results

    async def get_api_docs(self, api_path: str, api_type: str = "kit") -> Optional[Dict]:
        """Get specific API documentation."""
        cache_key = f"api:{api_type}:{api_path}"
        cached = await get_cached(cache_key)
        if cached:
            return cached

        # Construct URL based on API type and path
        if api_type == "kit":
            base_url = DOC_SOURCES["kit"]["base_url"]
            # Example: omni.usd.get_context -> extensions/omni.usd/docs/
            parts = api_path.split(".")
            if len(parts) >= 2:
                module = ".".join(parts[:2])  # e.g., omni.usd
                url = urljoin(base_url, f"source/extensions/{module}/docs/index.html")
            else:
                return None
        elif api_type == "usd":
            base_url = DOC_SOURCES["usd"]["base_url"]
            # Example: pxr.Usd.Stage -> class_usd_stage.html
            parts = api_path.split(".")
            if len(parts) >= 2:
                class_name = parts[-1]
                url = urljoin(base_url, f"release/api/class_{class_name.lower()}.html")
            else:
                return None
        else:
            return None

        html = await self.fetch_url(url)
        if not html:
            return None

        parsed = self.parse_html_content(html, extract_code=True)

        result = {
            "api_path": api_path,
            "api_type": api_type,
            "url": url,
            "title": parsed["title"],
            "content": parsed["text"],
            "code_examples": parsed.get("code_examples", []),
            "headings": parsed.get("headings", []),
        }

        await set_cached(cache_key, result)
        return result

