# Blog Archive Explorer
# A tool for exploring long-form personal blog archives
# Inspired by C. Wright Mills' "On Intellectual Craftsmanship"
#
# Now with Google Scholar integration for citation analysis

from .fetcher import BlogFetcher
from .indexer import BlogIndexer
from .explorer import BlogExplorer
from .scholar import (
    ScholarFetcher,
    MockScholarFetcher,
    Author,
    Publication,
    FieldAnalysis,
    get_fetcher,
)

__version__ = "0.2.0"
__all__ = [
    "BlogFetcher",
    "BlogIndexer",
    "BlogExplorer",
    "ScholarFetcher",
    "MockScholarFetcher",
    "Author",
    "Publication",
    "FieldAnalysis",
    "get_fetcher",
]
