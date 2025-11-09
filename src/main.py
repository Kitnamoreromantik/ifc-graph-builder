"""
main.py — IFC → Graph converter
--------------------------------
Usable from both:
    1) Command line:
        python src/main.py data/SampleHouse4.ifc data/out 1
    2) GUI:
        from src.main import run
        run(ifc_path, output_dir, depth)
"""

import logging
import json
import random
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import networkx as nx
import ifcopenshell
import ifcopenshell.util.element

import src.utils_json as utils_json
import src.utils_visualize_graph as utils_visualize_graph


# -------------------------------------------------------
# Global defaults (overridden in run())
# -------------------------------------------------------
IFC_PATH = Path("data/SampleHouse4.ifc")
OUTPUT_DIR = Path("data/out")
MAX_PARSE_RECURSION_DEPTH = 1
NODES_LIMIT = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# -------------------------------------------------------
# Helper: load allowed IFC types
# -------------------------------------------------------
def _load_allowed_types():
    global ALLOWED_IFC_TYPES, IS_FILTERED
    ALLOWED_TYPES_PATH = Path("allowed_ifc_types.json")
    if ALLOWED_TYPES_PATH.exists():
        with open(ALLOWED_TYPES_PATH, "r", encoding="utf-8") as f:
            ALLOWED_IFC_TYPES = set(json.load(f))
        IS_FILTERED = True
        logger.info(f"Filtering enabled — {len(ALLOWED_IFC_TYPES)} types loaded.")
    else:
        IS_FILTERED = False
        logger.warning("⚠️ allowed_ifc_types.json not found — parsing all entities.")


# -------------------------------------------------------
# IFC graph building
# -------------------------------------------------------
def _is_entity_or_collection_of_entites(v):
    if isinstance(v, ifcopenshell.entity_instance):
        return True
    if isinstance(v, (list, tuple)) and all(isinstance(i, ifcopenshell.entity_instance) for i in v):
        return True
    return False


def _get_related_entities(entity):
    ent_info = entity.get_info()
    refs = {}
    for attr, val in ent_info.items():
        if isinstance(val, ifcopenshell.entity_instance):
            refs.setdefault(attr, []).append(val)
        elif isinstance(val, (list, tuple)):
            for v in val:
                if isinstance(v, ifcopenshell.entity_instance):
                    refs.setdefault(attr, []).append(v)
    return refs


def build_ifc_graph(ifc_file_path):
    def _replace_spaces_in_keys(d):
        if isinstance(d, dict):
            return {k.replace(" ", "_"): _replace_spaces_in_keys(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [_replace_spaces_in_keys(i) for i in d]
        else:
            return d

    def _add_entity_to_graph(G, ifc_entity, ifc_entity_id, depth=0):
        ifc_entity_type = ifc_entity.is_a()
        ifc_entity_info = ifc_entity.get_info(recursive=False)
        ifc_entity_psets = ifcopenshell.util.element.get_psets(ifc_entity, should_inherit=False)
        ifc_entity_properties = ifc_entity_info | ifc_entity_psets

        properties_filtered = {
            k: v for k, v in ifc_entity_properties.items()
            if k != "id" and v not in ("", None) and not _is_entity_or_collection_of_entites(v)
        }

        properties_filtered["labels"] = [ifc_entity_type]
        properties_filtered = _replace_spaces_in_keys(properties_filtered)

        G.add_node(ifc_entity_id, **properties_filtered)
        parsed_ifc_entities_types_and_ids.add((ifc_entity_id, ifc_entity_type))

        relatives = _get_related_entities(ifc_entity)
        if relatives:
            depth += 1
            if MAX_PARSE_RECURSION_DEPTH is None or depth <= MAX_PARSE_RECURSION_DEPTH:
                for property_name, related_ifc_entities in relatives.items():
                    for child in related_ifc_entities:
                        child_id = child.id() or id(child)
                        if child_id not in recursively_visited_ifc_ids:
                            G.add_edge(
                                ifc_entity_id,
                                child_id,
                                id=str(hash((ifc_entity_id, child_id, property_name))),
                                label=property_name.upper(),
                                properties={
                                    "start_entity_type": ifc_entity_type,
                                    "target_entity_type": child.is_a(),
                                },
                            )
                            G = _add_entity_to_graph(G, child, child_id, depth)
                            recursively_visited_ifc_ids.add(child_id)
        return G

    logger.info("Parsing IFC graph...")
    model = ifcopenshell.open(ifc_file_path)
    G = nx.Graph()
    recursively_visited_ifc_ids = set()
    parsed_ifc_entities_types_and_ids = set()
    host_nodes_count = 0

    for ifc_entity in model:
        if IS_FILTERED and ifc_entity.is_a() not in ALLOWED_IFC_TYPES:
            continue
        ifc_entity_id = ifc_entity.id() or id(ifc_entity)
        G = _add_entity_to_graph(G, ifc_entity, ifc_entity_id)
        recursively_visited_ifc_ids.clear()
        host_nodes_count += 1
        if NODES_LIMIT and host_nodes_count >= NODES_LIMIT:
            break

    return G


# -------------------------------------------------------
# Schema utilities
# -------------------------------------------------------
def parse_ifc_relationships_schema(EDGES_PATH):
    with open(EDGES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    rel_map = defaultdict(set)
    for item in data:
        if item.get("type") != "relationship":
            continue
        label = item.get("label")
        props = item.get("properties", {})
        start = props.get("start_entity_type")
        end = props.get("target_entity_type")
        if all([label, start, end]):
            rel_map[label].add((start, end))

    lines = []
    for rel_type in sorted(rel_map):
        lines.append(f"Type: {rel_type}")
        for start, end in sorted(rel_map[rel_type]):
            lines.append(f"  - (:{start})-[:{rel_type}]->(:{end})")
        lines.append("")

    rel_txt_path = str(OUTPUT_DIR / "ifc_relationships_schema_llm.txt")
    with open(rel_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return rel_txt_path


def parse_ifc_nodes_schema(G, max_examples=1):
    nodes_schema = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    exclude_props = {"id", "GlobalId", "labels"}

    def _flatten_dict(d, parent_key="", sep="."):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(_flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    for _, data in G.nodes(data=True):
        label = data.get("labels", ["UNLABELED"])[0]
        flat = _flatten_dict(data)
        for prop, val in flat.items():
            if prop not in exclude_props:
                parent, child = prop.split(".", 1) if "." in prop else (prop, None)
                nodes_schema[label][parent][child].add(str(val))

    lines = ["Each node type includes properties hierarchy with sampled examples.\n"]
    for label, parent_dict in sorted(nodes_schema.items()):
        lines.append(f"Node Type: {label}")
        lines.append("Properties:")
        for parent, props in sorted(parent_dict.items()):
            if list(props.keys())[0] is not None:
                lines.append(f"\t.{parent}")
                for child, vals in sorted(props.items()):
                    sample = random.sample(list(vals), min(len(vals), max_examples))
                    lines.append(f"\t\t.{child}: {', '.join(sample)}")
            else:
                sample = random.sample(list(props[None]), min(len(props[None]), max_examples))
                lines.append(f"\t.{parent}: {', '.join(sample)}")
        lines.append("")

    node_txt_path = str(OUTPUT_DIR / "ifc_nodes_schema_llm.txt")
    with open(node_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return node_txt_path


# -------------------------------------------------------
# Main pipeline
# -------------------------------------------------------
def main():
    logger.info(f"Loading IFC file: {IFC_PATH}")
    _load_allowed_types()

    G = build_ifc_graph(IFC_PATH)
    logger.info(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    isolated_nodes = list(nx.isolates(G))
    isolated_labels = {G.nodes[n].get("labels", ['UNLABELED'])[0] for n in isolated_nodes}
    logger.info(f"Isolated nodes: {len(isolated_nodes)} — {isolated_labels}")
    num_clusters = nx.number_connected_components(G)
    logger.info(f"Connected components: {num_clusters}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    NODES_PATH = OUTPUT_DIR / "nodes.json"
    EDGES_PATH = OUTPUT_DIR / "edges.json"
    MERGED_PATH = OUTPUT_DIR / "graph_ifc.json"

    utils_json.export_nodes_to_json(G, NODES_PATH)
    utils_json.export_edges_to_json(G, EDGES_PATH)
    utils_json.merge_ifc_json(NODES_PATH, EDGES_PATH, MERGED_PATH)

    edges_schema_txt_path = parse_ifc_relationships_schema(EDGES_PATH)
    nodes_schema_txt_path = parse_ifc_nodes_schema(G)
    logger.info(f"Schemas saved:\n  Edges → {edges_schema_txt_path}\n  Nodes → {nodes_schema_txt_path}")

    if G.number_of_nodes() < 500:
        utils_visualize_graph.visualize_graph_pyvis(G, OUTPUT_DIR / "ifc_graph.html")


# -------------------------------------------------------
# Public API for GUI
# -------------------------------------------------------
def run(ifc_path: Path, output_dir: Path | None = None, depth: int | None = 1):
    """Entry point callable from GUI."""
    global IFC_PATH, OUTPUT_DIR, MAX_PARSE_RECURSION_DEPTH
    IFC_PATH = Path(ifc_path)
    OUTPUT_DIR = Path(output_dir) if output_dir else Path("data/out")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MAX_PARSE_RECURSION_DEPTH = depth
    main()


# -------------------------------------------------------
# CLI entry point
# -------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        in_path = Path(sys.argv[1])
        out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/out")
        if len(sys.argv) > 3:
            arg_depth = sys.argv[3]
            depth = None if str(arg_depth).lower() == "none" else int(arg_depth)
        else:
            depth = 1
        run(in_path, out_dir, depth)
    else:
        run(Path("data/SampleHouse4.ifc"), Path("data/out"), 1)
