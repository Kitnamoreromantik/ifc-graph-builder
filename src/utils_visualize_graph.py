import itertools
import logging

import matplotlib.colors as mcolors
from pyvis.network import Network

logger = logging.getLogger("main")  # Matches the __name__ of main.py when run


def visualize_graph_pyvis(G, html_path):
    """Generates an interactive HTML visualization of a NetworkX graph using PyVis.

    Nodes are color-coded by their IFC type and labeled with entity ID and type.
    Edges are labeled based on IFC relationship attributes. A hierarchical layout
    is applied to enhance readability, and the output is saved as an HTML file.

    Args:
        G (networkx.Graph): The graph representing IFC entities and relationships.
        html_path (Path or str): Path to save the resulting HTML visualization.
    """
    net = Network(notebook=False, height="800px", width="100%", directed=False)
    # net.force_atlas_2based(gravity=-50)
    net.set_options("""
                    {
                    "layout": {
                        "hierarchical": {
                        "enabled": true,
                        "direction": "LR",
                        "sortMethod": "hubsize",
                        "levelSeparation": 300,
                        "nodeSpacing": 200
                        }
                    },
                    "physics": {
                        "enabled": false
                    }
                    }
                    """)  #  "direction": "UD" upside-dow or "LR" left-to-right

    # Prepare a pool of distinguishable colors
    color_cycle = itertools.cycle(mcolors.TABLEAU_COLORS.values())
    type_color_map = {}

    for node, data in G.nodes(data=True):
        node_type_list = data.get("labels", [])
        node_type = node_type_list[0] if node_type_list else "Unknown"
        node_id = data.get("id", node)

        # Assign color dynamically if new type
        if node_type not in type_color_map:
            type_color_map[node_type] = next(color_cycle)

        label = f"#{node_id}\n{node_type}"
        title = "\n".join([f"{k}: {v}" for k, v in data.items()])
        color = type_color_map[node_type]

        net.add_node(
            node,
            label=label,
            title=title,
            size=10,
            font={"multi": True, "size": 10},
            color=color,
        )

    for u, v, data in G.edges(data=True):
        net.add_edge(u, v, title=data.get("label", ""), label=data.get("label", ""))

    net.write_html(str(html_path))
    logger.info(f"Interactive graph is saved to: {html_path}")
