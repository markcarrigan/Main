"""
Blog Explorer - The main interface for exploring blog archives.

Provides high-level methods for discovering connections, tracing themes,
and supporting the kind of intellectual craft C. Wright Mills advocated.
"""

import random
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .fetcher import BlogFetcher, BlogPost
from .indexer import BlogIndexer, SearchResult, strip_html


@dataclass
class Connection:
    """Represents a discovered connection between posts."""
    source: BlogPost
    target: BlogPost
    connection_type: str  # "similar", "shared_tag", "temporal_echo", etc.
    strength: float
    explanation: str


class BlogExplorer:
    """
    High-level interface for exploring a blog archive.

    Designed to support serendipitous discovery and intellectual
    connection-making across years of writing.
    """

    def __init__(self, indexer: BlogIndexer):
        self.indexer = indexer

    @classmethod
    def from_blog(
        cls,
        blog_url: str,
        cache_path: Optional[Path] = None,
        use_api: bool = True
    ) -> "BlogExplorer":
        """
        Create an explorer by fetching and indexing a blog.

        This may take a while for large archives.
        """
        fetcher = BlogFetcher(blog_url)

        if cache_path and cache_path.exists():
            posts = fetcher.load_posts(cache_path)
        elif use_api:
            posts = list(fetcher.fetch_via_wp_api())
            if cache_path:
                fetcher.save_posts(posts, cache_path)
        else:
            posts = fetcher.fetch_rss_feed()

        indexer = BlogIndexer(posts)
        return cls(indexer)

    @classmethod
    def from_index(cls, index_path: Path) -> "BlogExplorer":
        """Load an explorer from a saved index."""
        indexer = BlogIndexer.load(index_path)
        return cls(indexer)

    def search(self, query: str, **kwargs) -> list[SearchResult]:
        """Search the archive."""
        return self.indexer.search(query, **kwargs)

    def random_rediscovery(self, year: Optional[str] = None) -> BlogPost:
        """
        Return a random post for rediscovery.

        The blog archive is a form of external memory. Random sampling
        can surface forgotten ideas worth revisiting.
        """
        if year:
            candidates = self.indexer.posts_by_year.get(year, [])
            if candidates:
                post_id = random.choice(candidates)
                return self.indexer.post_by_id[post_id]

        return random.choice(self.indexer.posts)

    def temporal_echo(self, post: BlogPost, years_back: int = 5) -> list[SearchResult]:
        """
        Find similar posts from a specific number of years ago.

        This supports a Mills-style "conversation with your past self"
        by surfacing how you engaged with similar themes previously.
        """
        try:
            post_year = int(post.date[:4])
            target_year = str(post_year - years_back)
        except (ValueError, TypeError):
            return []

        # Get similar posts
        similar = self.indexer.find_similar(post.id, limit=50)

        # Filter to target year
        echoes = [r for r in similar
                  if r.post.date and r.post.date.startswith(target_year)]

        return echoes[:10]

    def trace_concept(self, concept: str) -> dict[str, list[SearchResult]]:
        """
        Trace how a concept has been used across years.

        Returns a year-by-year breakdown of posts engaging with the concept.
        """
        results = self.indexer.search(concept, limit=200)

        by_year: dict[str, list[SearchResult]] = {}
        for result in results:
            if result.post.date:
                year = result.post.date[:4]
                if year not in by_year:
                    by_year[year] = []
                by_year[year].append(result)

        return dict(sorted(by_year.items()))

    def find_bridges(self, tag1: str, tag2: str) -> list[BlogPost]:
        """
        Find posts that connect two different tags/themes.

        Useful for discovering how different areas of interest relate.
        """
        posts1 = set(self.indexer.posts_by_tag.get(tag1.lower(), []))
        posts2 = set(self.indexer.posts_by_tag.get(tag2.lower(), []))

        # Posts with both tags
        bridges = posts1 & posts2

        return [self.indexer.post_by_id[pid] for pid in bridges]

    def orphan_ideas(self, min_similarity_threshold: float = 0.1) -> list[BlogPost]:
        """
        Find posts that don't strongly connect to others.

        These might be underdeveloped ideas worth revisiting,
        or unique explorations that deserve further attention.
        """
        orphans = []

        for post in self.indexer.posts:
            similar = self.indexer.find_similar(post.id, limit=5)
            if not similar or similar[0].score < min_similarity_threshold:
                orphans.append(post)

        return orphans

    def idea_clusters(self, num_clusters: int = 10) -> list[list[BlogPost]]:
        """
        Identify clusters of related posts.

        Uses simple greedy clustering based on similarity.
        """
        # Start with unclustered posts
        unclustered = set(p.id for p in self.indexer.posts)
        clusters = []

        while unclustered and len(clusters) < num_clusters:
            # Pick a random seed
            seed_id = random.choice(list(unclustered))
            unclustered.remove(seed_id)

            cluster = [self.indexer.post_by_id[seed_id]]

            # Find similar posts that haven't been clustered
            similar = self.indexer.find_similar(seed_id, limit=50)
            for result in similar:
                if result.post.id in unclustered and result.score > 0.2:
                    cluster.append(result.post)
                    unclustered.remove(result.post.id)
                    if len(cluster) >= 20:  # Cap cluster size
                        break

            if len(cluster) >= 3:  # Only keep clusters of reasonable size
                clusters.append(cluster)

        return clusters

    def intellectual_trajectory(self) -> dict:
        """
        Analyze the intellectual trajectory of the blog over time.

        Returns insights about thematic evolution, productivity patterns, etc.
        """
        themes = self.indexer.get_temporal_themes()
        posts_per_year = {
            year: len(posts)
            for year, posts in self.indexer.posts_by_year.items()
        }

        # Find consistent vs. emerging themes
        all_themes = set()
        theme_years: dict[str, list[str]] = {}

        for year, year_themes in themes.items():
            for theme, _ in year_themes:
                all_themes.add(theme)
                if theme not in theme_years:
                    theme_years[theme] = []
                theme_years[theme].append(year)

        consistent_themes = [
            t for t, years in theme_years.items()
            if len(years) >= len(themes) * 0.5
        ]

        recent_years = sorted(self.indexer.posts_by_year.keys())[-3:]
        emerging_themes = [
            t for t, years in theme_years.items()
            if all(y in recent_years for y in years) and len(years) >= 2
        ]

        return {
            "posts_per_year": posts_per_year,
            "themes_per_year": themes,
            "consistent_themes": consistent_themes,
            "emerging_themes": emerging_themes,
            "total_posts": len(self.indexer.posts),
            "year_range": (
                min(self.indexer.posts_by_year.keys()) if self.indexer.posts_by_year else None,
                max(self.indexer.posts_by_year.keys()) if self.indexer.posts_by_year else None
            )
        }

    def fringe_thoughts(self, recent_days: int = 30) -> list[tuple[BlogPost, list[SearchResult]]]:
        """
        Surface recent posts with connections to older material.

        Inspired by Mills' advice to capture fringe-thoughts by connecting
        new ideas to established patterns of thinking.
        """
        # Find recent posts
        recent = []
        cutoff = datetime.now().year

        for post in self.indexer.posts:
            if post.date and post.date[:4] == str(cutoff):
                recent.append(post)

        # For each recent post, find older connections
        results = []
        for post in recent[:20]:  # Limit to avoid overwhelming
            similar = self.indexer.find_similar(post.id, limit=5)
            # Filter to posts at least 2 years old
            old_similar = [
                r for r in similar
                if r.post.date and int(r.post.date[:4]) < cutoff - 1
            ]
            if old_similar:
                results.append((post, old_similar))

        return results

    def generate_prompt(self, style: str = "connection") -> str:
        """
        Generate a writing prompt based on the archive.

        Different styles:
        - "connection": Prompt to connect two random posts
        - "revisit": Prompt to update an old post
        - "gap": Prompt to fill a gap between themes
        """
        if style == "connection":
            posts = random.sample(self.indexer.posts, 2)
            return (
                f"Consider the connection between:\n\n"
                f"1. \"{posts[0].title}\" ({posts[0].date[:4] if posts[0].date else 'undated'})\n"
                f"2. \"{posts[1].title}\" ({posts[1].date[:4] if posts[1].date else 'undated'})\n\n"
                f"What thread connects these two posts? What would you write differently now?"
            )

        elif style == "revisit":
            # Find a post from at least 5 years ago
            old_posts = [
                p for p in self.indexer.posts
                if p.date and int(p.date[:4]) < datetime.now().year - 5
            ]
            if old_posts:
                post = random.choice(old_posts)
                return (
                    f"Revisit: \"{post.title}\" ({post.date[:4] if post.date else 'undated'})\n\n"
                    f"How has your thinking on this topic evolved? "
                    f"What would you add, revise, or retract?"
                )

        elif style == "gap":
            # Find two tags that haven't been combined
            tags = list(self.indexer.posts_by_tag.keys())
            if len(tags) >= 2:
                tag1, tag2 = random.sample(tags, 2)
                bridges = self.find_bridges(tag1, tag2)
                if not bridges:
                    return (
                        f"Gap: You've written about '{tag1}' and '{tag2}' separately.\n\n"
                        f"What would it look like to bring these themes together? "
                        f"What questions emerge at their intersection?"
                    )

        return "Explore your archive and write about what surprises you."

    def summary(self) -> str:
        """Generate a human-readable summary of the archive."""
        trajectory = self.intellectual_trajectory()

        lines = [
            f"Blog Archive Summary",
            f"=" * 40,
            f"",
            f"Total posts: {trajectory['total_posts']}",
            f"Date range: {trajectory['year_range'][0]} - {trajectory['year_range'][1]}",
            f"",
            f"Posts per year:",
        ]

        for year, count in sorted(trajectory['posts_per_year'].items()):
            bar = "*" * min(count // 10, 50)
            lines.append(f"  {year}: {count:4d} {bar}")

        lines.extend([
            "",
            f"Consistent themes: {', '.join(trajectory['consistent_themes'][:10])}",
            "",
            f"Emerging themes: {', '.join(trajectory['emerging_themes'][:10])}",
        ])

        return "\n".join(lines)
