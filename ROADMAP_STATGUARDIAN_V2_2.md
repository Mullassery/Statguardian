# StatGuardian v2.2 — Lineage Foundation Roadmap

**Date:** 2026-07-17  
**Status:** LOCKED & READY TO BUILD  
**Timeline:** 4 weeks (2026-07-24 to 2026-08-21)  
**Target Release:** 2026-08-21  
**Priority:** P0 CRITICAL (blocking PyStreamMCP v0.3)

---

## Executive Summary

Build lineage as a first-class StatGuardian feature:
- Track table dependencies (A→B→C transformations)
- Version lineage history (when dependencies change)
- Detect lineage changes with impact assessment
- Integrate with schema validation, drift detection, quality scoring
- Support all warehouse formats (Delta/Iceberg/Hudi/PostgreSQL/Snowflake)

**Output:** PyStreamMCP can consume LineageGraph and LineageVersion APIs to build intelligent caching and agent context discovery.

**Impact:**
- v2.2 (Aug 2026): Lineage foundation
- v0.3 PyStreamMCP (Aug 2026): Semantic caching + lineage-aware validation
- v3.0+ (Sep 2026+): Advanced features (predictive cache, cost modeling, ML lineage detection)

---

## Week-by-Week Breakdown

### WEEK 1: Core Lineage Data Structures & Storage

**Goal:** Lineage model defined, database schema created, extractors stubbed

#### Components to Build

**1. rust/statguardian-lineage/src/model.rs** (400 lines)
   - `LineageNode` struct (table + stage + transformation metadata)
   - `LineageEdge` struct (dependency A→B with join type/columns)
   - `LineageGraph` struct (complete DAG of tables)
   - `LineageVersion` struct (snapshot with history)
   - `LineageChange` enum (node_added, edge_modified, etc.)
   - Serialization/deserialization for JSON

**2. rust/statguardian-lineage/src/storage.rs** (300 lines)
   - `LineageStore` trait (abstract interface)
   - `SQLiteLineageStore` implementation
   - Database schema initialization
   - Version management (list, get, create)
   - Changelog operations

**3. python/statguardian/_lineage.py** (250 lines)
   - Python bindings for Rust lineage types
   - Public API: `get_lineage_graph()`, `get_lineage_version()`, etc.
   - Integration with DataContract model
   - Example usage

**Tests:** 20 unit tests
   - Model creation and validation
   - Serialization round-trips
   - Storage CRUD operations
   - Version management
   - Graph construction

**Milestones:**
- ✅ LineageNode, LineageEdge, LineageGraph models working
- ✅ SQLite schema created and tested
- ✅ Version history working (create/list/get)
- ✅ All 20 tests passing

**Files Created:**
- `crates/statguardian-lineage/` (new crate)
- `crates/statguardian-lineage/src/model.rs`
- `crates/statguardian-lineage/src/storage.rs`
- `crates/statguardian-lineage/src/lib.rs`
- `python/statguardian/_lineage.py`

---

### WEEK 2: Lineage Extraction from All Table Formats

**Goal:** Extract lineage from Delta/Iceberg/Hudi/PostgreSQL/Snowflake

#### Components to Build

**1. rust/statguardian-lineage/src/extractors/mod.rs** (100 lines)
   - `LineageExtractor` trait (common interface)
   - Router to select correct extractor by warehouse type

**2. rust/statguardian-lineage/src/extractors/delta.rs** (200 lines)
   - `DeltaLineageExtractor`
   - Parse Delta table history for lineage hints
   - Query table properties for upstream tables
   - Handle `_history` metadata

**3. rust/statguardian-lineage/src/extractors/iceberg.rs** (200 lines)
   - `IcebergLineageExtractor`
   - Use Iceberg snapshot metadata
   - Parse schema evolution for transformations
   - Extract lineage from table properties

**4. rust/statguardian-lineage/src/extractors/hudi.rs** (200 lines)
   - `HudiLineageExtractor`
   - Parse Hudi commit timeline
   - Extract lineage from table properties
   - Handle point-in-time lineage

**5. python/statguardian/_lineage_sql.py** (400 lines)
   - `SQLLineageExtractor` (for PostgreSQL/Snowflake/etc.)
   - Query lineage from database system views
   - Parse SQL query logs for CREATE TABLE AS SELECT patterns
   - Build lineage from INSERT INTO patterns
   - SQL dialect handling (Postgres vs Snowflake)

**6. python/statguardian/_lineage_custom.py** (150 lines)
   - `CustomLineageIngestion` (manual lineage input)
   - Accept lineage from dbt manifests (future)
   - Accept lineage from external systems (Fivetran, etc.)

**Tests:** 25 unit tests
   - Delta extractor (5 tests)
   - Iceberg extractor (5 tests)
   - Hudi extractor (5 tests)
   - SQL extractor (5 tests)
   - Custom ingestion (3 tests)
   - Error handling (2 tests)

**Milestones:**
- ✅ Delta lineage extraction working
- ✅ Iceberg lineage extraction working
- ✅ Hudi lineage extraction working
- ✅ SQL lineage extraction working
- ✅ Custom ingestion working
- ✅ All 25 tests passing

**Files Created:**
- `crates/statguardian-lineage/src/extractors/mod.rs`
- `crates/statguardian-lineage/src/extractors/delta.rs`
- `crates/statguardian-lineage/src/extractors/iceberg.rs`
- `crates/statguardian-lineage/src/extractors/hudi.rs`
- `python/statguardian/_lineage_sql.py`
- `python/statguardian/_lineage_custom.py`

**Files Modified:**
- `crates/statguardian-lineage/Cargo.toml` (add dependencies)
- `python/statguardian/__init__.py` (export new APIs)

---

### WEEK 3: Lineage Change Detection & Impact Assessment

**Goal:** Detect when lineage changes, assess severity and impact

#### Components to Build

**1. rust/statguardian-lineage/src/detector.rs** (350 lines)
   - `LineageChangeDetector` struct
   - `detect_changes()` method
   - Compares previous vs. current LineageVersion
   - Identifies: added nodes, removed nodes, added edges, removed edges, modified edges
   - Severity assessment logic (HIGH/MEDIUM/LOW)

**2. rust/statguardian-lineage/src/impact.rs** (250 lines)
   - `ImpactAnalyzer` struct
   - `compute_impact_chain()` - BFS to find all downstream tables
   - `assess_impact_severity()` - how much do downstream tables depend on this?
   - `propagation_score()` - 0.0-1.0 quality degradation through chain

**3. python/statguardian/_lineage_changes.py** (200 lines)
   - Python API for change detection
   - `detect_lineage_changes(warehouse, v1, v2) → List[LineageChange]`
   - `get_impact_chain(warehouse, table_id) → List[str]`
   - Integrate with existing StatGuardian reports

**4. Integration with SchemaValidator** (150 lines)
   - Modify `crates/statguardian-validators/src/schema.rs`
   - Add lineage context to schema validation
   - Flag when upstream schema incompatibility detected
   - Compute downstream impact of schema changes

**5. Integration with DriftDetector** (150 lines)
   - Modify `crates/statguardian-stats/src/drift.rs`
   - Add lineage context to drift detection
   - Track drift through lineage chain
   - Attribute drift source (is it from upstream or local transformation?)

**Tests:** 25 unit tests
   - Change detection: added/removed/modified (6 tests)
   - Severity assessment (4 tests)
   - Impact chain computation (6 tests)
   - Quality propagation (4 tests)
   - Schema validator integration (3 tests)
   - Drift detector integration (2 tests)

**Milestones:**
- ✅ Change detection working for all change types
- ✅ Severity assessment accurate
- ✅ Impact chains computed correctly
- ✅ Quality propagation through lineage
- ✅ Schema validator uses lineage
- ✅ Drift detector uses lineage
- ✅ All 25 tests passing

**Files Created:**
- `crates/statguardian-lineage/src/detector.rs`
- `crates/statguardian-lineage/src/impact.rs`
- `python/statguardian/_lineage_changes.py`

**Files Modified:**
- `crates/statguardian-validators/src/schema.rs` (add lineage context)
- `crates/statguardian-stats/src/drift.rs` (add lineage context)
- `python/statguardian/__init__.py` (export new APIs)

---

### WEEK 4: Integration, Testing, Documentation & Release

**Goal:** Integrate everything, comprehensive testing, document for PyStreamMCP, release v2.2

#### Tasks

**1. Integration Points**
   - Hook lineage into `execute()` flow
   - LineageStore initialized with DataContract
   - Lineage versioning happens automatically on validation
   - Change detection runs on every major validation

**2. Documentation**
   - LINEAGE_GUIDE.md (how to use lineage APIs)
   - LINEAGE_EXTRACTION.md (warehouse-specific setup)
   - API_REFERENCE.md (all public APIs)
   - MIGRATION.md (for users upgrading from v2.1)

**3. Examples**
   - `examples/lineage_extraction.py` - extract lineage from Snowflake
   - `examples/lineage_change_detection.py` - detect and handle changes
   - `examples/lineage_impact_analysis.py` - find affected tables
   - `examples/lineage_with_schema.py` - combined schema + lineage validation

**4. Integration Tests** (10 tests)
   - End-to-end lineage extraction
   - Change detection accuracy
   - Schema+lineage validation together
   - Drift+lineage detection together
   - Multi-warehouse lineage federation
   - Performance under large graphs (1000+ tables)
   - Edge cases (circular references, orphaned tables)
   - Backward compatibility with v2.1
   - State transitions (new table discovery)
   - Version rollback safety

**5. Performance Validation**
   - Lineage extraction: <30s for 1000-table warehouse
   - Change detection: <5s
   - Impact chain: <100ms
   - Quality propagation: <50ms

**6. Release Preparation**
   - Version bump to v2.2.0
   - CHANGELOG.md entry
   - GitHub release notes
   - Update README.md with lineage examples
   - PyPI package publishing
   - Announce PyStreamMCP dependency ready

**Files Created:**
- `docs/LINEAGE_GUIDE.md`
- `docs/LINEAGE_EXTRACTION.md`
- `docs/API_REFERENCE_LINEAGE.md`
- `docs/MIGRATION_V2_2.md`
- `examples/lineage_extraction.py`
- `examples/lineage_change_detection.py`
- `examples/lineage_impact_analysis.py`
- `examples/lineage_with_schema.py`

**Files Modified:**
- `README.md` (add lineage section)
- `ROADMAP.md` (update, move v3.5 to v2.2)
- `CHANGELOG.md` (v2.2.0 entry)
- `Cargo.toml` (version bump)
- `pyproject.toml` (version bump)
- `python/statguardian/__init__.py` (export all lineage APIs)

---

## Directory Structure

```
statguardian/
├── crates/
│   └── statguardian-lineage/           (NEW CRATE)
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           ├── model.rs                (400 lines)
│           ├── storage.rs              (300 lines)
│           ├── detector.rs             (350 lines)
│           ├── impact.rs               (250 lines)
│           └── extractors/
│               ├── mod.rs              (100 lines)
│               ├── delta.rs            (200 lines)
│               ├── iceberg.rs          (200 lines)
│               └── hudi.rs             (200 lines)
│
├── python/statguardian/
│   ├── _lineage.py                     (250 lines, NEW)
│   ├── _lineage_sql.py                 (400 lines, NEW)
│   ├── _lineage_custom.py              (150 lines, NEW)
│   ├── _lineage_changes.py             (200 lines, NEW)
│   ├── _evolution.py                   (MODIFIED: integrate with lineage)
│   ├── _connectors.py                  (MODIFIED: pass lineage store)
│   └── __init__.py                     (MODIFIED: export lineage APIs)
│
├── tests/
│   ├── test_lineage_model.rs           (20 tests)
│   ├── test_lineage_extractors.rs      (25 tests)
│   ├── test_lineage_changes.rs         (25 tests)
│   └── test_lineage_integration.py     (10 tests)
│
├── examples/
│   ├── lineage_extraction.py           (NEW)
│   ├── lineage_change_detection.py     (NEW)
│   ├── lineage_impact_analysis.py      (NEW)
│   └── lineage_with_schema.py          (NEW)
│
└── docs/
    ├── LINEAGE_GUIDE.md                (NEW)
    ├── LINEAGE_EXTRACTION.md           (NEW)
    ├── API_REFERENCE_LINEAGE.md        (NEW)
    └── MIGRATION_V2_2.md               (NEW)
```

---

## Public API (What PyStreamMCP v0.3 Will Call)

### Lineage Extraction

```python
def get_lineage_graph(warehouse_config: Dict) -> LineageGraph
def get_lineage_version(warehouse_config: Dict, version: int = None) -> LineageVersion
def get_lineage_history(warehouse_config: Dict, table_id: str, limit: int = 10) -> List[LineageVersion]
```

### Change Detection

```python
def detect_lineage_changes(warehouse_config: Dict, from_version: int, to_version: int) -> List[LineageChange]
def get_change_summary(warehouse_config: Dict) -> ChangeReport
```

### Impact Analysis

```python
def get_impact_chain(warehouse_config: Dict, table_id: str) -> List[str]
def get_upstream_tables(warehouse_config: Dict, table_id: str) -> List[str]
def get_downstream_tables(warehouse_config: Dict, table_id: str) -> List[str]
def assess_change_impact(warehouse_config: Dict, change: LineageChange) -> ImpactReport
```

### Quality Through Lineage

```python
def get_quality_through_lineage(warehouse_config: Dict, table_id: str) -> float
def get_quality_degradation_chain(warehouse_config: Dict, table_id: str) -> Dict[str, float]
```

### Schema + Lineage Validation

```python
def validate_with_lineage(warehouse_config: Dict, table_id: str, contract: DataContract) -> ValidationReport
def detect_downstream_impact(warehouse_config: Dict, table_id: str, schema_change: SchemaChange) -> List[str]
```

---

## Testing Strategy

### Unit Tests (70 tests total)
- Week 1: 20 tests (model, storage)
- Week 2: 25 tests (extractors)
- Week 3: 25 tests (change detection, impact, integration)

### Integration Tests (10 tests)
- End-to-end workflows
- Multi-warehouse federation
- Performance benchmarks
- Backward compatibility

### Manual Testing
- Real Snowflake warehouse (SQL extraction)
- Real PostgreSQL database
- Real Delta Lake tables
- Real Iceberg tables
- Real Hudi tables
- Lineage visualization (graphviz output)

**Total:** 80 tests, 100% pass rate

---

## Success Criteria

### Correctness
✓ Lineage graph represents warehouse structure accurately  
✓ All table formats supported (Delta/Iceberg/Hudi/SQL)  
✓ Change detection catches 100% of dependency changes  
✓ Impact chains accurate (no false negatives/positives)  
✓ Quality propagation follows lineage correctly  

### Performance
✓ Extract lineage: <30 seconds for 1000-table warehouse  
✓ Change detection: <5 seconds  
✓ Impact chain: <100ms  
✓ Quality propagation: <50ms  
✓ No regression in existing validation performance  

### Integration
✓ Schema validator uses lineage context  
✓ Drift detector attributes sources via lineage  
✓ Quality scores propagate through lineage  
✓ All APIs work end-to-end  

### Safety
✓ Lineage versioning prevents data loss  
✓ Audit trail for all changes  
✓ Change severity accurately categorized  
✓ Backward compatible with v2.1  
✓ No breaking changes to existing APIs  

### User Impact
✓ Documentation clear and complete  
✓ Examples show real-world usage  
✓ Migration path from v2.1 smooth  
✓ PyStreamMCP can consume all APIs  

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Warehouse API changes | Adapter pattern + fallback extraction |
| Lineage extraction accuracy | Comprehensive test coverage, manual validation |
| Performance at scale | Benchmarking, caching strategies, sampling for large graphs |
| Change detection edge cases | Property-based testing, fuzz testing |
| Integration complexity | Clear separation of concerns, interfaces |

---

## Release Checklist

- [ ] All 80 tests passing (unit + integration)
- [ ] Performance benchmarks completed
- [ ] All warehouse formats tested
- [ ] Documentation reviewed
- [ ] Examples verified
- [ ] API stable and documented
- [ ] Version bumped to v2.2.0
- [ ] CHANGELOG updated
- [ ] GitHub release notes prepared
- [ ] PyPI package published
- [ ] Announce ready for PyStreamMCP v0.3 consumption

---

## Post-Release (v2.3 Roadmap)

### Phase 1: Lineage Intelligence (3 weeks)
- ML-based lineage inference (deduce missing lineage)
- Lineage quality scoring (confidence in extracted lineage)
- Cost propagation (cost of computation through chains)

### Phase 2: Advanced Features (4 weeks)
- dbt manifest parsing (native dbt lineage support)
- Fivetran lineage ingestion
- Custom connector framework
- Lineage visualization (graphviz, interactive)

### Phase 3: Predictive (4 weeks)
- Predictive lineage changes (ML model of change patterns)
- Anomaly detection in lineage graph
- Lineage-based cost forecasting

---

## Summary

**Timeline:** 4 weeks (2026-07-24 to 2026-08-21)  
**Code:** ~2500 lines new Rust + Python  
**Tests:** 80 total (70 unit + 10 integration)  
**Dependencies:** 0 new (uses existing Rust/Python ecosystems)  
**Impact:** Lineage foundation for PyStreamMCP v0.3  

**Status:** ✅ LOCKED & READY TO BUILD

### What PyStreamMCP v0.3 Gets

```python
from statguardian import get_lineage_graph, detect_lineage_changes

# Available after v2.2 release:
lineage = get_lineage_graph(warehouse_config)
# → Complete DAG of table transformations

changes = detect_lineage_changes(warehouse_config, v1=5, v2=6)
# → What changed in lineage between versions

impact = get_impact_chain(warehouse_config, "customers_raw")
# → All tables affected by changes to customers_raw
```

PyStreamMCP uses these APIs to:
1. Cache schemas with lineage awareness (cache invalidation is surgical)
2. Give agents lineage context (not just schema)
3. Optimize cost using transformation chains
4. Prune context intelligently (relevant transformation chains only)
