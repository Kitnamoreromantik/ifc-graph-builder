import json
import logging
from pathlib import Path

import networkx as nx

logger = logging.getLogger("main")  # Matches the __name__ of main.py when run


def export_edges_to_json(G: nx.Graph, output_path: Path):
    """Export edges from a NetworkX graph to a JSON file.

    Each edge is serialized as a dict with the fields:
    'start', 'end', 'id', 'label', 'type', 'properties'.
    The output JSON is written to the specified file path.

    Args:
        G (nx.Graph): A NetworkX graph containing edge data.
        output_path (Path): The file path where the JSON will be saved.

    Raises:
        KeyError: If an edge in the graph is missing the 'id' attribute.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    edge_list = []
    for u, v, data in G.edges(data=True):
        if "id" not in data:
            raise ValueError(f"Missing 'id' in edge ({u}, {v})")

        edge_list.append(
            {
                "start": u,
                "end": v,
                "id": abs(int(data["id"])),
                "label": data.get("label", ""),
                "type": "relationship",
                "properties": data.get("properties", {}),
            }
        )

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(edge_list, f, indent=4, ensure_ascii=False)

    logger.info(f"Edges exported to: {output_path}")


def export_nodes_to_json(G: nx.Graph, output_path: Path):
    """Export nodes from a NetworkX graph to a JSON file.

    Each node is serialized as a dict with the fields:
    'id', 'labels', 'type', 'properties'.
    The output JSON is written to the specified file path.

    Args:
        G (nx.Graph): A NetworkX graph containing node data.
        output_path (Path): The file path where the JSON will be saved.

    Raises:
        OSError: If the file cannot be written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    node_list = []
    for node_id, data in G.nodes(data=True):
        labels = data.get("labels", [])
        properties = {k: v for k, v in data.items() if k != "labels"}
        node_list.append(
            {
                "id": node_id,
                "labels": labels if isinstance(labels, list) else [labels],
                "type": "node",
                "properties": properties,
            }
        )

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(node_list, f, indent=4, ensure_ascii=False)

    logger.info(f"Nodes exported to: {output_path}")


def merge_ifc_json(nodes_path: Path, edges_path: Path, output_path: Path):
    """Merges node and edge JSON files into a single JSON file.

    Reads two JSON files containing IFC graph nodes and edges, concatenates their
    contents into a single list, and writes the merged result to the specified output path.

    Args:
        nodes_path (Path): Path to the JSON file containing graph nodes.
        edges_path (Path): Path to the JSON file containing graph edges.
        output_path (Path): Destination path for the merged JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with nodes_path.open("r", encoding="utf-8") as f:
        nodes = json.load(f)
    with edges_path.open("r", encoding="utf-8") as f:
        edges = json.load(f)

    merged = nodes + edges

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    logger.info(f"Merged {len(nodes)} nodes and {len(edges)} edges into {output_path}")
