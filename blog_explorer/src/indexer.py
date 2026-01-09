"""
Blog Indexer - Creates searchable indices of blog archives.

Provides full-text search, tag/category indexing, and basic similarity detection
for finding related posts across years of writing.
"""

import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional
from html import unescape

from .fetcher import BlogPost


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = unescape(clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def tokenize(text: str) -> list[str]:
    """Simple tokenization for search indexing."""
    text = text.lower()
    # Keep alphanumeric and common punctuation that might be meaningful
    tokens = re.findall(r"\b[a-z][a-z0-9\-\']*[a-z0-9]\b|\b[a-z]\b", text)
    return tokens


# Common English stopwords to filter from analysis
STOPWORDS = set([
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "was", "are", "were", "been", "be", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "must", "shall", "can", "this", "that", "these", "those", "it", "its",
    "i", "you", "he", "she", "we", "they", "my", "your", "his", "her", "our",
    "their", "what", "which", "who", "whom", "when", "where", "why", "how", "all",
    "each", "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "about", "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once", "here", "there",
    "also", "being", "because", "if", "while", "up", "out", "any", "one", "two"
])


@dataclass
class SearchResult:
    """A search result with relevance score."""
    post: BlogPost
    score: float
    matched_terms: list[str] = field(default_factory=list)
    snippet: str = ""


class BlogIndexer:
    """
    Creates and queries a searchable index of blog posts.

    Uses TF-IDF for relevance ranking and provides various ways to
    explore the archive: by search, by theme, by time period, etc.
    """

    def __init__(self, posts: Optional[list[BlogPost]] = None):
        self.posts: list[BlogPost] = []
        self.post_by_id: dict[str, BlogPost] = {}

        # Inverted index: term -> [(post_id, term_frequency), ...]
        self.inverted_index: dict[str, list[tuple[str, int]]] = defaultdict(list)

        # Document frequency for IDF calculation
        self.doc_freq: Counter = Counter()

        # Tag and category indices
        self.posts_by_tag: dict[str, list[str]] = defaultdict(list)
        self.posts_by_category: dict[str, list[str]] = defaultdict(list)
        self.posts_by_year: dict[str, list[str]] = defaultdict(list)

        # Per-document term frequencies (for similarity)
        self.doc_vectors: dict[str, Counter] = {}

        if posts:
            self.add_posts(posts)

    def add_posts(self, posts: list[BlogPost]):
        """Add posts to the index."""
        for post in posts:
            self.add_post(post)

    def add_post(self, post: BlogPost):
        """Add a single post to all indices."""
        if post.id in self.post_by_id:
            return  # Already indexed

        self.posts.append(post)
        self.post_by_id[post.id] = post

        # Process text content
        full_text = f"{post.title} {strip_html(post.content)}"
        tokens = tokenize(full_text)
        term_freq = Counter(tokens)

        # Store document vector
        self.doc_vectors[post.id] = term_freq

        # Update inverted index and document frequencies
        for term, freq in term_freq.items():
            self.inverted_index[term].append((post.id, freq))

        self.doc_freq.update(term_freq.keys())

        # Index by tags and categories
        for tag in post.tags:
            self.posts_by_tag[tag.lower()].append(post.id)

        for cat in post.categories:
            self.posts_by_category[cat.lower()].append(post.id)

        # Index by year
        if post.date:
            year = post.date[:4]
            if year.isdigit():
                self.posts_by_year[year].append(post.id)

    def _compute_tfidf(self, term: str, doc_id: str) -> float:
        """Compute TF-IDF score for a term in a document."""
        if doc_id not in self.doc_vectors:
            return 0.0

        tf = self.doc_vectors[doc_id].get(term, 0)
        if tf == 0:
            return 0.0

        # Log-normalized TF
        tf_score = 1 + math.log(tf)

        # IDF with smoothing
        df = self.doc_freq.get(term, 0)
        if df == 0:
            return 0.0
        idf_score = math.log(len(self.posts) / df)

        return tf_score * idf_score

    def search(
        self,
        query: str,
        limit: int = 20,
        year: Optional[str] = None,
        tag: Optional[str] = None,
        category: Optional[str] = None
    ) -> list[SearchResult]:
        """
        Search for posts matching the query.

        Uses TF-IDF ranking with optional filtering by year, tag, or category.
        """
        query_tokens = [t for t in tokenize(query) if t not in STOPWORDS]
        if not query_tokens:
            return []

        # Score all documents
        scores: dict[str, float] = defaultdict(float)
        matched_terms: dict[str, list[str]] = defaultdict(list)

        for term in query_tokens:
            if term not in self.inverted_index:
                continue

            for doc_id, _ in self.inverted_index[term]:
                score = self._compute_tfidf(term, doc_id)
                scores[doc_id] += score
                if score > 0:
                    matched_terms[doc_id].append(term)

        # Apply filters
        candidate_ids = set(scores.keys())

        if year:
            year_posts = set(self.posts_by_year.get(year, []))
            candidate_ids &= year_posts

        if tag:
            tag_posts = set(self.posts_by_tag.get(tag.lower(), []))
            candidate_ids &= tag_posts

        if category:
            cat_posts = set(self.posts_by_category.get(category.lower(), []))
            candidate_ids &= cat_posts

        # Build results
        results = []
        for doc_id in candidate_ids:
            post = self.post_by_id[doc_id]
            score = scores[doc_id]

            # Generate snippet
            content = strip_html(post.content)
            snippet = self._extract_snippet(content, query_tokens)

            results.append(SearchResult(
                post=post,
                score=score,
                matched_terms=matched_terms[doc_id],
                snippet=snippet
            ))

        # Sort by score and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _extract_snippet(self, content: str, query_tokens: list[str], window: int = 100) -> str:
        """Extract a relevant snippet containing query terms."""
        content_lower = content.lower()

        # Find first occurrence of any query term
        best_pos = len(content)
        for term in query_tokens:
            pos = content_lower.find(term)
            if pos != -1 and pos < best_pos:
                best_pos = pos

        if best_pos == len(content):
            # No match found, return start of content
            return content[:window * 2] + "..."

        # Extract window around the match
        start = max(0, best_pos - window)
        end = min(len(content), best_pos + window)

        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def find_similar(self, post_id: str, limit: int = 10) -> list[SearchResult]:
        """
        Find posts similar to the given post using cosine similarity.

        This is useful for discovering thematic connections across time.
        """
        if post_id not in self.doc_vectors:
            return []

        source_vector = self.doc_vectors[post_id]
        source_magnitude = math.sqrt(sum(v ** 2 for v in source_vector.values()))

        if source_magnitude == 0:
            return []

        similarities = []
        for other_id, other_vector in self.doc_vectors.items():
            if other_id == post_id:
                continue

            # Compute cosine similarity
            dot_product = sum(
                source_vector.get(term, 0) * freq
                for term, freq in other_vector.items()
            )
            other_magnitude = math.sqrt(sum(v ** 2 for v in other_vector.values()))

            if other_magnitude == 0:
                continue

            similarity = dot_product / (source_magnitude * other_magnitude)

            # Find shared significant terms
            shared_terms = []
            for term in source_vector:
                if term in other_vector and term not in STOPWORDS:
                    shared_terms.append(term)

            similarities.append((other_id, similarity, shared_terms[:10]))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Build results
        results = []
        for doc_id, score, terms in similarities[:limit]:
            post = self.post_by_id[doc_id]
            results.append(SearchResult(
                post=post,
                score=score,
                matched_terms=terms,
                snippet=strip_html(post.excerpt or post.content[:300])
            ))

        return results

    def get_key_concepts(self, min_doc_freq: int = 5, limit: int = 100) -> list[tuple[str, float]]:
        """
        Extract key concepts from the corpus using TF-IDF.

        Returns terms that are distinctive to the blog's content.
        """
        # Calculate average TF-IDF across all documents for each term
        term_scores: dict[str, float] = defaultdict(float)
        term_counts: dict[str, int] = defaultdict(int)

        for term, postings in self.inverted_index.items():
            if term in STOPWORDS:
                continue
            if len(term) < 3:
                continue
            if self.doc_freq[term] < min_doc_freq:
                continue

            for doc_id, _ in postings:
                score = self._compute_tfidf(term, doc_id)
                term_scores[term] += score
                term_counts[term] += 1

        # Normalize by document count
        for term in term_scores:
            term_scores[term] /= term_counts[term]

        # Sort by score
        sorted_terms = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_terms[:limit]

    def get_temporal_themes(self) -> dict[str, list[tuple[str, float]]]:
        """
        Identify distinctive themes for each year.

        Useful for tracking intellectual evolution over time.
        """
        themes = {}

        for year, post_ids in sorted(self.posts_by_year.items()):
            if len(post_ids) < 3:
                continue

            # Build year-specific term frequencies
            year_terms: Counter = Counter()
            for post_id in post_ids:
                if post_id in self.doc_vectors:
                    year_terms.update(self.doc_vectors[post_id])

            # Score terms by their distinctiveness to this year
            term_scores = []
            for term, year_freq in year_terms.most_common(500):
                if term in STOPWORDS or len(term) < 3:
                    continue

                # Compare to corpus-wide frequency
                total_freq = self.doc_freq.get(term, 0)
                if total_freq == 0:
                    continue

                # Calculate over-representation in this year
                year_ratio = year_freq / len(post_ids)
                corpus_ratio = total_freq / len(self.posts)

                if corpus_ratio > 0:
                    distinctiveness = year_ratio / corpus_ratio
                    if distinctiveness > 1.5:  # At least 50% more common
                        term_scores.append((term, distinctiveness))

            term_scores.sort(key=lambda x: x[1], reverse=True)
            themes[year] = term_scores[:20]

        return themes

    def save(self, filepath: Path):
        """Save the index to disk."""
        data = {
            "posts": [p.to_dict() for p in self.posts],
            "inverted_index": dict(self.inverted_index),
            "doc_freq": dict(self.doc_freq),
            "posts_by_tag": dict(self.posts_by_tag),
            "posts_by_category": dict(self.posts_by_category),
            "posts_by_year": dict(self.posts_by_year),
            "doc_vectors": {k: dict(v) for k, v in self.doc_vectors.items()}
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, filepath: Path) -> "BlogIndexer":
        """Load an index from disk."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        indexer = cls()
        indexer.posts = [BlogPost.from_dict(p) for p in data["posts"]]
        indexer.post_by_id = {p.id: p for p in indexer.posts}
        indexer.inverted_index = defaultdict(list, {
            k: [tuple(x) for x in v] for k, v in data["inverted_index"].items()
        })
        indexer.doc_freq = Counter(data["doc_freq"])
        indexer.posts_by_tag = defaultdict(list, data["posts_by_tag"])
        indexer.posts_by_category = defaultdict(list, data["posts_by_category"])
        indexer.posts_by_year = defaultdict(list, data["posts_by_year"])
        indexer.doc_vectors = {k: Counter(v) for k, v in data["doc_vectors"].items()}

        return indexer
