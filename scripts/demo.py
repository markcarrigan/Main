#!/usr/bin/env python3
"""
Demo script to show blog explorer capabilities using sample data.
"""

import json
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / "blog_explorer"))

from src.fetcher import BlogPost
from src.indexer import BlogIndexer
from src.explorer import BlogExplorer


def main():
    # Load sample posts
    data_dir = Path(__file__).parent.parent / "data"
    sample_file = data_dir / "sample_posts.json"

    print("=" * 60)
    print("Blog Explorer Demo")
    print("=" * 60)
    print()

    with open(sample_file) as f:
        posts_data = json.load(f)

    posts = [BlogPost.from_dict(p) for p in posts_data]
    print(f"Loaded {len(posts)} sample posts from markcarrigan.net")
    print()

    # Build index
    print("Building index...")
    indexer = BlogIndexer(posts)

    # Save index
    index_path = data_dir / "sample_posts.index.json"
    indexer.save(index_path)
    print(f"Saved index to {index_path}")
    print()

    # Create explorer
    explorer = BlogExplorer(indexer)

    # Demo: Summary
    print("=" * 60)
    print("ARCHIVE SUMMARY")
    print("=" * 60)
    print(explorer.summary())
    print()

    # Demo: Search
    print("=" * 60)
    print("SEARCH: 'digital distraction'")
    print("=" * 60)
    results = explorer.search("digital distraction", limit=5)
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.post.title}")
        print(f"   Date: {r.post.date}")
        print(f"   Score: {r.score:.2f}")
        print()

    # Demo: Search for critical realism
    print("=" * 60)
    print("SEARCH: 'critical realism morphogenesis'")
    print("=" * 60)
    results = explorer.search("critical realism morphogenesis", limit=5)
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.post.title}")
        print(f"   Date: {r.post.date}")
        print(f"   Score: {r.score:.2f}")
        print()

    # Demo: Similar posts
    print("=" * 60)
    print("SIMILAR POSTS TO: 'The problem of generative AI...'")
    print("=" * 60)
    # Find the cybernetics post
    source_post = next((p for p in posts if "cybernetics" in p.title.lower()), posts[0])
    similar = indexer.find_similar(source_post.id, limit=5)
    for i, r in enumerate(similar, 1):
        print(f"{i}. {r.post.title}")
        print(f"   Similarity: {r.score:.2f}")
        print(f"   Shared concepts: {', '.join(r.matched_terms[:5])}")
        print()

    # Demo: Trace concept
    print("=" * 60)
    print("TRACING CONCEPT: 'reflexivity'")
    print("=" * 60)
    by_year = explorer.trace_concept("reflexivity")
    for year, year_results in sorted(by_year.items()):
        print(f"\n{year}:")
        for r in year_results[:2]:
            print(f"  - {r.post.title}")
    print()

    # Demo: Key concepts
    print("=" * 60)
    print("KEY CONCEPTS IN THE ARCHIVE")
    print("=" * 60)
    concepts = indexer.get_key_concepts(min_doc_freq=2, limit=20)
    for concept, score in concepts:
        print(f"  {concept}: {score:.2f}")
    print()

    # Demo: Random rediscovery
    print("=" * 60)
    print("RANDOM REDISCOVERY")
    print("=" * 60)
    post = explorer.random_rediscovery()
    print(f"Title: {post.title}")
    print(f"Date: {post.date}")
    print(f"URL: {post.url}")
    print()

    # Demo: Writing prompt
    print("=" * 60)
    print("WRITING PROMPT")
    print("=" * 60)
    prompt = explorer.generate_prompt(style="connection")
    print(prompt)
    print()

    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
