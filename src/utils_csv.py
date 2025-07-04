import csv
import logging
import os

logger = logging.getLogger("main")


def _get_all_node_keys(G):
    keys = set()
    for _, data in G.nodes(data=True):
        keys.update(data.keys())
    return sorted(keys)


def export_nodes_to_csv(G, path="out/nodes.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Collect all keys excluding 'id' and 'type'
    keys = _get_all_node_keys(G)
    keys = [k for k in keys if k not in ("id", "type")]

    # Ensure id and type are first
    fieldnames = ["id", "type"] + keys

    with open(path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for node, data in G.nodes(data=True):
            row = {"id": node, "type": data.get("type", "")}
            for k in keys:
                row[k] = data.get(k, "")
            writer.writerow(row)

    logger.info(f"Nodes exported to: {path}")


def export_edges_to_csv(G, path="out/edges.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode="w", newline="", encoding="utf-8-sig") as f:  # <- use utf-8-sig
        writer = csv.writer(f)
        header = ["source", "target", "label"]
        writer.writerow(header)
        for u, v, data in G.edges(data=True):
            writer.writerow([u, v, data.get("label", "")])
    logger.info(f"Edges exported to: {path}")
