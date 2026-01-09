"""
Command-line interface for the Blog Explorer.

Provides interactive exploration of blog archives from the terminal,
plus Google Scholar citation analysis tools.
"""

import argparse
import sys
from pathlib import Path

from .fetcher import BlogFetcher
from .indexer import BlogIndexer
from .explorer import BlogExplorer
from .scholar import get_fetcher, FieldAnalysis


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


# Google Scholar commands

def cmd_scholar_analyze(args):
    """Analyze a research field using Google Scholar."""
    print(f"\n{'='*60}")
    print("GOOGLE SCHOLAR FIELD ANALYSIS")
    print(f"{'='*60}\n")

    fetcher = get_fetcher(use_mock=args.mock, use_proxy=args.proxy)

    analysis = fetcher.analyze_field(
        query=args.query,
        field_name=args.name,
        max_publications=args.max_pubs,
        max_authors=args.max_authors,
        year_low=args.year_from,
        year_high=args.year_to,
        fetch_author_details=not args.quick
    )

    # Save results
    output_path = Path(args.output)
    fetcher.save_analysis(analysis, output_path)

    # Print summary
    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Field: {analysis.field_name}")
    print(f"Query: {analysis.query}")
    print(f"Publications analyzed: {analysis.total_publications_analyzed}")
    print(f"Authors found: {len(analysis.authors)}")
    print(f"\nTop 10 most cited authors:\n")

    for i, author in enumerate(analysis.authors[:10], 1):
        print(f"  {i:2}. {author.name}")
        print(f"      Citations: {author.citations:,}  |  H-Index: {author.h_index}")
        if author.affiliation:
            print(f"      {author.affiliation}")
        print()

    print(f"\nResults saved to: {output_path}")


def cmd_scholar_visualize(args):
    """Generate visualization from field analysis."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from visualizations.author_map import (
        generate_author_bubble_data,
        generate_author_network_data,
        generate_html_bubble_chart,
        generate_html_bar_chart,
        generate_html_network_graph
    )

    print(f"Loading analysis from {args.analysis}...")
    analysis = FieldAnalysis.from_dict(
        __import__('json').load(open(args.analysis, 'r', encoding='utf-8'))
    )

    output_path = Path(args.output)

    if args.type == "bubble":
        data = generate_author_bubble_data(analysis, max_authors=args.max_authors)
        generate_html_bubble_chart(data, output_path=output_path)
    elif args.type == "bar":
        data = generate_author_bubble_data(analysis, max_authors=args.max_authors)
        generate_html_bar_chart(data, output_path=output_path)
    elif args.type == "network":
        data = generate_author_network_data(analysis, max_authors=args.max_authors)
        generate_html_network_graph(data, output_path=output_path)

    print(f"Visualization saved to {output_path}")


def cmd_scholar_author(args):
    """Look up a specific author on Google Scholar."""
    fetcher = get_fetcher(use_mock=args.mock, use_proxy=args.proxy)

    print(f"Searching for author: {args.name}...")
    author = fetcher.search_author(args.name)

    if not author:
        print(f"Author not found: {args.name}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"AUTHOR: {author.name}")
    print(f"{'='*60}")
    if author.affiliation:
        print(f"Affiliation: {author.affiliation}")
    if author.interests:
        print(f"Interests: {', '.join(author.interests)}")
    print()
    print(f"Total Citations: {author.citations:,}")
    print(f"H-Index: {author.h_index}")
    print(f"i10-Index: {author.i10_index}")

    if author.scholar_id:
        print(f"\nGoogle Scholar: https://scholar.google.com/citations?user={author.scholar_id}")


def cmd_scholar_top(args):
    """Quick view of top authors in a field."""
    fetcher = get_fetcher(use_mock=args.mock)

    print(f"Analyzing: {args.query}")
    print("This may take a few minutes...\n")

    analysis = fetcher.analyze_field(
        query=args.query,
        max_publications=args.limit,
        max_authors=20,
        fetch_author_details=False
    )

    print(f"\n{'='*60}")
    print(f"TOP AUTHORS: {args.query.upper()}")
    print(f"{'='*60}\n")

    for i, author in enumerate(analysis.authors[:20], 1):
        print(f"{i:2}. {author.name:<40} {author.citations:>10,} citations")


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

    # =========================================================================
    # Google Scholar commands
    # =========================================================================

    # Scholar analyze command
    scholar_analyze = subparsers.add_parser(
        "scholar-analyze",
        help="Analyze a research field using Google Scholar"
    )
    scholar_analyze.add_argument("query", help="Search query (e.g., 'digital sociology')")
    scholar_analyze.add_argument("-n", "--name", help="Field name for display")
    scholar_analyze.add_argument(
        "-o", "--output",
        default="field_analysis.json",
        help="Output file path"
    )
    scholar_analyze.add_argument(
        "--max-pubs",
        type=int,
        default=100,
        help="Max publications to analyze"
    )
    scholar_analyze.add_argument(
        "--max-authors",
        type=int,
        default=50,
        help="Max authors to include"
    )
    scholar_analyze.add_argument("--year-from", type=int, help="Filter from year")
    scholar_analyze.add_argument("--year-to", type=int, help="Filter to year")
    scholar_analyze.add_argument(
        "--quick",
        action="store_true",
        help="Skip fetching detailed author profiles"
    )
    scholar_analyze.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data (for testing)"
    )
    scholar_analyze.add_argument(
        "--proxy",
        action="store_true",
        help="Use proxy to avoid rate limits"
    )
    scholar_analyze.set_defaults(func=cmd_scholar_analyze)

    # Scholar visualize command
    scholar_viz = subparsers.add_parser(
        "scholar-viz",
        help="Generate author citation map visualization"
    )
    scholar_viz.add_argument("analysis", help="Path to field analysis JSON")
    scholar_viz.add_argument(
        "-o", "--output",
        default="author_map.html",
        help="Output HTML file"
    )
    scholar_viz.add_argument(
        "-t", "--type",
        choices=["bubble", "bar", "network"],
        default="bubble",
        help="Visualization type"
    )
    scholar_viz.add_argument(
        "--max-authors",
        type=int,
        default=50,
        help="Max authors to display"
    )
    scholar_viz.set_defaults(func=cmd_scholar_visualize)

    # Scholar author lookup command
    scholar_author = subparsers.add_parser(
        "scholar-author",
        help="Look up a specific author on Google Scholar"
    )
    scholar_author.add_argument("name", help="Author name to search")
    scholar_author.add_argument("--mock", action="store_true", help="Use mock data")
    scholar_author.add_argument("--proxy", action="store_true", help="Use proxy")
    scholar_author.set_defaults(func=cmd_scholar_author)

    # Scholar top command (quick analysis)
    scholar_top = subparsers.add_parser(
        "scholar-top",
        help="Quick list of top cited authors in a field"
    )
    scholar_top.add_argument("query", help="Search query")
    scholar_top.add_argument(
        "-l", "--limit",
        type=int,
        default=50,
        help="Publications to analyze"
    )
    scholar_top.add_argument("--mock", action="store_true", help="Use mock data")
    scholar_top.set_defaults(func=cmd_scholar_top)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
