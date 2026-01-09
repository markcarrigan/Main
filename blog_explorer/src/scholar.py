"""
Google Scholar Integration Module

Fetches citation data and author information from Google Scholar
to create maps of the most cited authors in particular fields.

Note: This module uses the `scholarly` library which scrapes Google Scholar.
For production use, consider using a paid API service like SerpAPI for reliability.
"""

import json
import time
import random
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Iterator
from collections import defaultdict

try:
    from scholarly import scholarly, ProxyGenerator
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False


@dataclass
class Publication:
    """Represents a scholarly publication."""
    title: str
    authors: list[str]
    year: Optional[int]
    citations: int
    venue: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Publication":
        return cls(**data)


@dataclass
class Author:
    """Represents a Google Scholar author profile."""
    name: str
    scholar_id: str = ""
    affiliation: str = ""
    interests: list[str] = field(default_factory=list)
    citations: int = 0
    h_index: int = 0
    i10_index: int = 0
    publications: list[Publication] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data['publications'] = [p.to_dict() for p in self.publications]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Author":
        pubs = [Publication.from_dict(p) for p in data.pop('publications', [])]
        return cls(**data, publications=pubs)


@dataclass
class FieldAnalysis:
    """Analysis of a research field."""
    field_name: str
    query: str
    authors: list[Author] = field(default_factory=list)
    total_publications_analyzed: int = 0
    fetch_date: str = ""

    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "query": self.query,
            "authors": [a.to_dict() for a in self.authors],
            "total_publications_analyzed": self.total_publications_analyzed,
            "fetch_date": self.fetch_date
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FieldAnalysis":
        authors = [Author.from_dict(a) for a in data.pop('authors', [])]
        return cls(**data, authors=authors)


class ScholarFetcher:
    """
    Fetches citation data from Google Scholar.

    Usage:
        fetcher = ScholarFetcher()
        analysis = fetcher.analyze_field("digital sociology", max_results=100)
        fetcher.save_analysis(analysis, Path("sociology_analysis.json"))
    """

    def __init__(self, use_proxy: bool = False, delay_range: tuple[float, float] = (2.0, 5.0)):
        """
        Initialize the Scholar fetcher.

        Args:
            use_proxy: Whether to use free proxies (helps avoid rate limiting)
            delay_range: Random delay range between requests (min, max) in seconds
        """
        if not SCHOLARLY_AVAILABLE:
            raise ImportError(
                "The 'scholarly' package is required for Google Scholar integration.\n"
                "Install it with: pip install scholarly"
            )

        self.delay_range = delay_range

        if use_proxy:
            pg = ProxyGenerator()
            pg.FreeProxies()
            scholarly.use_proxy(pg)

    def _delay(self):
        """Add a random delay to avoid rate limiting."""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

    def search_publications(
        self,
        query: str,
        max_results: int = 100,
        year_low: Optional[int] = None,
        year_high: Optional[int] = None
    ) -> Iterator[Publication]:
        """
        Search for publications matching a query.

        Args:
            query: Search query (e.g., "digital sociology")
            max_results: Maximum number of publications to fetch
            year_low: Filter to publications from this year onwards
            year_high: Filter to publications up to this year

        Yields:
            Publication objects
        """
        search_query = scholarly.search_pubs(query, year_low=year_low, year_high=year_high)

        for i, result in enumerate(search_query):
            if i >= max_results:
                break

            try:
                pub = Publication(
                    title=result.get('bib', {}).get('title', 'Unknown'),
                    authors=result.get('bib', {}).get('author', '').split(' and '),
                    year=result.get('bib', {}).get('pub_year'),
                    citations=result.get('num_citations', 0),
                    venue=result.get('bib', {}).get('venue', ''),
                    url=result.get('pub_url', result.get('eprint_url', ''))
                )
                yield pub
                self._delay()
            except Exception as e:
                print(f"Warning: Failed to parse publication: {e}")
                continue

    def search_author(self, name: str) -> Optional[Author]:
        """
        Search for an author by name and get their profile.

        Args:
            name: Author name to search for

        Returns:
            Author object if found, None otherwise
        """
        try:
            search_query = scholarly.search_author(name)
            result = next(search_query, None)

            if result is None:
                return None

            # Fill in detailed information
            author_data = scholarly.fill(result, sections=['basics', 'indices'])

            return Author(
                name=author_data.get('name', name),
                scholar_id=author_data.get('scholar_id', ''),
                affiliation=author_data.get('affiliation', ''),
                interests=author_data.get('interests', []),
                citations=author_data.get('citedby', 0),
                h_index=author_data.get('hindex', 0),
                i10_index=author_data.get('i10index', 0)
            )
        except Exception as e:
            print(f"Warning: Failed to fetch author {name}: {e}")
            return None

    def get_author_by_id(self, scholar_id: str, fill_publications: bool = False) -> Optional[Author]:
        """
        Get an author profile by their Google Scholar ID.

        Args:
            scholar_id: Google Scholar author ID
            fill_publications: Whether to also fetch publication list

        Returns:
            Author object if found
        """
        try:
            sections = ['basics', 'indices']
            if fill_publications:
                sections.append('publications')

            author_data = scholarly.search_author_id(scholar_id)
            author_data = scholarly.fill(author_data, sections=sections)

            publications = []
            if fill_publications and 'publications' in author_data:
                for pub in author_data['publications'][:20]:  # Limit to top 20
                    publications.append(Publication(
                        title=pub.get('bib', {}).get('title', ''),
                        authors=[author_data.get('name', '')],
                        year=pub.get('bib', {}).get('pub_year'),
                        citations=pub.get('num_citations', 0),
                        venue=pub.get('bib', {}).get('venue', '')
                    ))

            return Author(
                name=author_data.get('name', ''),
                scholar_id=scholar_id,
                affiliation=author_data.get('affiliation', ''),
                interests=author_data.get('interests', []),
                citations=author_data.get('citedby', 0),
                h_index=author_data.get('hindex', 0),
                i10_index=author_data.get('i10index', 0),
                publications=publications
            )
        except Exception as e:
            print(f"Warning: Failed to fetch author ID {scholar_id}: {e}")
            return None

    def analyze_field(
        self,
        query: str,
        field_name: Optional[str] = None,
        max_publications: int = 100,
        max_authors: int = 50,
        year_low: Optional[int] = None,
        year_high: Optional[int] = None,
        fetch_author_details: bool = True
    ) -> FieldAnalysis:
        """
        Analyze a research field by searching publications and aggregating author citations.

        This is the main method for producing citation maps of a field.

        Args:
            query: Search query defining the field (e.g., "digital sociology")
            field_name: Human-readable name for the field
            max_publications: Maximum publications to analyze
            max_authors: Maximum authors to include in results
            year_low: Filter publications from this year onwards
            year_high: Filter publications up to this year
            fetch_author_details: Whether to fetch detailed author profiles

        Returns:
            FieldAnalysis object with ranked authors
        """
        from datetime import datetime

        field_name = field_name or query.title()
        print(f"Analyzing field: {field_name}")
        print(f"Search query: {query}")
        print(f"Fetching up to {max_publications} publications...")

        # Track author citation contributions from these publications
        author_citations: dict[str, int] = defaultdict(int)
        author_publication_count: dict[str, int] = defaultdict(int)

        pub_count = 0
        for pub in self.search_publications(query, max_publications, year_low, year_high):
            pub_count += 1
            if pub_count % 10 == 0:
                print(f"  Processed {pub_count} publications...")

            # Distribute citations across authors
            for author_name in pub.authors:
                author_name = author_name.strip()
                if author_name and len(author_name) > 2:  # Skip empty/initials
                    author_citations[author_name] += pub.citations
                    author_publication_count[author_name] += 1

        print(f"Found {len(author_citations)} unique authors")

        # Sort authors by citations and take top N
        sorted_authors = sorted(
            author_citations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_authors]

        # Build author objects
        authors = []
        for i, (name, citations) in enumerate(sorted_authors):
            print(f"  Processing author {i+1}/{len(sorted_authors)}: {name}")

            if fetch_author_details:
                author = self.search_author(name)
                if author:
                    authors.append(author)
                    self._delay()
                else:
                    # Create basic author record
                    authors.append(Author(
                        name=name,
                        citations=citations
                    ))
            else:
                authors.append(Author(
                    name=name,
                    citations=citations
                ))

        return FieldAnalysis(
            field_name=field_name,
            query=query,
            authors=authors,
            total_publications_analyzed=pub_count,
            fetch_date=datetime.now().isoformat()
        )

    def save_analysis(self, analysis: FieldAnalysis, path: Path):
        """Save field analysis to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(analysis.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Saved analysis to {path}")

    @staticmethod
    def load_analysis(path: Path) -> FieldAnalysis:
        """Load field analysis from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return FieldAnalysis.from_dict(data)


class MockScholarFetcher:
    """
    Mock fetcher for testing without hitting Google Scholar.
    Uses sample data to demonstrate functionality.
    """

    def __init__(self, **kwargs):
        pass

    def analyze_field(
        self,
        query: str,
        field_name: Optional[str] = None,
        max_publications: int = 100,
        max_authors: int = 50,
        **kwargs
    ) -> FieldAnalysis:
        """Return mock data for demonstration."""
        from datetime import datetime

        # Sample data for demonstration
        sample_authors = [
            Author(
                name="Deborah Lupton",
                affiliation="UNSW Sydney",
                interests=["digital sociology", "digital health", "data practices"],
                citations=45000,
                h_index=78,
                i10_index=200
            ),
            Author(
                name="Nick Couldry",
                affiliation="London School of Economics",
                interests=["media theory", "digital culture", "data colonialism"],
                citations=52000,
                h_index=82,
                i10_index=180
            ),
            Author(
                name="danah boyd",
                affiliation="Microsoft Research",
                interests=["social media", "youth", "privacy", "technology"],
                citations=48000,
                h_index=65,
                i10_index=120
            ),
            Author(
                name="Noortje Marres",
                affiliation="University of Warwick",
                interests=["digital sociology", "issue mapping", "participation"],
                citations=12000,
                h_index=42,
                i10_index=80
            ),
            Author(
                name="David Beer",
                affiliation="University of York",
                interests=["digital culture", "algorithms", "metrics"],
                citations=15000,
                h_index=45,
                i10_index=90
            ),
            Author(
                name="Tarleton Gillespie",
                affiliation="Microsoft Research",
                interests=["platforms", "content moderation", "algorithms"],
                citations=18000,
                h_index=38,
                i10_index=65
            ),
            Author(
                name="Jose van Dijck",
                affiliation="Utrecht University",
                interests=["platform society", "media studies", "connectivity"],
                citations=32000,
                h_index=55,
                i10_index=110
            ),
            Author(
                name="Sherry Turkle",
                affiliation="MIT",
                interests=["technology and self", "digital devices", "conversation"],
                citations=55000,
                h_index=60,
                i10_index=95
            ),
        ]

        return FieldAnalysis(
            field_name=field_name or query.title(),
            query=query,
            authors=sample_authors[:max_authors],
            total_publications_analyzed=max_publications,
            fetch_date=datetime.now().isoformat()
        )

    def search_author(self, name: str) -> Optional[Author]:
        """Return mock author data."""
        return Author(
            name=name,
            affiliation="Sample University",
            citations=1000,
            h_index=20,
            i10_index=30
        )

    def save_analysis(self, analysis: FieldAnalysis, path: Path):
        """Save field analysis to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(analysis.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Saved analysis to {path}")

    @staticmethod
    def load_analysis(path: Path) -> FieldAnalysis:
        """Load field analysis from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return FieldAnalysis.from_dict(data)


def get_fetcher(use_mock: bool = False, **kwargs) -> ScholarFetcher | MockScholarFetcher:
    """
    Get an appropriate fetcher based on availability and settings.

    Args:
        use_mock: Force use of mock fetcher
        **kwargs: Arguments passed to fetcher constructor

    Returns:
        ScholarFetcher if scholarly is available, MockScholarFetcher otherwise
    """
    if use_mock or not SCHOLARLY_AVAILABLE:
        if not use_mock and not SCHOLARLY_AVAILABLE:
            print("Note: 'scholarly' not installed. Using mock data for demonstration.")
            print("Install with: pip install scholarly")
        return MockScholarFetcher(**kwargs)
    return ScholarFetcher(**kwargs)
