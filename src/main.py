# To run in project root: python ifc_graph_builder/main.py
# To install a new package: python3 -m pip install ifcpatch
import logging
from datetime import datetime
from pathlib import Path

import ifcopenshell

# import ifcpatch
import ifcopenshell.util.element
import networkx as nx
import utils_json

# import utils_csv
import utils_visualize_graph

from collections import defaultdict
import random

IFC_PATH = Path("data/SampleHouse4.ifc")
# IFC_PATH = Path("data/SmallModelIfc2x3.ifc")
OUTPUT_DIR = Path("data/out") / datetime.now().strftime("%Y%m%d_%H%M%S")
NODES_PATH = OUTPUT_DIR / "nodes.json"
EDGES_PATH = OUTPUT_DIR / "edges.json"
MERGED_PATH = OUTPUT_DIR / (datetime.now().strftime("%m%d_%H%M%S") + "_ifc.json")  # to distinguis different json files on memgraph

NODES_LIMIT = None  # None or integer to limit number of parsed host IFC entities in order to save memory
MAX_PARSE_RECURSION_DEPTH = None  # None or integer to limit the related entities parsing recursion depth
# TODO: add logic that if we meet at max depth a connecting entity - add one step down (?)
# TODO: If IfcRel... also add related elements even if

# This does not limits the type of children nodes parsed recursively, though, only "host" ones:

# To obtain info about spaces:
ALLOWED_IFC_TYPES = {
    # Core
    "IfcSpace",

    # Geometry and Placement
    # "IfcLocalPlacement",
    # "IfcAxis2Placement3D",
    # "IfcDirection",
    # "IfcCartesianPoint",
    # "IfcProductDefinitionShape",
    # "IfcShapeRepresentation",

    # Property Sets and Quantities

    # These psets can be ignored since we call ifcopenshell.util.element.get_psets():
    # "IfcPropertySet",
    # "IfcPropertySingleValue",
    # "IfcRelDefinesByProperties",

    "IfcElementQuantity",
    "IfcQuantityArea",
    "IfcQuantityVolume",
    "IfcQuantityLength",
    
    # Contained Elements
    "IfcFurnishingElement",
    "IfcSystemFurnitureElement",
    "IfcDistributionElement",
    "IfcCovering",

    # Spatial Hierarchy
    "IfcBuildingStorey",
    "IfcZone",
    "IfcRelAggregates",
    "IfcRelContainedInSpatialStructure",

    # Boundaries and Openings
    "IfcRelSpaceBoundary",
    "IfcWall",
    "IfcWallStandardCase",
    "IfcDoor",
    "IfcWindow",
    "IfcOpeningElement",

    # Classification and Typing
    "IfcRelAssociatesClassification",
    "IfcClassificationReference",
    "IfcRelDefinesByType"
}
# TODO: Add MVD (?) to smartly parse a projection of the IFC schema 
# related to the current task for more reasonable filtering.
# Maybe in the future, give a LLM-coder the ability to decide about filtering parameters.

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def extract_graph_schema_with_examples(G: nx.Graph, max_examples=1) -> tuple[str, str]:
    nodes_schema = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    edges_schema = defaultdict(lambda: {"properties": defaultdict(set), "source_target_types": set()})
    exclude_props = {"id", "GlobalId", "labels"}

    def _flatten_dict(d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(_flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    # Collect node data:
    for _, data in G.nodes(data=True):
        label = data.get("labels", ["UNLABELED"])[0]
        flat_data = _flatten_dict(data)
        for prop, val in flat_data.items():
            if prop not in exclude_props:
                if isinstance(val, float):
                    val = round(val, 2)
                if '.' in prop:
                    parent, child = prop.split('.', 1)
                else:
                    parent, child = prop, None
                nodes_schema[label][parent][child].add(str(val))

    # Collect edge data:
    for src, tgt, data in G.edges(data=True):
        label = data.get("label", ["UNLABELED"])
        src_type = G.nodes[src].get("labels", ["UNKNOWN"])[0]
        tgt_type = G.nodes[tgt].get("labels", ["UNKNOWN"])[0]
        edges_schema[label]["source_target_types"].add((src_type, tgt_type))

        for prop, val in data.items():
            if prop not in {"label", "id"}:
                edges_schema[label]["properties"][prop].add(str(val))

    # Build node schema lines
    node_lines = []
    # node_lines.append("=== NODES SCHEMA ===")
    node_lines.append("Each node type includes properties hierarchy divided by '.' and sampled examples of each property values.\n")
    node_lines.append("The graph is parsed from Revit using ifcopenshell.\n")

    for label, parent_dict in nodes_schema.items():
        node_lines.append(f"Node Type: {label}")
        node_lines.append(f"Properties:")
        for parent, props in parent_dict.items():
            keys = list(props.keys())
            if keys[0] is not None:
                node_lines.append(f"\t.{parent}")
                for child, vals in props.items():
                    examples = random.sample(list(vals), min(len(vals), max_examples))
                    clean_examples = str(examples).translate(str.maketrans('', '', "[]'"))
                    node_lines.append(f"\t\t.{child}: {clean_examples}")
            else:
                examples = random.sample(list(props[None]), min(len(props[None]), max_examples))
                clean_examples = str(examples).translate(str.maketrans('', '', "[]'"))
                node_lines.append(f"\t.{parent}: {clean_examples}")
        node_lines.append("")

    # Build relationship schema lines:
    rel_lines = []
    # rel_lines.append("=== RELATIONSHIPS SCHEMA ===")
    for label, content in edges_schema.items():
        rel_lines.append(f"Type: {label}")
        for src_type, tgt_type in sorted(content["source_target_types"]):
            rel_lines.append(f"  - (:{src_type})-[:{label}]->(:{tgt_type})")
        rel_lines.append("")

    # Write to files:
    node_txt_path = str(OUTPUT_DIR / "ifc_nodes_schema_llm.txt")
    rel_txt_path = str(OUTPUT_DIR / "ifc_relationships_schema_llm.txt")

    with open(node_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(node_lines))

    with open(rel_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rel_lines))

    return node_txt_path, rel_txt_path


def _is_entity_or_collection_of_entites(v):
    """Checks if a value is an IFC entity or a list/tuple of IFC entities."""
    if isinstance(v, ifcopenshell.entity_instance):
        return True
    if isinstance(v, (list, tuple)) and all(isinstance(i, ifcopenshell.entity_instance) for i in v):
        return True
    return False


def _get_related_entities(entity):
    """Returns a dictionary of IFC attributes that reference other IFC entities."""
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
            d_res = {}
            for k, v in d.items():
                new_key = k.replace(" ", "_")
                d_res[new_key] = _replace_spaces_in_keys(v)
            return d_res
        elif isinstance(d, list):
            return [_replace_spaces_in_keys(i) for i in d]
        else:
            return d
    
    def _add_entity_to_graph(G, ifc_entity, depth=0):
        """
        Constructs a semantic graph from an IFC file using NetworkX.

        The function parses a subset of IFC entities defined in `ALLOWED_IFC_TYPES` and recursively expands
        each of them by traversing their referenced entities via IFC attributes. The resulting graph captures
        both the hierarchical and referential structure of the model.

        Each node in the graph corresponds to an IFC entity, enriched with filtered scalar attributes and
        inherited property sets (psets). References to other IFC entities (e.g., ObjectPlacement, RelAggregates)
        are excluded from node attributes and instead form labeled edges in the graph. Cycles in entity
        references are avoided by maintaining a visited entity set per recursion to prevent infinite expansion.

        The recursion depth can be limited by setting `MAX_PARSE_RECURSION_DEPTH`. The number of host
        (root) entities to include is also limited by the global `NODES_LIMIT` parameter. This allows controlled
        parsing of large IFC files in memory-constrained environments.

        The graph includes:
        - Nodes: Each with `labels` (entity type) and selected scalar attributes and property sets.
        - Edges: Directed from referencing to referenced entity, labeled by the IFC attribute name that induced the link.

        Args:
            ifc_file_path (str or Path): Path to the IFC file to be parsed.

        Returns:
            networkx.Graph: A graph where nodes represent IFC entities with attributes, and
                edges represent typed semantic references derived from the IFC schema.
        """

        ifc_entity_id = ifc_entity.id()
        ifc_entity_type = ifc_entity.is_a()

        ifc_entity_info = ifc_entity.get_info(recursive=False)
        ifc_entity_psets = ifcopenshell.util.element.get_psets(ifc_entity, should_inherit=False)
        ifc_entity_properties = ifc_entity_info | ifc_entity_psets

        # Filter out empty properties and 'id' as it is not a property per se:
        properties_filtered = {
            k: v for k, v in ifc_entity_properties.items() 
            if k != "id" and v not in ("", None) and not _is_entity_or_collection_of_entites(v)
        }

        properties_filtered["type"] = ifc_entity_type  # ensure type of entity is always recorded
        node_labels = []
        # Move "type" to "labels":
        if "type" in properties_filtered:
            node_labels.append(properties_filtered.pop("type"))

        properties_filtered["labels"] = node_labels
        # To inspect what we add as a node to G:
        # import json
        # print(json.dumps(properties_filtered, indent=4, ensure_ascii=False))

        properties_filtered = _replace_spaces_in_keys(properties_filtered)  # to ensure correct syntax in Cypher queries

        G.add_node(ifc_entity.id(), **properties_filtered)
        parsed_ifc_entities_types_and_ids.add((ifc_entity_id, ifc_entity_type))

        # RECURSIVELY append child ifc_entities the current ifc_entity refers to.
        # Then wire current host ifc_entity with its relatives,i.e. unfold the trees
        # rooted in the current host ifc_entity.
        relatives = _get_related_entities(ifc_entity)
        if relatives:
            depth += 1  # children recursion parse depth counter
            if MAX_PARSE_RECURSION_DEPTH is None or depth <= MAX_PARSE_RECURSION_DEPTH:
                for property_name, related_ifc_entities in relatives.items():
                    for relative_ifc_entity in related_ifc_entities:
                        relative_ifc_entity_id = relative_ifc_entity.id()
                        relative_ifc_entity_type = relative_ifc_entity.is_a()
                        if (relative_ifc_entity_id not in recursively_visited_ifc_ids  # to avoid endless recursion
                            and relative_ifc_entity_type in ALLOWED_IFC_TYPES):
                            G.add_edge(
                                ifc_entity_id,
                                relative_ifc_entity_id,
                                id=str(hash((ifc_entity_id, relative_ifc_entity_id, property_name))),
                                label=property_name.upper(),
                                properties={},
                            )  # NOTE: edge properties may be assigned too
                            G = _add_entity_to_graph(G, relative_ifc_entity, depth)
                            recursively_visited_ifc_ids.add(relative_ifc_entity_id)
        return G

    # Initialize:
    model = ifcopenshell.open(ifc_file_path)
    # # fixes classification codes asssigned by Revit to occurrences instead of types:
    # model = ifcpatch.execute({"input": ifcopenshell.open("data/G_07.ifc"),
    #                           "file": ifcopenshell.open("data/G_07.ifc"),
    #                           "recipe": "FixRevitClassificationCodeTypes"})
    G = nx.Graph()
    recursively_visited_ifc_ids = set()
    parsed_ifc_entities_types_and_ids = set()
    host_nodes_count = 0

    # Iterate over each IFC entity:
    logger.info(f"IFC graph is being parsed...")
    for ifc_entity in model:
        # Pre-process (e.g. filter):
        if ifc_entity.is_a() not in ALLOWED_IFC_TYPES:
            continue

        # Add the host IFC entity and its relatives (depending of the MAX_PARSE_RECURSION_DEPTH value)
        if ifc_entity.id() not in parsed_ifc_entities_types_and_ids:
            G = _add_entity_to_graph(G, ifc_entity)

        # Post-process:
        # TODO: may add post-filtering by IFC type ("wrong" ones could be recursively parsed children)
        recursively_visited_ifc_ids.clear()  # clear for the next recursions
        host_nodes_count += 1
        if NODES_LIMIT is not None and host_nodes_count >= NODES_LIMIT:
            break

    return G


def main():
    logger.info(f"Loading IFC file: {IFC_PATH}")

    G = build_ifc_graph(IFC_PATH)
    logger.info(f"IFC graph is built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    # logger.info(f"IFC graph has {len(list(nx.isolates(G)))} isolated node(s)")
    isolated_nodes = list(nx.isolates(G))
    isolated_labels = {
        G.nodes[n].get("labels", ["UNLABELED"])[0] for n in isolated_nodes
    }
    logger.info(f"Isolated nodes ({len(isolated_nodes)}), unique labels: {isolated_labels}")

    # Save for graph DBMS to import from CSV:
    # export_nodes_to_csv(G, "out/1/nodes.csv")
    # export_edges_to_csv(G, "out/1/edges.csv")

    # Save for graph DBMS to import from JSON:
    utils_json.export_nodes_to_json(G, NODES_PATH)
    utils_json.export_edges_to_json(G, EDGES_PATH)
    utils_json.merge_ifc_json(NODES_PATH, EDGES_PATH, MERGED_PATH)  # to be exported to the graph DB

    schema_txt_path = extract_graph_schema_with_examples(G)
    logger.info(f"LLM-friendly schema saved at: {schema_txt_path}")

    # Visualize graph if graph is small:
    if G.number_of_nodes() < 200:
        utils_visualize_graph.visualize_graph_pyvis(G, OUTPUT_DIR / "ifc_graph.html")


if __name__ == "__main__":
    main()
