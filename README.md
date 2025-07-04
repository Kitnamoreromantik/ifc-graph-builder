
# Overview

`ifc_graph_builder/main.py`

The parser transforms an IFC-file into a graph representation using `networkx`, with nodes corresponding to IFC entities and edges representing semantic relationships between them. The resulting graph is exported as JSON to subsequently import in graph database, and optionally visualized via `pyvis` (`html` file is generated).

## Execution

Run `python main.py`

This will parse the file located at `data/file.ifc` and store all outputs in a timestamped folder within `data/out/`. These include the resulting graph in JSON format (3 files for nodes, edges, and both), as well as an HTML visualization for exploratory analysis of parsed data.


### Input

The parser requires a single IFC file as input, located at `data/file.ifc`. It must conform to standard IFC schema definitions. 

### Output

The parser generates multiple artifacts, stored under a timestamped directory within `data/out/`:

- `nodes.json`: A JSON file containing all parsed graph nodes, each representing an IFC entity with associated scalar attributes and labels.
- `edges.json`: A JSON file describing the relationships between nodes as edges, labeled by property names used in the original IFC references.
- `ifc.json`: A merged JSON file containing both nodes and edges in a format suitable for import into a graph database (e.g., Memgraph, Neo4j).
- `ifc_graph.html`: An interactive HTML visualization of the graph using the PyVis library, useful for visual inspection and debugging.

## Logic

The processing is organised as follows:

An IFC model is opened with Pythonic library [`ifcopenshell`](https://ifcopenshell.org). A filtering logic selects a subset of entities to act as entry points or "host" entities (e.g., `IfcSpace`). These hosts are iterated over the whole IFC model. For each, the parser initiates a depth-first recursive traversal of all their related entities, according to the IFC schema relations exposed via `ifcopenshell` functions `get_info()` and `get_psets()`.

Each entity is added as a node to a [NetworkX](https://networkx.org) graph. Non-empty scalar properties are preserved, while entity references are excluded from the node payload to avoid redundancy. Instead, such referenced IFC entities later on _recursively_ connected as nodes and wired through the graph edges, labeled with the property name that induced the relation (e.g., `ObjectPlacement`, `ContainedInStructure`). 

Recursion depth is controlled via `MAX_PARSE_RECURSION_DEPTH`. This limits how deep into the semantic tree the parser traverses. When set to `None`, traversal proceeds without limit unless cycles are encountered.

Cycle prevention is implemented via a tracking set `recursively_visited_ifc_ids` that ensures the graph construction remains finite and acyclic in practice, even if the IFC model has recursive references.

The graph is constructed incrementally. Each root IFC entity is parsed along with its semantic tree. After a configured number of root host entities (defined by `NODES_LIMIT`) are processed, parsing terminates. This enables partial parsing of large IFC models with bounded memory consumption.

## Output structure

Upon completion, the graph is exported into separate `nodes.json` and `edges.json` files. These are further merged into a single `ifc.json` for graph database import. Each node in the graph includes its IFC type as label and associated scalar properties (e.g., dimensions, name, GUID). Each edge includes the label of the relationship and the directionality implied by the source entity's reference.

In addition to the raw data output, the graph is visualized with `PyVis` into an HTML file, allowing interactive inspection of the parsed graph.


## Filtering and configuration

Entity filtering is defined in the `ALLOWED_IFC_TYPES` set. This restricts which IFC types serve as roots of semantic extraction. For exampale, only `IfcSpace` can be enabled, though the parser is designed to generalize across types. **More intelligent filtering could be introduced in the future via MVD (Model View Definitions), or by using LLMs to dynamically infer relevant projections of the IFC schema.**

## Future work

Several improvements are planned. 

These include MVD integration for schema-aware filtering, extension of edge property assignment, selective post-filtering of recursively added entities, and support for dynamic reasoning-driven parsing where models select their own relevant scopes based on task context. Or using advanced [`ifcopenshell`](https://ifcopenshell.org) features such as [IfcPatch](https://docs.ifcopenshell.org/autoapi/ifcpatch/index.html).

There is also intention to enable seamless integration with graph DBMS systems (e.g., Memgraph or Neo4j) by aligning exported JSON formats with database import standards. Deployment workflows involving Docker are under consideration for automated data ingestion.
