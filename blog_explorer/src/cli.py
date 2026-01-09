"""
Command-line interface for the Blog Explorer.

Provides interactive exploration of blog archives from the terminal.
"""

import argparse
import sys
from pathlib import Path

from .fetcher import BlogFetcher
from .indexer import BlogIndexer
from .explorer import BlogExplorer


def cmd_fetch(args):
    """Fetch and index a blog."""
    print(f"Fetching blog from {args.url}...")

    fetcher = BlogFetcher(args.url)

    if args.method == "api":
        print("Using WordPress REST API (this may take a while for large blogs)...")
        posts = list(fetcher.fetch_via_wp_api(max_pages=args.max_pages))
    else:
        print("Using RSS feed (limited to recent posts)...")
        posts = fetcher.fetch_rss_feed()

    print(f"Fetched {len(posts)} posts")

    if posts:
        # Save posts
        cache_path = Path(args.output) if args.output else Path("posts.json")
        fetcher.save_posts(posts, cache_path)
        print(f"Saved posts to {cache_path}")

        # Build and save index
        print("Building index...")
        indexer = BlogIndexer(posts)
        index_path = cache_path.with_suffix(".index.json")
        indexer.save(index_path)
        print(f"Saved index to {index_path}")


def cmd_search(args):
    """Search the indexed blog."""
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Index not found: {index_path}")
        sys.exit(1)

    explorer = BlogExplorer.from_index(index_path)
    results = explorer.search(
        args.query,
        limit=args.limit,
        year=args.year,
        tag=args.tag
    )

    if not results:
        print("No results found.")
        return

    print(f"\nFound {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.post.title}")
        print(f"   Date: {result.post.date[:10] if result.post.date else 'Unknown'}")
        print(f"   URL: {result.post.url}")
        print(f"   Score: {result.score:.2f}")
        if result.snippet:
            print(f"   ...{result.snippet[:200]}...")
        print()


def cmd_similar(args):
    """Find posts similar to a given post."""
    index_path = Path(args.index)
    explorer = BlogExplorer.from_index(index_path)

    # First search to find the post
    results = explorer.search(args.query, limit=1)
    if not results:
        print(f"No post found matching: {args.query}")
        return

    source = results[0].post
    print(f"\nFinding posts similar to: {source.title}\n")

    similar = explorer.indexer.find_similar(source.id, limit=args.limit)
    for i, result in enumerate(similar, 1):
        print(f"{i}. {result.post.title}")
        print(f"   Date: {result.post.date[:10] if result.post.date else 'Unknown'}")
        print(f"   Similarity: {result.score:.2f}")
        print(f"   Shared concepts: {', '.join(result.matched_terms[:5])}")
        print()


def cmd_random(args):
    """Surface a random post for rediscovery."""
    index_path = Path(args.index)
    explorer = BlogExplorer.from_index(index_path)

    post = explorer.random_rediscovery(year=args.year)

    print("\n" + "=" * 60)
    print("RANDOM REDISCOVERY")
    print("=" * 60)
    print(f"\nTitle: {post.title}")
    print(f"Date: {post.date[:10] if post.date else 'Unknown'}")
    print(f"URL: {post.url}")
    if post.tags:
        print(f"Tags: {', '.join(post.tags[:5])}")
    print(f"\n{post.excerpt[:500]}...")
    print()


def cmd_trace(args):
    """Trace a concept through the archive."""
    index_path = Path(args.index)
    explorer = BlogExplorer.from_index(index_path)

    print(f"\nTracing '{args.concept}' through the archive:\n")

    by_year = explorer.trace_concept(args.concept)
    for year, results in by_year.items():
        print(f"\n{year} ({len(results)} posts):")
        for result in results[:3]:
            print(f"  - {result.post.title}")


def cmd_summary(args):
    """Show archive summary."""
    index_path = Path(args.index)
    explorer = BlogExplorer.from_index(index_path)

    print(explorer.summary())


def cmd_prompt(args):
    """Generate a writing prompt."""
    index_path = Path(args.index)
    explorer = BlogExplorer.from_index(index_path)

    prompt = explorer.generate_prompt(style=args.style)
    print("\n" + "=" * 60)
    print("WRITING PROMPT")
    print("=" * 60)
    print(f"\n{prompt}\n")


def cmd_themes(args):
    """Show themes by year."""
    index_path = Path(args.index)
    explorer = BlogExplorer.from_index(index_path)

    themes = explorer.indexer.get_temporal_themes()

    print("\nDistinctive themes by year:\n")
    for year, year_themes in sorted(themes.items()):
        theme_list = [t for t, _ in year_themes[:8]]
        print(f"{year}: {', '.join(theme_list)}")


def main():
    parser = argparse.ArgumentParser(
        description="Explore your blog archive",
        epilog="A tool for intellectual craft, inspired by C. Wright Mills"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch and index a blog")
    fetch_parser.add_argument("url", help="Blog URL (e.g., https://markcarrigan.net)")
    fetch_parser.add_argument("-o", "--output", help="Output file path")
    fetch_parser.add_argument(
        "-m", "--method",
        choices=["api", "rss"],
        default="api",
        help="Fetch method (default: api)"
    )
    fetch_parser.add_argument(
        "--max-pages",
        type=int,
        default=100,
        help="Maximum pages to fetch via API"
    )
    fetch_parser.set_defaults(func=cmd_fetch)

    # Search command
    search_parser = subparsers.add_parser("search", help="Search the archive")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "-i", "--index",
        default="posts.index.json",
        help="Index file path"
    )
    search_parser.add_argument("-l", "--limit", type=int, default=10)
    search_parser.add_argument("-y", "--year", help="Filter by year")
    search_parser.add_argument("-t", "--tag", help="Filter by tag")
    search_parser.set_defaults(func=cmd_search)

    # Similar command
    similar_parser = subparsers.add_parser("similar", help="Find similar posts")
    similar_parser.add_argument("query", help="Post to find similar posts for")
    similar_parser.add_argument("-i", "--index", default="posts.index.json")
    similar_parser.add_argument("-l", "--limit", type=int, default=10)
    similar_parser.set_defaults(func=cmd_similar)

    # Random command
    random_parser = subparsers.add_parser("random", help="Random post for rediscovery")
    random_parser.add_argument("-i", "--index", default="posts.index.json")
    random_parser.add_argument("-y", "--year", help="Limit to specific year")
    random_parser.set_defaults(func=cmd_random)

    # Trace command
    trace_parser = subparsers.add_parser("trace", help="Trace a concept through time")
    trace_parser.add_argument("concept", help="Concept to trace")
    trace_parser.add_argument("-i", "--index", default="posts.index.json")
    trace_parser.set_defaults(func=cmd_trace)

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Archive summary")
    summary_parser.add_argument("-i", "--index", default="posts.index.json")
    summary_parser.set_defaults(func=cmd_summary)

    # Prompt command
    prompt_parser = subparsers.add_parser("prompt", help="Generate writing prompt")
    prompt_parser.add_argument("-i", "--index", default="posts.index.json")
    prompt_parser.add_argument(
        "-s", "--style",
        choices=["connection", "revisit", "gap"],
        default="connection"
    )
    prompt_parser.set_defaults(func=cmd_prompt)

    # Themes command
    themes_parser = subparsers.add_parser("themes", help="Show themes by year")
    themes_parser.add_argument("-i", "--index", default="posts.index.json")
    themes_parser.set_defaults(func=cmd_themes)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
