"""
Blog Fetcher - Retrieves posts from WordPress blogs via RSS/Atom feeds.

This module handles the extraction of blog content from WordPress sites,
respecting rate limits and caching results locally.
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Iterator, Optional
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

try:
    import requests
except ImportError:
    requests = None


@dataclass
class BlogPost:
    """Represents a single blog post."""
    id: str
    title: str
    url: str
    date: str
    content: str
    excerpt: str
    categories: list[str]
    tags: list[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BlogPost":
        return cls(**data)


class BlogFetcher:
    """
    Fetches blog posts from WordPress sites.

    Supports both RSS feeds and the WordPress REST API for more comprehensive access.
    Implements polite crawling with rate limiting and caching.
    """

    def __init__(
        self,
        blog_url: str,
        cache_dir: Optional[Path] = None,
        rate_limit: float = 1.0  # seconds between requests
    ):
        if requests is None:
            raise ImportError("requests library required. Install with: pip install requests")

        self.blog_url = blog_url.rstrip("/")
        self.cache_dir = cache_dir or Path.home() / ".blog_explorer_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self._last_request = 0.0

    def _wait_for_rate_limit(self):
        """Ensure we respect rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def _get_cache_path(self, key: str) -> Path:
        """Generate cache file path for a given key."""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.json"

    def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content with rate limiting and error handling."""
        self._wait_for_rate_limit()
        try:
            response = requests.get(url, timeout=30, headers={
                "User-Agent": "BlogExplorer/0.1 (Research Tool)"
            })
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def fetch_rss_feed(self, feed_url: Optional[str] = None) -> list[BlogPost]:
        """
        Fetch posts from RSS feed.

        WordPress default feed is at /feed/ and typically contains recent posts.
        """
        url = feed_url or f"{self.blog_url}/feed/"
        content = self._fetch_url(url)
        if not content:
            return []

        posts = []
        try:
            root = ET.fromstring(content)
            # Handle both RSS and Atom namespaces
            namespaces = {
                "content": "http://purl.org/rss/1.0/modules/content/",
                "dc": "http://purl.org/dc/elements/1.1/",
                "atom": "http://www.w3.org/2005/Atom"
            }

            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")

                # Try to get full content, fall back to description
                content_elem = item.find("content:encoded", namespaces)
                description = item.findtext("description", "")
                full_content = content_elem.text if content_elem is not None else description

                # Extract categories and tags
                categories = [cat.text for cat in item.findall("category")
                             if cat.get("domain") == "category" and cat.text]
                tags = [cat.text for cat in item.findall("category")
                       if cat.get("domain") == "post_tag" and cat.text]

                post = BlogPost(
                    id=hashlib.md5(link.encode()).hexdigest()[:12],
                    title=title,
                    url=link,
                    date=pub_date,
                    content=full_content or "",
                    excerpt=description[:500] if description else "",
                    categories=categories,
                    tags=tags
                )
                posts.append(post)

        except ET.ParseError as e:
            print(f"Error parsing RSS feed: {e}")

        return posts

    def fetch_via_wp_api(self, per_page: int = 100, max_pages: int = 100) -> Iterator[BlogPost]:
        """
        Fetch posts via WordPress REST API for comprehensive access.

        This provides access to all posts, not just recent ones.
        Yields posts one at a time to handle large archives.
        """
        api_url = f"{self.blog_url}/wp-json/wp/v2/posts"
        page = 1

        while page <= max_pages:
            url = f"{api_url}?per_page={per_page}&page={page}&_embed"
            content = self._fetch_url(url)

            if not content:
                break

            try:
                posts_data = json.loads(content)
                if not posts_data:
                    break

                for post_data in posts_data:
                    # Extract embedded taxonomy terms if available
                    embedded = post_data.get("_embedded", {})
                    terms = embedded.get("wp:term", [])

                    categories = []
                    tags = []
                    for term_group in terms:
                        for term in term_group:
                            if term.get("taxonomy") == "category":
                                categories.append(term.get("name", ""))
                            elif term.get("taxonomy") == "post_tag":
                                tags.append(term.get("name", ""))

                    post = BlogPost(
                        id=str(post_data.get("id", "")),
                        title=post_data.get("title", {}).get("rendered", ""),
                        url=post_data.get("link", ""),
                        date=post_data.get("date", ""),
                        content=post_data.get("content", {}).get("rendered", ""),
                        excerpt=post_data.get("excerpt", {}).get("rendered", ""),
                        categories=categories,
                        tags=tags
                    )
                    yield post

                page += 1

            except json.JSONDecodeError as e:
                print(f"Error parsing API response: {e}")
                break

    def fetch_sitemap_urls(self) -> list[str]:
        """
        Parse WordPress sitemap for all post URLs.

        Useful for discovering the full extent of the archive.
        """
        sitemap_url = f"{self.blog_url}/sitemap.xml"
        content = self._fetch_url(sitemap_url)

        if not content:
            # Try alternate locations
            for alt in ["/sitemap_index.xml", "/wp-sitemap.xml"]:
                content = self._fetch_url(f"{self.blog_url}{alt}")
                if content:
                    break

        if not content:
            return []

        urls = []
        try:
            root = ET.fromstring(content)
            namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Check if this is a sitemap index
            for sitemap in root.findall(".//ns:sitemap/ns:loc", namespace):
                if "post-sitemap" in sitemap.text:
                    # Fetch the posts sitemap
                    sub_content = self._fetch_url(sitemap.text)
                    if sub_content:
                        sub_root = ET.fromstring(sub_content)
                        for url_elem in sub_root.findall(".//ns:url/ns:loc", namespace):
                            urls.append(url_elem.text)

            # Also check direct URLs in case it's not an index
            for url_elem in root.findall(".//ns:url/ns:loc", namespace):
                urls.append(url_elem.text)

        except ET.ParseError as e:
            print(f"Error parsing sitemap: {e}")

        return urls

    def save_posts(self, posts: list[BlogPost], filepath: Path):
        """Save posts to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in posts], f, indent=2, ensure_ascii=False)

    def load_posts(self, filepath: Path) -> list[BlogPost]:
        """Load posts from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return [BlogPost.from_dict(d) for d in json.load(f)]
