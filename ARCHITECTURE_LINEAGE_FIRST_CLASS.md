# StatGuardian v2.2 — Lineage as First-Class Feature

**Date:** 2026-07-17  
**Status:** ARCHITECTURE DESIGN (LOCKED)  
**Priority:** P0 CRITICAL (blocking PyStreamMCP v0.3)  
**Vision:** Make lineage a foundational concept alongside schema, not bolted-on

---

## Executive Problem Statement

### Current Gaps

StatGuardian validates **individual tables** but doesn't understand **table relationships**:

```
❌ What StatGuardian DOES know:
   customers (v1): [id, name, email, phone]
   customers (v2): [id, name, email, phone, region]  ← schema change detected

❌ What StatGuardian DOESN'T know:
   customers_raw → (clean) → customers_cleaned
   customers_cleaned → (enrich) → customers_enriched
   customers_enriched → (aggregate) → customer_metrics

   IF customers_raw schema changes:
   └─ IMPACT: customers_cleaned becomes invalid
   └─ IMPACT: customers_enriched becomes invalid
   └─ IMPACT: customer_metrics becomes invalid
   
   StatGuardian detects this for EACH table, but doesn't know they're related.
```

### Data Analytics Reality

In data warehouses/data lakes:
- Same table flows through **multiple stages** (raw → cleaned → enriched → aggregated)
- Each stage has **different meaning** but shares lineage
- Schema changes **propagate downstream** (breaking dependent analyses)
- Agents need **transformation chain context** (not just schema)
- Quality scores need **lineage-aware propagation** (garbage in = garbage out chain)

### The Solution: Lineage as Core Entity

**NOT:** "Lineage is a metadata layer on top of schema validation"  
**YES:** "Lineage is a first-class entity alongside schema, drift, quality"

---

## Architecture Overview

### 3-Layer Lineage System

```
┌────────────────────────────────────────────────────────────────┐
│ LINEAGE EXTRACTION LAYER                                       │
│ ├─ Native API Extractors (Delta/Iceberg/Hudi/Query-based)     │
│ ├─ SQL table lineage parsing (FROM/JOIN/INSERT INTO)          │
│ ├─ dbt manifest parsing (if available)                        │
│ └─ Custom lineage ingestion API                               │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ LINEAGE VERSIONING & CHANGE DETECTION                        │
│ ├─ LineageVersion (snapshot at timestamp)                    │
│ ├─ LineageChange (when dependencies change)                  │
│ ├─ LineageImpactAssessment (downstream effects)              │
│ └─ LineageStorage (database persistence)                     │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ LINEAGE INTEGRATION WITH VALIDATION                          │
│ ├─ Schema changes affect which tables?                       │
│ ├─ Drift detected in A, impacts B,C,D?                       │
│ ├─ Quality scoring propagates through lineage chain          │
│ └─ Anomalies in source = expected in downstream              │
└────────────────────────────────────────────────────────────────┘
```

---

## Core Data Structures

### 1. LineageNode (Represents a Table at a Stage)

```python
@dataclass
class LineageNode:
    """A table at a specific transformation stage"""
    table_id: str              # "customers" or "customers_enriched"
    stage: str                 # "raw" | "cleaned" | "enriched" | "aggregated"
    version: int               # Schema version
    
    # Connection info
    warehouse: str             # "snowflake" | "postgres" | "delta_lake" | "iceberg"
    database: str
    schema_name: str
    table_name: str
    
    # Transformation metadata
    transformation_sql: str    # SELECT ... FROM customers_raw WHERE ...
    transformation_name: str   # e.g., "deduplication", "type_coercion"
    
    # Timestamps
    created_at: datetime
    last_accessed: datetime
    
    # Semantics
    description: str           # "Customer records after deduplication"
    owner: str                 # Who owns this table
```

### 2. LineageEdge (Represents a Dependency)

```python
@dataclass
class LineageEdge:
    """A→B dependency (A feeds into B)"""
    source_node_id: str        # "customers_raw"
    target_node_id: str        # "customers_cleaned"
    
    # Edge properties
    join_type: str             # "full_join" | "left_join" | "inner_join" | "pass_through"
    columns_used: List[str]    # Columns from A that go into B
    filter_condition: str      # Optional: "WHERE timestamp > now() - 1 day"
    
    # Change tracking
    version: int               # Lineage edge version
    created_at: datetime
    last_modified: datetime
    modification_reason: str   # "Added new enrichment" | "Changed join logic"
```

### 3. LineageGraph (Complete Warehouse Graph)

```python
@dataclass
class LineageGraph:
    """Complete DAG of table transformations"""
    warehouse_id: str
    timestamp: datetime
    
    nodes: Dict[str, LineageNode]          # table_id → LineageNode
    edges: List[LineageEdge]               # All dependencies
    
    def get_upstream(self, table_id: str) -> List[str]:
        """All tables that feed into table_id"""
        return [e.source_node_id for e in self.edges 
                if e.target_node_id == table_id]
    
    def get_downstream(self, table_id: str) -> List[str]:
        """All tables that depend on table_id"""
        return [e.target_node_id for e in self.edges 
                if e.source_node_id == table_id]
    
    def get_impact_chain(self, table_id: str) -> List[str]:
        """All tables affected if table_id breaks"""
        # BFS through edges to find all downstream
```

### 4. LineageVersion (Snapshot with History)

```python
@dataclass
class LineageVersion:
    """Snapshot of lineage at a point in time"""
    lineage_graph: LineageGraph
    version_number: int
    timestamp: datetime
    schema_version: Dict[str, int]    # {table_id: schema_version}
    quality_scores: Dict[str, float]  # {table_id: quality_score}
    
    # Change tracking
    changes_from_previous: List[LineageChange]
    change_severity: str  # "HIGH" | "MEDIUM" | "LOW" | "NONE"
```

### 5. LineageChange (What Changed)

```python
@dataclass
class LineageChange:
    """A single change in the lineage graph"""
    change_type: str           # "node_added" | "node_removed" | "edge_added" | 
                               # "edge_removed" | "edge_modified"
    
    # What changed
    source_table: str
    target_table: Optional[str]
    
    # Why and when
    change_reason: str         # "Added deduplication step"
    changed_at: datetime
    changed_by: str            # Who made the change
    
    # Impact
    tables_affected: List[str]
    severity: str              # "HIGH" | "MEDIUM" | "LOW"
    propagates_schema_changes: bool  # Does this edge pass schema changes?
```

---

## Database Schema for Lineage Storage

### Tables

```sql
-- Core lineage nodes (tables)
CREATE TABLE lineage_nodes (
    node_id TEXT PRIMARY KEY,
    table_id TEXT NOT NULL,
    stage TEXT NOT NULL,          -- raw, cleaned, enriched, aggregated
    warehouse TEXT NOT NULL,
    database TEXT NOT NULL,
    schema_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    
    transformation_sql TEXT,
    transformation_name TEXT,
    description TEXT,
    owner TEXT,
    
    created_at DATETIME NOT NULL,
    last_accessed DATETIME,
    
    UNIQUE(table_id, stage)
);

-- Lineage edges (dependencies)
CREATE TABLE lineage_edges (
    edge_id TEXT PRIMARY KEY,
    source_node_id TEXT NOT NULL REFERENCES lineage_nodes(node_id),
    target_node_id TEXT NOT NULL REFERENCES lineage_nodes(node_id),
    
    join_type TEXT,
    columns_used TEXT,            -- JSON array
    filter_condition TEXT,
    
    version INT NOT NULL,
    created_at DATETIME NOT NULL,
    last_modified DATETIME,
    modification_reason TEXT,
    
    UNIQUE(source_node_id, target_node_id)
);

-- Lineage versions (snapshots with history)
CREATE TABLE lineage_versions (
    version_id TEXT PRIMARY KEY,
    warehouse_id TEXT NOT NULL,
    version_number INT NOT NULL,
    timestamp DATETIME NOT NULL,
    
    nodes_snapshot TEXT,          -- JSON serialization of all nodes
    edges_snapshot TEXT,          -- JSON serialization of all edges
    
    schema_versions TEXT,         -- {table_id: schema_version}
    quality_scores TEXT,          -- {table_id: quality_score}
    
    changes_from_previous TEXT,   -- JSON array of LineageChange
    change_severity TEXT,         -- HIGH | MEDIUM | LOW | NONE
    
    UNIQUE(warehouse_id, version_number)
);

-- Change history (audit trail)
CREATE TABLE lineage_changes (
    change_id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL REFERENCES lineage_versions(version_id),
    
    change_type TEXT,             -- node_added, edge_modified, etc.
    source_table TEXT,
    target_table TEXT,
    
    change_reason TEXT,
    changed_at DATETIME NOT NULL,
    changed_by TEXT,
    
    tables_affected TEXT,         -- JSON array
    severity TEXT,                -- HIGH | MEDIUM | LOW
    propagates_schema_changes BOOLEAN
);

-- Lineage impact assessments
CREATE TABLE lineage_impacts (
    impact_id TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    
    -- When this table changes, what breaks?
    downstream_tables TEXT,       -- JSON array of affected tables
    
    -- Quality propagation
    quality_propagation_score FLOAT,  -- 0.0-1.0, how much does quality degrade downstream
    
    -- Severity
    impact_severity TEXT,         -- HIGH | MEDIUM | LOW
    
    computed_at DATETIME NOT NULL,
    valid_until DATETIME NOT NULL
);

-- Index for common queries
CREATE INDEX idx_lineage_table ON lineage_nodes(table_id);
CREATE INDEX idx_lineage_stage ON lineage_nodes(table_id, stage);
CREATE INDEX idx_lineage_upstream ON lineage_edges(target_node_id);
CREATE INDEX idx_lineage_downstream ON lineage_edges(source_node_id);
CREATE INDEX idx_lineage_version ON lineage_versions(warehouse_id, version_number DESC);
```

---

## Lineage Extraction: Multi-Format Support

### 1. Native API Extractors

#### Delta Lake

```python
class DeltaLineageExtractor:
    """Extract lineage from Delta Lake _history() and table properties"""
    
    def extract_lineage(self, table_path: str) -> LineageGraph:
        # Use Delta table properties to find upstream tables
        # DeltaTable.detail()['table_properties'] may contain lineage hints
        # Parse SQL from table creation history
        pass
```

#### Apache Iceberg

```python
class IcebergLineageExtractor:
    """Extract lineage from Iceberg metadata and snapshots"""
    
    def extract_lineage(self, table_identifier: str) -> LineageGraph:
        # Use Iceberg's snapshot metadata
        # Parse SQL from schema evolution history
        # Extract transformation lineage if available
        pass
```

#### Apache Hudi

```python
class HudiLineageExtractor:
    """Extract lineage from Hudi commit timeline"""
    
    def extract_lineage(self, table_path: str) -> LineageGraph:
        # Use Hudi's commit timeline
        # Extract lineage from table properties
        pass
```

#### SQL-based (PostgreSQL/Snowflake)

```python
class SQLLineageExtractor:
    """Extract lineage from SQL query analysis and table lineage views"""
    
    def extract_lineage_from_query_log(self, warehouse) -> LineageGraph:
        # Parse query logs to build lineage
        # Identify CREATE TABLE AS SELECT patterns
        # Build transformation graph from INSERT INTO patterns
        pass
    
    def extract_lineage_from_lineage_views(self, warehouse) -> LineageGraph:
        # Some warehouses (Snowflake) have built-in lineage
        # Query their system views
        pass
```

#### Custom API Ingestion

```python
class CustomLineageIngestion:
    """Allow manual lineage ingestion"""
    
    def ingest_lineage(self, nodes: List[LineageNode], 
                      edges: List[LineageEdge]) -> LineageVersion:
        # Accept lineage from external sources (e.g., dbt, Fivetran)
        pass
```

---

## Lineage Change Detection

### Detecting Changes Between Versions

```python
class LineageChangeDetector:
    """Compare two LineageVersions to detect changes"""
    
    def detect_changes(self, previous: LineageVersion, 
                      current: LineageVersion) -> List[LineageChange]:
        """
        Detects:
        1. New nodes (new tables in warehouse)
        2. Removed nodes (tables deprecated)
        3. New edges (new dependencies)
        4. Removed edges (dependencies deleted)
        5. Modified edges (join logic changed)
        """
        pass
    
    def assess_severity(self, change: LineageChange) -> str:
        """
        HIGH: Breaking changes (edges removed, nodes removed)
        MEDIUM: Potentially disruptive (join type changed, filter added)
        LOW: Additive only (new tables, new edges added)
        """
        pass
    
    def compute_impact_chain(self, change: LineageChange, 
                            graph: LineageGraph) -> List[str]:
        """Which tables are affected by this change?"""
        # BFS through edges from change point to find all downstream
        pass
```

---

## Integration with Existing StatGuardian Components

### Schema Validation Integration

```python
class LineageAwareSchemaValidator:
    """Validate schemas considering lineage context"""
    
    def validate_with_lineage(self, table_id: str, 
                             lineage_graph: LineageGraph,
                             contract: DataContract) -> ValidationReport:
        # Validate table against contract
        # ALSO check: upstream table schemas (do they match expectations?)
        # Flag if upstream broke but this table somehow passed
        pass
    
    def predict_downstream_impact(self, schema_change: SchemaChange,
                                 table_id: str,
                                 lineage_graph: LineageGraph) -> List[str]:
        # Schema changed in customers_raw
        # Which downstream tables are affected?
        pass
```

### Drift Detection Integration

```python
class LineageAwareDriftDetector:
    """Detect drift considering upstream context"""
    
    def detect_drift_with_lineage(self, table_id: str,
                                 lineage_graph: LineageGraph,
                                 current_stats: Stats,
                                 baseline_stats: Stats) -> DriftReport:
        # Detect drift in this table
        # ALSO: Check upstream tables for drift
        # If upstream has drift, downstream drift might be expected
        pass
    
    def attribute_drift_source(self, table_id: str,
                              lineage_graph: LineageGraph) -> List[str]:
        # Drift detected in customers_enriched
        # Is it from customers_cleaned or the enrichment step itself?
        # Trace back through lineage
        pass
```

### Quality Scoring Through Lineage

```python
class LineageQualityPropagation:
    """Quality scores flow through lineage chain"""
    
    def compute_quality_score(self, table_id: str,
                             lineage_graph: LineageGraph,
                             current_metrics: QualityMetrics) -> float:
        # Quality of table = own metrics × upstream_quality
        # If upstream is garbage, downstream can't be good
        
        upstream_quality = self._get_upstream_quality(table_id, lineage_graph)
        own_quality = self._compute_own_quality(current_metrics)
        
        return own_quality * upstream_quality  # Multiplicative degradation
    
    def get_upstream_quality(self, table_id: str,
                            lineage_graph: LineageGraph) -> float:
        # Recursive: get quality of all upstream tables
        # Return minimum (weakest link breaks chain)
        pass
```

---

## API Surface (What PyStreamMCP Will Use)

### Core APIs

```python
# Extraction & Versioning
def get_lineage_graph(warehouse: str, timestamp: datetime = None) -> LineageGraph
def get_lineage_version(warehouse: str, version: int) -> LineageVersion
def get_lineage_history(warehouse: str, table_id: str, limit: int = 10) -> List[LineageVersion]

# Change Detection
def detect_lineage_changes(warehouse: str, previous_version: int, 
                          current_version: int) -> List[LineageChange]

# Impact Assessment
def get_impact_chain(warehouse: str, table_id: str) -> List[str]
def get_upstream_tables(warehouse: str, table_id: str) -> List[str]
def get_downstream_tables(warehouse: str, table_id: str) -> List[str]

# Quality Through Lineage
def get_quality_through_lineage(warehouse: str, table_id: str) -> float
def get_quality_degradation(warehouse: str, table_id: str) -> Dict[str, float]

# Change Validation
def validate_lineage_change_safety(warehouse: str, 
                                   proposed_change: LineageChange) -> ValidationReport
```

---

## Lineage Types: Four Patterns

### 1. Serial Lineage (Most Common in Analytics)

```
customers_raw 
  → (clean) → customers_cleaned
  → (enrich) → customers_enriched
  → (agg) → customer_metrics
```

**Validation:** Schema must flow unchanged through join columns

### 2. Fan-Out Lineage

```
orders_raw
  ├→ (clean) → orders_cleaned
  ├→ (denorm) → orders_denormalized
  └→ (sample) → orders_sample
```

**Validation:** All outputs must have compatible schemas with input

### 3. Fan-In Lineage (Joins)

```
customers_raw ┐
              ├→ (join) → customer_orders_joined
orders_raw    ┘
```

**Validation:** Join columns must be compatible types

### 4. Diamond Lineage (Complex)

```
raw_data 
  ├→ path_1 → path_1_clean
  │            ↓
  │         combined
  │            ↑
  └→ path_2 → path_2_clean
```

**Validation:** Convergence points must have compatible schemas

---

## Success Criteria for v2.2

### Correctness
✓ Lineage graph accurately represents warehouse structure  
✓ All table formats supported (Delta/Iceberg/Hudi/SQL)  
✓ Change detection catches 100% of dependency changes  
✓ Impact chains accurate (no false negatives)  

### Performance
✓ Extract lineage: <30 seconds for 1000-table warehouse  
✓ Change detection: <5 seconds  
✓ Impact chain computation: <100ms  
✓ Quality propagation: <50ms per table  

### Integration
✓ Schema validator uses lineage context  
✓ Drift detector attributes sources via lineage  
✓ Quality scores propagate through lineage  
✓ PyStreamMCP can use all APIs  

### Safety
✓ Lineage versioning prevents data loss  
✓ Audit trail for all changes  
✓ Change severity accurately categorized  
✓ Backward compatible with existing APIs  

---

## Why This Matters

**Before Lineage:**
```
Schema changed in customers_raw (HIGH severity)
❌ Agents don't know this breaks 47 downstream tables
❌ Cache gets invalidated for everything
❌ Agent context is just "customers has 20 columns"
```

**After Lineage:**
```
Lineage changed in customers_raw → customers_cleaned (HIGH severity)
✅ Impact chain immediately shows [customers_cleaned, customer_metrics, ...]
✅ Cache only invalidates affected chain
✅ Agent context is "customers_raw→cleaned→enriched→metrics (47 tables affected)"
✅ PyStreamMCP can reason about cost of cache misses
```

---

## Summary

**Lineage = Schema + Relationships + Quality**

With lineage as first-class:
- ✅ Agents understand transformation chains
- ✅ Cache invalidation is surgical (not blanket)
- ✅ Quality scores are meaningful (not garbage-in bias)
- ✅ Data dependencies are explicit
- ✅ Impact analysis is automatic
