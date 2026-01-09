# Blog Explorer

A tool for exploring long-form personal blog archives, inspired by C. Wright Mills' essay "On Intellectual Craftsmanship."

## Philosophy

Mills argued that keeping a file or journal "encourages you to capture 'fringe-thoughts': various ideas which may be by-products of everyday life." A long-running blog serves a similar function—but as the archive grows, rediscovery becomes difficult.

This tool treats your blog archive as an intellectual resource to be explored, not just a chronological record. It surfaces connections across time, helps you rediscover forgotten ideas, and supports the kind of reflexive engagement with your own thinking that Mills advocated.

## Features

- **Full-text search** with TF-IDF ranking
- **Similarity detection** to find thematically related posts
- **Temporal tracing** to see how concepts evolve over years
- **Random rediscovery** to surface forgotten posts
- **Theme extraction** showing distinctive concepts by year
- **Writing prompts** generated from your archive
- **Orphan detection** finding isolated ideas worth developing

## Installation

```bash
pip install -e .
```

Or with optional development dependencies:

```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Fetch and index your blog

```bash
# Using WordPress REST API (recommended for full archives)
blog-explorer fetch https://markcarrigan.net -o markcarrigan.json

# Using RSS (faster, but limited to recent posts)
blog-explorer fetch https://markcarrigan.net -m rss -o markcarrigan.json
```

### 2. Explore your archive

```bash
# Search for posts
blog-explorer search "digital distraction" -i markcarrigan.index.json

# Find similar posts
blog-explorer similar "platform capitalism" -i markcarrigan.index.json

# Trace a concept through time
blog-explorer trace "reflexivity" -i markcarrigan.index.json

# Get a random post for rediscovery
blog-explorer random -i markcarrigan.index.json

# See archive summary
blog-explorer summary -i markcarrigan.index.json

# Show themes by year
blog-explorer themes -i markcarrigan.index.json

# Generate a writing prompt
blog-explorer prompt -s connection -i markcarrigan.index.json
```

## Python API

```python
from blog_explorer import BlogExplorer
from pathlib import Path

# Load from saved index
explorer = BlogExplorer.from_index(Path("markcarrigan.index.json"))

# Or fetch fresh (takes time for large blogs)
explorer = BlogExplorer.from_blog(
    "https://markcarrigan.net",
    cache_path=Path("posts.json")
)

# Search
results = explorer.search("accelerated academy", limit=10)
for r in results:
    print(f"{r.post.title} ({r.score:.2f})")

# Find similar posts
similar = explorer.indexer.find_similar(results[0].post.id)

# Trace concept through time
by_year = explorer.trace_concept("platform")

# Random rediscovery
post = explorer.random_rediscovery(year="2015")

# Generate prompts
prompt = explorer.generate_prompt(style="revisit")

# Get intellectual trajectory
trajectory = explorer.intellectual_trajectory()
print(f"Consistent themes: {trajectory['consistent_themes']}")
print(f"Emerging themes: {trajectory['emerging_themes']}")
```

## Use Cases

### Preparing talks or papers
Search for everything you've written on a topic, trace how your thinking has evolved, find older posts that provide foundation for current work.

### Intellectual audit
Use `themes` to see what you've focused on each year. Use `orphan_ideas` to find underdeveloped threads worth pursuing.

### Combating the acceleration trap
The `random` command resurfaces forgotten work, counteracting the pressure to always produce new content rather than developing existing ideas.

### Writing with your archive
The `prompt` command generates prompts based on your actual archive, encouraging dialogue between your current and past selves.

## Architecture

- `fetcher.py`: Retrieves posts via WordPress REST API or RSS feeds
- `indexer.py`: Builds searchable indices with TF-IDF ranking
- `explorer.py`: High-level exploration interface
- `cli.py`: Command-line interface

## Privacy

This tool operates entirely locally. Your posts are fetched once and stored on your machine. No data is sent to external services.

## Acknowledgments

- C. Wright Mills, "On Intellectual Craftsmanship" (appendix to *The Sociological Imagination*, 1959)
- The long tradition of bloggers who've maintained public thinking spaces

## License

MIT
