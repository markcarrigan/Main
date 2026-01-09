"""
Concept Map Generator

Creates interactive HTML visualizations of concept relationships
across a blog archive. Uses D3.js for force-directed graph layout.
"""

import json
import math
from pathlib import Path
from collections import defaultdict
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexer import BlogIndexer, STOPWORDS


def generate_concept_graph(
    indexer: BlogIndexer,
    min_cooccurrence: int = 5,
    max_concepts: int = 100
) -> dict:
    """
    Generate a graph of concept co-occurrences.

    Nodes are concepts, edges represent how often concepts appear together.
    """
    # Get top concepts
    key_concepts = indexer.get_key_concepts(min_doc_freq=10, limit=max_concepts * 2)
    concept_set = set(c for c, _ in key_concepts[:max_concepts])

    # Build co-occurrence matrix
    cooccurrence: dict[tuple[str, str], int] = defaultdict(int)

    for doc_id, doc_vector in indexer.doc_vectors.items():
        doc_concepts = [c for c in doc_vector if c in concept_set]

        # Count pairs
        for i, c1 in enumerate(doc_concepts):
            for c2 in doc_concepts[i + 1:]:
                pair = tuple(sorted([c1, c2]))
                cooccurrence[pair] += 1

    # Build nodes
    nodes = []
    concept_docs = defaultdict(int)
    for concept in concept_set:
        count = indexer.doc_freq.get(concept, 0)
        concept_docs[concept] = count
        nodes.append({
            "id": concept,
            "label": concept,
            "size": math.log(count + 1) * 5,
            "doc_count": count
        })

    # Build edges
    edges = []
    for (c1, c2), weight in cooccurrence.items():
        if weight >= min_cooccurrence:
            edges.append({
                "source": c1,
                "target": c2,
                "weight": weight
            })

    return {"nodes": nodes, "edges": edges}


def generate_temporal_flow(indexer: BlogIndexer) -> dict:
    """
    Generate a temporal flow visualization showing how themes
    emerge and persist over time.
    """
    themes = indexer.get_temporal_themes()

    years = sorted(themes.keys())
    all_themes = set()
    for year_themes in themes.values():
        for theme, _ in year_themes[:15]:
            all_themes.add(theme)

    # Build flow data
    nodes = []
    links = []

    theme_indices = {t: i for i, t in enumerate(sorted(all_themes))}

    for yi, year in enumerate(years):
        year_themes = themes.get(year, [])
        theme_dict = {t: s for t, s in year_themes}

        for theme in all_themes:
            if theme in theme_dict:
                nodes.append({
                    "id": f"{year}_{theme}",
                    "year": year,
                    "theme": theme,
                    "strength": theme_dict[theme]
                })

                # Link to next year if theme continues
                if yi < len(years) - 1:
                    next_year = years[yi + 1]
                    next_themes = dict(themes.get(next_year, []))
                    if theme in next_themes:
                        links.append({
                            "source": f"{year}_{theme}",
                            "target": f"{next_year}_{theme}",
                            "value": min(theme_dict[theme], next_themes[theme])
                        })

    return {"nodes": nodes, "links": links, "years": years, "themes": list(all_themes)}


def generate_html_visualization(
    graph_data: dict,
    title: str = "Blog Concept Map",
    output_path: Optional[Path] = None
) -> str:
    """
    Generate an interactive HTML visualization using D3.js.
    """
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #fafafa;
        }}
        h1 {{
            color: #333;
            font-weight: 400;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        #graph {{
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
        }}
        .node {{
            cursor: pointer;
        }}
        .node circle {{
            stroke: #fff;
            stroke-width: 2px;
        }}
        .node text {{
            font-size: 11px;
            fill: #333;
            pointer-events: none;
        }}
        .link {{
            stroke: #999;
            stroke-opacity: 0.4;
        }}
        .tooltip {{
            position: absolute;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            font-size: 12px;
            pointer-events: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .controls {{
            margin-bottom: 15px;
        }}
        .controls label {{
            margin-right: 20px;
            font-size: 13px;
        }}
        .legend {{
            margin-top: 15px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="subtitle">Interactive concept map showing relationships between themes in the blog archive.
    Drag nodes to explore. Node size indicates frequency. Edge thickness indicates co-occurrence.</p>

    <div class="controls">
        <label>
            Min connections:
            <input type="range" id="minEdges" min="1" max="20" value="3">
            <span id="minEdgesVal">3</span>
        </label>
        <label>
            Link strength:
            <input type="range" id="linkStrength" min="1" max="100" value="30">
        </label>
    </div>

    <svg id="graph" width="1200" height="800"></svg>

    <div class="legend">
        <strong>Tips:</strong> Drag nodes to reposition. Scroll to zoom. Click nodes for details.
    </div>

    <div class="tooltip" style="display: none;"></div>

    <script>
        const data = {json.dumps(graph_data)};

        const width = 1200;
        const height = 800;

        const svg = d3.select("#graph")
            .attr("viewBox", [0, 0, width, height]);

        const g = svg.append("g");

        // Zoom behavior
        svg.call(d3.zoom()
            .extent([[0, 0], [width, height]])
            .scaleExtent([0.5, 4])
            .on("zoom", (event) => g.attr("transform", event.transform)));

        // Color scale based on document count
        const colorScale = d3.scaleSequential(d3.interpolateBlues)
            .domain([0, d3.max(data.nodes, d => d.doc_count)]);

        // Create simulation
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.edges)
                .id(d => d.id)
                .distance(100)
                .strength(d => d.weight / 50))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => d.size + 10));

        // Draw edges
        const link = g.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(data.edges)
            .join("line")
            .attr("class", "link")
            .attr("stroke-width", d => Math.sqrt(d.weight));

        // Draw nodes
        const node = g.append("g")
            .attr("class", "nodes")
            .selectAll("g")
            .data(data.nodes)
            .join("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));

        node.append("circle")
            .attr("r", d => d.size)
            .attr("fill", d => colorScale(d.doc_count));

        node.append("text")
            .attr("dx", d => d.size + 3)
            .attr("dy", ".35em")
            .text(d => d.label);

        // Tooltip
        const tooltip = d3.select(".tooltip");

        node.on("mouseover", (event, d) => {{
            tooltip
                .style("display", "block")
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px")
                .html(`<strong>${{d.label}}</strong><br>Appears in ${{d.doc_count}} posts`);
        }})
        .on("mouseout", () => tooltip.style("display", "none"));

        // Update positions on tick
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});

        // Drag functions
        function dragstarted(event) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }}

        function dragged(event) {{
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }}

        function dragended(event) {{
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }}

        // Controls
        d3.select("#minEdges").on("input", function() {{
            const val = +this.value;
            d3.select("#minEdgesVal").text(val);
            link.style("display", d => d.weight >= val ? null : "none");
        }});

        d3.select("#linkStrength").on("input", function() {{
            const val = +this.value;
            simulation.force("link").strength(d => d.weight / val);
            simulation.alpha(0.5).restart();
        }});
    </script>
</body>
</html>'''

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    return html


def main():
    """Generate visualization from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate concept map visualization")
    parser.add_argument("index", help="Path to blog index file")
    parser.add_argument("-o", "--output", default="concept_map.html", help="Output HTML file")
    parser.add_argument("--max-concepts", type=int, default=80, help="Maximum concepts to show")
    parser.add_argument("--min-cooccurrence", type=int, default=3, help="Minimum co-occurrence count")

    args = parser.parse_args()

    print(f"Loading index from {args.index}...")
    indexer = BlogIndexer.load(Path(args.index))

    print("Generating concept graph...")
    graph = generate_concept_graph(
        indexer,
        min_cooccurrence=args.min_cooccurrence,
        max_concepts=args.max_concepts
    )

    print(f"Graph has {len(graph['nodes'])} nodes and {len(graph['edges'])} edges")

    output_path = Path(args.output)
    generate_html_visualization(graph, output_path=output_path)

    print(f"Visualization saved to {output_path}")


if __name__ == "__main__":
    main()
