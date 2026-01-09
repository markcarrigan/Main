#!/usr/bin/env python3
"""Run the blog explorer demo with expanded dataset."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "blog_explorer"))

from src.fetcher import BlogPost
from src.indexer import BlogIndexer
from src.explorer import BlogExplorer

data_dir = Path(__file__).parent.parent / "data"

# Load expanded posts
with open(data_dir / "expanded_posts.json") as f:
    posts_data = json.load(f)

posts = [BlogPost.from_dict(p) for p in posts_data]
print(f"Loaded {len(posts)} posts from markcarrigan.net\n")

# Build index
indexer = BlogIndexer(posts)
indexer.save(data_dir / "expanded_posts.index.json")

explorer = BlogExplorer(indexer)

print("=" * 70)
print("BLOG ARCHIVE SUMMARY")
print("=" * 70)
print(explorer.summary())

print("\n" + "=" * 70)
print("SEARCH: 'platform capitalism surveillance'")
print("=" * 70)
for i, r in enumerate(explorer.search("platform capitalism surveillance", limit=5), 1):
    print(f"{i}. {r.post.title} ({r.post.date})")
    print(f"   Score: {r.score:.2f}")

print("\n" + "=" * 70)
print("SEARCH: 'margaret archer reflexivity'")
print("=" * 70)
for i, r in enumerate(explorer.search("margaret archer reflexivity", limit=5), 1):
    print(f"{i}. {r.post.title} ({r.post.date})")
    print(f"   Score: {r.score:.2f}")

print("\n" + "=" * 70)
print("SEARCH: 'accelerated academy'")
print("=" * 70)
for i, r in enumerate(explorer.search("accelerated academy", limit=5), 1):
    print(f"{i}. {r.post.title} ({r.post.date})")
    print(f"   Score: {r.score:.2f}")

print("\n" + "=" * 70)
print("TRACING CONCEPT: 'generative AI' THROUGH THE YEARS")
print("=" * 70)
by_year = explorer.trace_concept("generative AI")
for year, results in sorted(by_year.items()):
    print(f"\n{year}:")
    for r in results[:3]:
        print(f"  - {r.post.title}")

print("\n" + "=" * 70)
print("KEY CONCEPTS IN THE ARCHIVE")
print("=" * 70)
for concept, score in indexer.get_key_concepts(min_doc_freq=3, limit=25):
    print(f"  {concept}: {score:.2f}")

print("\n" + "=" * 70)
print("FINDING SIMILAR POSTS TO: 'The problem of generative AI from a cybernetics perspective'")
print("=" * 70)
source = next((p for p in posts if "cybernetics" in p.title.lower()), posts[0])
for i, r in enumerate(indexer.find_similar(source.id, limit=5), 1):
    print(f"{i}. {r.post.title}")
    print(f"   Similarity: {r.score:.2f}")
    print(f"   Shared: {', '.join(r.matched_terms[:5])}")

print("\n" + "=" * 70)
print("RANDOM REDISCOVERY")
print("=" * 70)
post = explorer.random_rediscovery()
print(f"Title: {post.title}")
print(f"Date: {post.date}")
print(f"URL: {post.url}")

print("\n" + "=" * 70)
print("WRITING PROMPT")
print("=" * 70)
print(explorer.generate_prompt(style="connection"))

print("\n" + "=" * 70)
print("INTELLECTUAL TRAJECTORY")
print("=" * 70)
trajectory = explorer.intellectual_trajectory()
print(f"Total posts: {trajectory['total_posts']}")
print(f"Year range: {trajectory['year_range'][0]} - {trajectory['year_range'][1]}")
print(f"\nConsistent themes: {', '.join(trajectory['consistent_themes'][:10])}")
print(f"Emerging themes: {', '.join(trajectory['emerging_themes'][:10])}")

print("\n" + "=" * 70)
print("Demo complete!")
print("=" * 70)
