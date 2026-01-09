#!/usr/bin/env python3
"""
Google Scholar Citation Mapping Demo

This script demonstrates the Google Scholar integration features,
including field analysis and author citation map generation.

Run with: python scripts/scholar_demo.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "blog_explorer"))

from src.scholar import get_fetcher, FieldAnalysis
from visualizations.author_map import (
    generate_author_bubble_data,
    generate_author_network_data,
    generate_html_bubble_chart,
    generate_html_bar_chart,
    generate_html_network_graph,
)


def main():
    print("=" * 70)
    print("GOOGLE SCHOLAR CITATION MAPPING DEMO")
    print("=" * 70)
    print()

    # Use mock fetcher for demo (doesn't require scholarly package)
    print("Using mock data for demonstration...")
    print("(Install 'scholarly' package to fetch real Google Scholar data)")
    print()

    fetcher = get_fetcher(use_mock=True)

    # Analyze a field
    print("Analyzing field: Digital Sociology")
    print("-" * 40)

    analysis = fetcher.analyze_field(
        query="digital sociology",
        field_name="Digital Sociology",
        max_publications=100,
        max_authors=20
    )

    print(f"Query: {analysis.query}")
    print(f"Publications analyzed: {analysis.total_publications_analyzed}")
    print(f"Authors found: {len(analysis.authors)}")
    print()

    # Display top authors
    print("Top 10 Most Cited Authors:")
    print("-" * 40)

    for i, author in enumerate(analysis.authors[:10], 1):
        print(f"{i:2}. {author.name}")
        print(f"    Affiliation: {author.affiliation}")
        print(f"    Citations: {author.citations:,}")
        print(f"    H-Index: {author.h_index}")
        if author.interests:
            print(f"    Interests: {', '.join(author.interests[:3])}")
        print()

    # Save analysis
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)

    analysis_path = output_dir / "digital_sociology_analysis.json"
    fetcher.save_analysis(analysis, analysis_path)

    # Generate visualizations
    print("=" * 70)
    print("GENERATING VISUALIZATIONS")
    print("=" * 70)
    print()

    # Bubble chart
    print("1. Generating bubble chart...")
    bubble_data = generate_author_bubble_data(analysis, max_authors=20)
    bubble_path = output_dir / "author_bubble_map.html"
    generate_html_bubble_chart(bubble_data, output_path=bubble_path)
    print(f"   Saved to: {bubble_path}")

    # Bar chart
    print("2. Generating bar chart...")
    bar_path = output_dir / "author_bar_chart.html"
    generate_html_bar_chart(bubble_data, output_path=bar_path)
    print(f"   Saved to: {bar_path}")

    # Network graph
    print("3. Generating network graph...")
    network_data = generate_author_network_data(analysis, max_authors=20)
    network_path = output_dir / "author_network.html"
    generate_html_network_graph(network_data, output_path=network_path)
    print(f"   Saved to: {network_path}")

    print()
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print()
    print("Generated files:")
    print(f"  - {analysis_path}")
    print(f"  - {bubble_path}")
    print(f"  - {bar_path}")
    print(f"  - {network_path}")
    print()
    print("Open the HTML files in a browser to view interactive visualizations.")
    print()
    print("To use real Google Scholar data:")
    print("  1. pip install scholarly")
    print("  2. blog-explorer scholar-analyze 'your query' -o output.json")
    print("  3. blog-explorer scholar-viz output.json -t bubble")


if __name__ == "__main__":
    main()
