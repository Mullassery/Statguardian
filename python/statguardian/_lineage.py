"""
StatGuardian Lineage Module — Lineage as First-Class Feature

This module provides Python access to lineage tracking, versioning, and analysis
for data warehouse transformations.

Example:
    ```python
    from statguardian import get_lineage_graph, get_lineage_version

    # Get current lineage graph
    lineage = get_lineage_graph(warehouse_config)

    # Access nodes and edges
    for node_id, node in lineage.nodes.items():
        print(f"{node.table_id}:{node.stage} at {node.warehouse}")

    # Find impact chain
    impact = lineage.get_impact_chain("customers_raw")
    print(f"If customers_raw breaks, affects: {impact}")
    ```
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
import json
import uuid

# Note: In production, these would be bound from Rust via pyo3
# For now, we use pure Python implementations that work with the Rust models


@dataclass
class LineageNode:
    """A table at a specific transformation stage"""

    node_id: str
    table_id: str
    stage: str
    version: int
    warehouse: str
    database: str
    schema_name: str
    table_name: str
    transformation_sql: Optional[str] = None
    transformation_name: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    created_at: Optional[str] = None  # ISO format datetime
    last_accessed: Optional[str] = None
    columns: List[str] = field(default_factory=list)
    row_count: Optional[int] = None

    def qualified_name(self) -> str:
        """Full qualified name"""
        return f"{self.database}.{self.schema_name}.{self.table_name}"

    def cache_key(self) -> str:
        """Unique cache key"""
        return f"{self.table_id}:{self.stage}:v{self.version}"


@dataclass
class LineageEdge:
    """A dependency from one table to another"""

    edge_id: str
    source_node_id: str
    target_node_id: str
    join_type: Optional[str] = None
    columns_used: List[str] = field(default_factory=list)
    filter_condition: Optional[str] = None
    version: int = 1
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    modification_reason: Optional[str] = None


@dataclass
class LineageChange:
    """A single change in the lineage graph"""

    change_type: str  # "node_added", "node_removed", "edge_added", "edge_removed", "edge_modified"
    source_table: str
    target_table: Optional[str] = None
    change_reason: Optional[str] = None
    changed_at: Optional[str] = None
    changed_by: Optional[str] = None
    tables_affected: List[str] = field(default_factory=list)
    severity: str = "NONE"  # "NONE", "LOW", "MEDIUM", "HIGH"
    propagates_schema_changes: bool = False


@dataclass
class LineageGraph:
    """Complete DAG of table transformations"""

    warehouse_id: str
    timestamp: str  # ISO format datetime
    nodes: Dict[str, LineageNode] = field(default_factory=dict)
    edges: List[LineageEdge] = field(default_factory=list)

    def add_node(self, node: LineageNode) -> None:
        """Add a node to the graph"""
        self.nodes[node.node_id] = node

    def add_edge(self, edge: LineageEdge) -> None:
        """Add an edge to the graph"""
        self.edges.append(edge)

    def get_upstream(self, target_node_id: str) -> List[str]:
        """Get all upstream tables (tables that feed into target)"""
        return [
            e.source_node_id
            for e in self.edges
            if e.target_node_id == target_node_id
        ]

    def get_downstream(self, source_node_id: str) -> List[str]:
        """Get all downstream tables (tables that depend on source)"""
        return [
            e.target_node_id
            for e in self.edges
            if e.source_node_id == source_node_id
        ]

    def get_impact_chain(self, target_node_id: str) -> List[str]:
        """Compute impact chain: all tables affected if target breaks"""
        affected = []
        queue = [target_node_id]
        visited = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            affected.append(current)

            for downstream in self.get_downstream(current):
                if downstream not in visited:
                    queue.append(downstream)

        return affected

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        """Get node by ID"""
        return self.nodes.get(node_id)

    def size(self) -> tuple:
        """Return (node_count, edge_count)"""
        return (len(self.nodes), len(self.edges))


@dataclass
class LineageVersion:
    """Snapshot of lineage at a point in time"""

    version_id: str
    lineage_graph: LineageGraph
    version_number: int
    timestamp: str  # ISO format datetime
    schema_versions: Dict[str, int] = field(default_factory=dict)
    quality_scores: Dict[str, float] = field(default_factory=dict)
    changes_from_previous: List[LineageChange] = field(default_factory=list)
    change_severity: str = "NONE"


def create_lineage_node(
    table_id: str,
    stage: str,
    version: int,
    warehouse: str,
    database: str,
    schema_name: str,
    table_name: str,
) -> LineageNode:
    """Helper to create a LineageNode with generated node_id"""
    node_id = f"{table_id}__{stage}__{version}"
    return LineageNode(
        node_id=node_id,
        table_id=table_id,
        stage=stage,
        version=version,
        warehouse=warehouse,
        database=database,
        schema_name=schema_name,
        table_name=table_name,
        created_at=datetime.utcnow().isoformat(),
    )


def create_lineage_edge(
    source_node_id: str,
    target_node_id: str,
) -> LineageEdge:
    """Helper to create a LineageEdge"""
    edge_id = f"{source_node_id}__{target_node_id}"
    return LineageEdge(
        edge_id=edge_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        created_at=datetime.utcnow().isoformat(),
    )


def lineage_node_from_dict(data: dict) -> LineageNode:
    """Deserialize LineageNode from dict"""
    return LineageNode(**data)


def lineage_edge_from_dict(data: dict) -> LineageEdge:
    """Deserialize LineageEdge from dict"""
    return LineageEdge(**data)


def lineage_graph_from_dict(data: dict) -> LineageGraph:
    """Deserialize LineageGraph from dict"""
    nodes = {
        k: lineage_node_from_dict(v) for k, v in data.get("nodes", {}).items()
    }
    edges = [lineage_edge_from_dict(e) for e in data.get("edges", [])]

    return LineageGraph(
        warehouse_id=data["warehouse_id"],
        timestamp=data["timestamp"],
        nodes=nodes,
        edges=edges,
    )


def lineage_version_from_dict(data: dict) -> LineageVersion:
    """Deserialize LineageVersion from dict"""
    return LineageVersion(
        version_id=data["version_id"],
        lineage_graph=lineage_graph_from_dict(data["lineage_graph"]),
        version_number=data["version_number"],
        timestamp=data["timestamp"],
        schema_versions=data.get("schema_versions", {}),
        quality_scores=data.get("quality_scores", {}),
        changes_from_previous=[
            LineageChange(**c) for c in data.get("changes_from_previous", [])
        ],
        change_severity=data.get("change_severity", "NONE"),
    )


# Note: These are stub implementations. In production, they would connect
# to the Rust backend via PyO3 bindings or via FFI.


def get_lineage_graph(warehouse_config: dict) -> LineageGraph:
    """
    Get current lineage graph for a warehouse.

    Args:
        warehouse_config: Configuration dict with warehouse connection details

    Returns:
        LineageGraph: Complete warehouse DAG
    """
    # TODO: Implement via Rust FFI / PyO3 binding
    # For now, return empty graph
    return LineageGraph(
        warehouse_id=warehouse_config.get("warehouse_id", "unknown"),
        timestamp=datetime.utcnow().isoformat(),
    )


def get_lineage_version(
    warehouse_config: dict, version: Optional[int] = None
) -> Optional[LineageVersion]:
    """
    Get specific lineage version.

    Args:
        warehouse_config: Configuration dict
        version: Version number (None = latest)

    Returns:
        LineageVersion or None if not found
    """
    # TODO: Implement via Rust FFI / PyO3 binding
    return None


def get_lineage_history(
    warehouse_config: dict, table_id: str, limit: int = 10
) -> List[LineageVersion]:
    """
    Get lineage history for a specific table.

    Args:
        warehouse_config: Configuration dict
        table_id: Table identifier
        limit: Max versions to return

    Returns:
        List of LineageVersion objects
    """
    # TODO: Implement via Rust FFI / PyO3 binding
    return []


__all__ = [
    "LineageNode",
    "LineageEdge",
    "LineageGraph",
    "LineageVersion",
    "LineageChange",
    "create_lineage_node",
    "create_lineage_edge",
    "lineage_node_from_dict",
    "lineage_edge_from_dict",
    "lineage_graph_from_dict",
    "lineage_version_from_dict",
    "get_lineage_graph",
    "get_lineage_version",
    "get_lineage_history",
]
