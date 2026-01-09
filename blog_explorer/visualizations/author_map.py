"""
Author Citation Map Visualization

Creates interactive HTML visualizations showing the most cited authors
in a research field. Supports multiple visualization types:
- Bubble chart (citation count as size)
- Bar chart (ranked by citations)
- Network graph (authors connected by shared interests)
"""

import json
import math
from pathlib import Path
from typing import Optional
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scholar import FieldAnalysis, Author


def generate_author_bubble_data(analysis: FieldAnalysis, max_authors: int = 50) -> dict:
    """
    Generate data for bubble chart visualization.

    Bubble size = total citations
    Color = h-index
    Position = clustered by research interests
    """
    # Collect all interests for clustering
    all_interests = set()
    for author in analysis.authors:
        all_interests.update(author.interests)

    # Assign colors to interest areas
    interest_list = sorted(all_interests)
    interest_colors = {interest: i for i, interest in enumerate(interest_list)}

    nodes = []
    for author in analysis.authors[:max_authors]:
        # Determine primary interest (first one)
        primary_interest = author.interests[0] if author.interests else "general"
        color_idx = interest_colors.get(primary_interest, 0)

        nodes.append({
            "id": author.scholar_id or author.name,
            "name": author.name,
            "affiliation": author.affiliation,
            "citations": author.citations,
            "h_index": author.h_index,
            "i10_index": author.i10_index,
            "interests": author.interests,
            "primary_interest": primary_interest,
            "color_group": color_idx,
            "size": math.sqrt(author.citations) / 10 + 10  # Scale for visibility
        })

    return {
        "nodes": nodes,
        "field_name": analysis.field_name,
        "total_analyzed": analysis.total_publications_analyzed,
        "fetch_date": analysis.fetch_date,
        "interests": interest_list
    }


def generate_author_network_data(analysis: FieldAnalysis, max_authors: int = 50) -> dict:
    """
    Generate data for network graph visualization.

    Authors are connected if they share research interests.
    Edge weight = number of shared interests.
    """
    authors = analysis.authors[:max_authors]

    # Build nodes
    nodes = []
    for author in authors:
        nodes.append({
            "id": author.scholar_id or author.name,
            "name": author.name,
            "affiliation": author.affiliation,
            "citations": author.citations,
            "h_index": author.h_index,
            "interests": author.interests,
            "size": math.log(author.citations + 1) * 3 + 8
        })

    # Build edges based on shared interests
    edges = []
    for i, a1 in enumerate(authors):
        for a2 in authors[i+1:]:
            shared = set(a1.interests) & set(a2.interests)
            if shared:
                edges.append({
                    "source": a1.scholar_id or a1.name,
                    "target": a2.scholar_id or a2.name,
                    "shared_interests": list(shared),
                    "weight": len(shared)
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "field_name": analysis.field_name
    }


def generate_html_bubble_chart(
    data: dict,
    title: Optional[str] = None,
    output_path: Optional[Path] = None
) -> str:
    """
    Generate an interactive bubble chart visualization.

    Bubble size represents citation count.
    Hover for author details.
    Click to open Google Scholar profile.
    """
    title = title or f"Most Cited Authors in {data['field_name']}"

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: white;
            font-weight: 300;
            font-size: 2.5em;
            margin-bottom: 5px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        .subtitle {{
            color: rgba(255,255,255,0.9);
            font-size: 16px;
            margin-bottom: 20px;
        }}
        .stats {{
            display: flex;
            gap: 30px;
            margin-bottom: 20px;
        }}
        .stat {{
            background: rgba(255,255,255,0.15);
            padding: 15px 25px;
            border-radius: 10px;
            color: white;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: 600;
        }}
        .stat-label {{
            font-size: 12px;
            text-transform: uppercase;
            opacity: 0.8;
        }}
        #chart {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .bubble {{
            cursor: pointer;
            transition: opacity 0.2s;
        }}
        .bubble:hover {{
            opacity: 0.8;
        }}
        .tooltip {{
            position: absolute;
            background: white;
            border-radius: 8px;
            padding: 15px;
            font-size: 13px;
            pointer-events: none;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            max-width: 300px;
            z-index: 1000;
        }}
        .tooltip h3 {{
            margin: 0 0 8px 0;
            font-size: 16px;
            color: #333;
        }}
        .tooltip .affiliation {{
            color: #666;
            font-style: italic;
            margin-bottom: 10px;
        }}
        .tooltip .metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 10px;
        }}
        .tooltip .metric {{
            text-align: center;
        }}
        .tooltip .metric-value {{
            font-size: 18px;
            font-weight: 600;
            color: #667eea;
        }}
        .tooltip .metric-label {{
            font-size: 10px;
            color: #999;
            text-transform: uppercase;
        }}
        .tooltip .interests {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }}
        .tooltip .interest {{
            background: #f0f0f0;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            color: #666;
        }}
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            color: white;
            font-size: 12px;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        .controls {{
            margin: 15px 0;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            display: flex;
            gap: 20px;
            align-items: center;
        }}
        .controls label {{
            color: white;
            font-size: 13px;
        }}
        .controls select, .controls input {{
            padding: 8px 12px;
            border-radius: 6px;
            border: none;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p class="subtitle">Bubble size represents total citations. Click an author to view their Google Scholar profile.</p>

        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(data['nodes'])}</div>
                <div class="stat-label">Authors</div>
            </div>
            <div class="stat">
                <div class="stat-value">{data['total_analyzed']:,}</div>
                <div class="stat-label">Publications Analyzed</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sum(n['citations'] for n in data['nodes']):,}</div>
                <div class="stat-label">Total Citations</div>
            </div>
        </div>

        <div class="controls">
            <label>
                Sort by:
                <select id="sortBy">
                    <option value="citations">Citations</option>
                    <option value="h_index">H-Index</option>
                    <option value="name">Name</option>
                </select>
            </label>
            <label>
                Min citations:
                <input type="range" id="minCitations" min="0" max="50000" value="0" step="1000">
                <span id="minCitationsVal">0</span>
            </label>
        </div>

        <svg id="chart" width="1200" height="700"></svg>

        <div class="legend" id="legend"></div>
    </div>

    <div class="tooltip" style="display: none;"></div>

    <script>
        const data = {json.dumps(data)};

        const width = 1200;
        const height = 700;
        const margin = {{ top: 20, right: 20, bottom: 20, left: 20 }};

        const svg = d3.select("#chart");
        const tooltip = d3.select(".tooltip");

        // Color scale for interests
        const colorScale = d3.scaleOrdinal(d3.schemeTableau10);

        // Size scale
        const sizeScale = d3.scaleSqrt()
            .domain([0, d3.max(data.nodes, d => d.citations)])
            .range([10, 80]);

        // Create force simulation
        const simulation = d3.forceSimulation(data.nodes)
            .force("charge", d3.forceManyBody().strength(5))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => sizeScale(d.citations) + 2))
            .force("x", d3.forceX(width / 2).strength(0.05))
            .force("y", d3.forceY(height / 2).strength(0.05));

        // Draw bubbles
        const bubbles = svg.selectAll(".bubble")
            .data(data.nodes)
            .join("g")
            .attr("class", "bubble")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));

        bubbles.append("circle")
            .attr("r", d => sizeScale(d.citations))
            .attr("fill", d => colorScale(d.color_group))
            .attr("stroke", "white")
            .attr("stroke-width", 2)
            .attr("opacity", 0.85);

        bubbles.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", ".3em")
            .attr("font-size", d => Math.min(sizeScale(d.citations) / 3, 14))
            .attr("fill", "white")
            .attr("font-weight", "500")
            .text(d => d.name.split(" ").pop()); // Last name only

        // Tooltip events
        bubbles.on("mouseover", (event, d) => {{
            tooltip
                .style("display", "block")
                .style("left", (event.pageX + 15) + "px")
                .style("top", (event.pageY - 10) + "px")
                .html(`
                    <h3>${{d.name}}</h3>
                    <div class="affiliation">${{d.affiliation || 'Affiliation unknown'}}</div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">${{d.citations.toLocaleString()}}</div>
                            <div class="metric-label">Citations</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${{d.h_index}}</div>
                            <div class="metric-label">H-Index</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${{d.i10_index}}</div>
                            <div class="metric-label">i10-Index</div>
                        </div>
                    </div>
                    <div class="interests">
                        ${{d.interests.slice(0, 5).map(i => `<span class="interest">${{i}}</span>`).join('')}}
                    </div>
                `);
        }})
        .on("mousemove", (event) => {{
            tooltip
                .style("left", (event.pageX + 15) + "px")
                .style("top", (event.pageY - 10) + "px");
        }})
        .on("mouseout", () => {{
            tooltip.style("display", "none");
        }})
        .on("click", (event, d) => {{
            if (d.id && d.id !== d.name) {{
                window.open(`https://scholar.google.com/citations?user=${{d.id}}`, '_blank');
            }} else {{
                window.open(`https://scholar.google.com/scholar?q=author:"${{encodeURIComponent(d.name)}}"`, '_blank');
            }}
        }});

        // Update positions on tick
        simulation.on("tick", () => {{
            bubbles.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
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

        // Build legend
        const interestCounts = {{}};
        data.nodes.forEach(n => {{
            const interest = n.primary_interest;
            interestCounts[interest] = (interestCounts[interest] || 0) + 1;
        }});

        const legendItems = Object.entries(interestCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);

        const legend = d3.select("#legend");
        legendItems.forEach(([interest, count], i) => {{
            legend.append("div")
                .attr("class", "legend-item")
                .html(`<div class="legend-color" style="background: ${{colorScale(data.interests.indexOf(interest))}}"></div>${{interest}} (${{count}})`);
        }});

        // Controls
        d3.select("#minCitations").on("input", function() {{
            const val = +this.value;
            d3.select("#minCitationsVal").text(val.toLocaleString());
            bubbles.style("display", d => d.citations >= val ? null : "none");
        }});

        d3.select("#sortBy").on("change", function() {{
            const sortBy = this.value;
            // Re-run simulation with new positions
            simulation.alpha(0.5).restart();
        }});
    </script>
</body>
</html>'''

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Saved visualization to {output_path}")

    return html


def generate_html_bar_chart(
    data: dict,
    title: Optional[str] = None,
    output_path: Optional[Path] = None
) -> str:
    """
    Generate an interactive bar chart of authors ranked by citations.
    """
    title = title or f"Top Authors in {data['field_name']} by Citations"

    # Sort by citations
    sorted_nodes = sorted(data['nodes'], key=lambda x: x['citations'], reverse=True)

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
            padding: 30px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            font-weight: 400;
        }}
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .bar {{
            cursor: pointer;
        }}
        .bar:hover {{
            opacity: 0.8;
        }}
        .bar-label {{
            font-size: 12px;
            fill: #333;
        }}
        .bar-value {{
            font-size: 11px;
            fill: #666;
        }}
        .tooltip {{
            position: absolute;
            background: white;
            border-radius: 6px;
            padding: 12px;
            font-size: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            pointer-events: none;
            z-index: 100;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="chart-container">
        <svg id="chart"></svg>
    </div>
    <div class="tooltip" style="display: none;"></div>

    <script>
        const data = {json.dumps(sorted_nodes)};

        const margin = {{ top: 20, right: 120, bottom: 40, left: 200 }};
        const barHeight = 28;
        const width = 1000;
        const height = data.length * barHeight + margin.top + margin.bottom;

        const svg = d3.select("#chart")
            .attr("width", width)
            .attr("height", height);

        const g = svg.append("g")
            .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

        const x = d3.scaleLinear()
            .domain([0, d3.max(data, d => d.citations)])
            .range([0, width - margin.left - margin.right]);

        const y = d3.scaleBand()
            .domain(data.map(d => d.name))
            .range([0, data.length * barHeight])
            .padding(0.2);

        const colorScale = d3.scaleSequential(d3.interpolateBlues)
            .domain([0, d3.max(data, d => d.h_index)]);

        const tooltip = d3.select(".tooltip");

        // Bars
        g.selectAll(".bar")
            .data(data)
            .join("rect")
            .attr("class", "bar")
            .attr("x", 0)
            .attr("y", d => y(d.name))
            .attr("width", d => x(d.citations))
            .attr("height", y.bandwidth())
            .attr("fill", d => colorScale(d.h_index))
            .attr("rx", 3)
            .on("mouseover", (event, d) => {{
                tooltip
                    .style("display", "block")
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 10) + "px")
                    .html(`
                        <strong>${{d.name}}</strong><br>
                        ${{d.affiliation || ''}}<br><br>
                        Citations: ${{d.citations.toLocaleString()}}<br>
                        H-Index: ${{d.h_index}}<br>
                        i10-Index: ${{d.i10_index}}
                    `);
            }})
            .on("mouseout", () => tooltip.style("display", "none"))
            .on("click", (event, d) => {{
                if (d.id && d.id !== d.name) {{
                    window.open(`https://scholar.google.com/citations?user=${{d.id}}`, '_blank');
                }}
            }});

        // Labels
        g.selectAll(".bar-label")
            .data(data)
            .join("text")
            .attr("class", "bar-label")
            .attr("x", -10)
            .attr("y", d => y(d.name) + y.bandwidth() / 2)
            .attr("text-anchor", "end")
            .attr("dy", ".35em")
            .text(d => d.name);

        // Values
        g.selectAll(".bar-value")
            .data(data)
            .join("text")
            .attr("class", "bar-value")
            .attr("x", d => x(d.citations) + 5)
            .attr("y", d => y(d.name) + y.bandwidth() / 2)
            .attr("dy", ".35em")
            .text(d => d.citations.toLocaleString());
    </script>
</body>
</html>'''

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Saved visualization to {output_path}")

    return html


def generate_html_network_graph(
    data: dict,
    title: Optional[str] = None,
    output_path: Optional[Path] = None
) -> str:
    """
    Generate a network graph showing authors connected by shared interests.
    """
    title = title or f"Author Network in {data['field_name']}"

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
            background: #1a1a2e;
        }}
        h1 {{
            color: white;
            font-weight: 300;
        }}
        .subtitle {{
            color: rgba(255,255,255,0.7);
            font-size: 14px;
            margin-bottom: 20px;
        }}
        #chart {{
            background: #16213e;
            border-radius: 8px;
        }}
        .node {{
            cursor: pointer;
        }}
        .node text {{
            fill: white;
            font-size: 10px;
            pointer-events: none;
        }}
        .link {{
            stroke: rgba(255,255,255,0.2);
            stroke-opacity: 0.6;
        }}
        .tooltip {{
            position: absolute;
            background: white;
            border-radius: 6px;
            padding: 12px;
            font-size: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            pointer-events: none;
            z-index: 100;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="subtitle">Authors are connected when they share research interests. Edge thickness indicates number of shared interests.</p>

    <svg id="chart" width="1200" height="800"></svg>
    <div class="tooltip" style="display: none;"></div>

    <script>
        const data = {json.dumps(data)};

        const width = 1200;
        const height = 800;

        const svg = d3.select("#chart");
        const g = svg.append("g");
        const tooltip = d3.select(".tooltip");

        // Zoom
        svg.call(d3.zoom()
            .extent([[0, 0], [width, height]])
            .scaleExtent([0.5, 4])
            .on("zoom", (event) => g.attr("transform", event.transform)));

        const colorScale = d3.scaleSequential(d3.interpolatePlasma)
            .domain([0, d3.max(data.nodes, d => d.citations)]);

        // Simulation
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.edges)
                .id(d => d.id)
                .distance(100)
                .strength(d => d.weight / 5))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => d.size + 5));

        // Links
        const link = g.append("g")
            .selectAll("line")
            .data(data.edges)
            .join("line")
            .attr("class", "link")
            .attr("stroke-width", d => d.weight * 2);

        // Nodes
        const node = g.append("g")
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
            .attr("fill", d => colorScale(d.citations))
            .attr("stroke", "white")
            .attr("stroke-width", 2);

        node.append("text")
            .attr("dx", d => d.size + 3)
            .attr("dy", ".35em")
            .text(d => d.name.split(" ").pop());

        // Tooltips
        node.on("mouseover", (event, d) => {{
            tooltip
                .style("display", "block")
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px")
                .html(`
                    <strong>${{d.name}}</strong><br>
                    ${{d.affiliation || ''}}<br><br>
                    Citations: ${{d.citations.toLocaleString()}}<br>
                    H-Index: ${{d.h_index}}<br><br>
                    <em>Interests:</em> ${{d.interests.slice(0, 5).join(", ")}}
                `);
        }})
        .on("mouseout", () => tooltip.style("display", "none"))
        .on("click", (event, d) => {{
            if (d.id && d.id !== d.name) {{
                window.open(`https://scholar.google.com/citations?user=${{d.id}}`, '_blank');
            }}
        }});

        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});

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
    </script>
</body>
</html>'''

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Saved visualization to {output_path}")

    return html


def main():
    """Generate author visualization from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate author citation map visualization")
    parser.add_argument("analysis", help="Path to field analysis JSON file")
    parser.add_argument("-o", "--output", default="author_map.html", help="Output HTML file")
    parser.add_argument(
        "-t", "--type",
        choices=["bubble", "bar", "network"],
        default="bubble",
        help="Visualization type"
    )
    parser.add_argument("--max-authors", type=int, default=50, help="Maximum authors to show")

    args = parser.parse_args()

    print(f"Loading analysis from {args.analysis}...")
    analysis = FieldAnalysis.from_dict(
        json.load(open(args.analysis, 'r', encoding='utf-8'))
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


if __name__ == "__main__":
    main()
