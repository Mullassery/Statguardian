# StatGuardian v3.0 — Streaming & Distributed Validation Roadmap

**Date:** 2026-07-17  
**Status:** LOCKED & READY TO BUILD  
**Timeline:** 6 weeks (2026-09-25 to 2026-11-06)  
**Target Release:** 2026-11-06  
**Dependency:** v2.2 (lineage APIs available), v2.3 (ML predictions available)  
**Blocking:** v4.0 (intelligent automation needs streaming foundation)

---

## Executive Overview

Transform StatGuardian from batch to streaming:
- Real-time validation (milliseconds latency)
- Distributed execution (scale to 100K+ events/sec)
- Quality propagation through lineage (immediate insights)
- Production-ready resilience (recovery, auto-scaling, checkpointing)

**Impact:** Move from "detect problems daily" to "prevent problems in real-time"

---

## Week-by-Week Breakdown

### WEEK 1: Stream Ingestion (Days 1-5)

**Goal:** Multi-source event ingestion (Kafka, S3, CDC)

**Components to Build:**

1. **rust/statguardian-streaming/src/sources.rs** (600 lines)
   - `StreamSource` trait (async iterator interface)
   - `KafkaSource` (async consumer, offset management)
   - `CloudStorageSource` (S3/GCS polling, file parsing)
   - `DatabaseCDCSource` (PostgreSQL logical decoding, MySQL binlog, MongoDB change streams)

2. **python/statguardian/_streaming_sources.py** (350 lines)
   - Python bindings for stream sources
   - Configuration loaders for each source type
   - Checkpoint management (for recovery)

3. **Integration tests** (150 lines)
   - Test with real Kafka cluster (Docker)
   - Test S3 polling
   - Test PostgreSQL CDC

**Tests:** 12 unit tests
- Kafka consumer functionality
- S3 file discovery and parsing
- PostgreSQL logical decoding
- MySQL binlog reading
- MongoDB change stream subscription
- Checkpoint persistence
- Event deserialization
- Partition key extraction
- Edge cases (empty topics, malformed events, source unavailable)

**Milestones:**
- ✅ Kafka source working (produce/consume)
- ✅ S3 polling working (new files detected)
- ✅ PostgreSQL CDC working (DML captured)
- ✅ All 12 tests passing

**Files Created:**
- `crates/statguardian-streaming/src/sources.rs`
- `crates/statguardian-streaming/Cargo.toml`
- `python/statguardian/_streaming_sources.py`
- `tests/test_streaming_sources.py`

---

### WEEK 2: Distributed Validator Core (Days 6-10)

**Goal:** Event validation pipeline with distributed worker coordination

**Components to Build:**

1. **rust/statguardian-streaming/src/validator.rs** (500 lines)
   - `ValidationWorker` struct (processes events, maintains local cache)
   - `DistributedValidator` coordinator (routes to workers, collects results)
   - Event routing by partition key (hash-based)
   - Result aggregation

2. **python/statguardian/_streaming_validator.py** (300 lines)
   - Python wrapper for Rust validator
   - Integration with contract manager
   - Result collection and emission

3. **State management** (200 lines)
   - Local cache per worker
   - Async state persistence (non-blocking)
   - State backend abstraction

**Tests:** 10 unit tests
- Event routing to correct worker
- Cache hits (fast path)
- Cache misses (slow path with state store fetch)
- Result aggregation
- Partition key hashing
- Multiple concurrent workers
- Contract loading
- Result formatting
- High throughput (stress test)
- Latency targets (<10ms)

**Milestones:**
- ✅ Events routed correctly (partition key hashing)
- ✅ Validation latency <10ms (hot path)
- ✅ Workers coordinated properly
- ✅ All 10 tests passing

**Files Created:**
- `crates/statguardian-streaming/src/validator.rs`
- `crates/statguardian-streaming/src/state.rs`
- `python/statguardian/_streaming_validator.py`
- `tests/test_streaming_validator.py`

---

### WEEK 3: Quality Propagation & Lineage (Days 11-15)

**Goal:** Real-time quality propagation through lineage graph

**Components to Build:**

1. **rust/statguardian-streaming/src/propagation.rs** (400 lines)
   - `QualityPropagator` struct
   - Lineage traversal (breadth-first)
   - Quality score calculation (direct × transfer factor)
   - SLA checking

2. **python/statguardian/_streaming_propagation.py** (250 lines)
   - Python quality propagation API
   - Result-to-quality conversion
   - Lineage integration with v2.2

3. **Database schema** (100 lines)
   - `streaming_quality_scores` table (timestamp, table_id, quality, violations)
   - `propagated_quality` table (source → target quality flow)
   - Indices for fast queries

4. **Real-time metrics** (50 lines)
   - Expose quality metrics to Prometheus
   - Quality timeline per table

**Tests:** 8 unit tests
- Quality propagation through linear chain (A→B→C)
- Quality propagation through fan-out (A→[B,C,D])
- Quality propagation through fan-in ([A,B]→C)
- Transfer factor application (0.95x per hop)
- SLA violation detection
- Effective quality calculation (min of direct + propagated)
- Metrics emission
- Edge cases (missing upstream, quality = 0)

**Milestones:**
- ✅ Quality propagates correctly through lineage
- ✅ SLA violations detected (alerts sent)
- ✅ Effective quality accurate
- ✅ All 8 tests passing

**Files Created:**
- `crates/statguardian-streaming/src/propagation.rs`
- `python/statguardian/_streaming_propagation.py`
- Database schema SQL
- `tests/test_streaming_propagation.py`

---

### WEEK 4: State Management & Checkpointing (Days 16-20)

**Goal:** Reliable state management with recovery capabilities

**Components to Build:**

1. **rust/statguardian-streaming/src/checkpoint.rs** (400 lines)
   - `StatefulValidator` (processes events with state tracking)
   - `Checkpoint` (event offset, timestamp, state digest)
   - Checkpoint storage (RocksDB, Redis, PostgreSQL backends)
   - Periodic flushing (every N events)

2. **python/statguardian/_streaming_state.py** (200 lines)
   - State backend abstraction
   - RocksDB implementation
   - Redis implementation
   - PostgreSQL implementation

3. **Recovery logic** (150 lines)
   - Load from latest checkpoint
   - Replay events from offset
   - State consistency verification

**Tests:** 10 unit tests
- State save/restore
- Checkpoint creation
- Checkpoint recovery (resume from offset)
- Multiple checkpoint versions
- State consistency
- RocksDB backend
- Redis backend
- PostgreSQL backend
- Stress test (many checkpoints)
- Recovery after crash simulation

**Milestones:**
- ✅ State persistence working
- ✅ Recovery from checkpoint (resume correctly)
- ✅ No data loss (exactly-once semantics)
- ✅ All 10 tests passing

**Files Created:**
- `crates/statguardian-streaming/src/checkpoint.rs`
- `crates/statguardian-streaming/src/state_backends/mod.rs`
- `crates/statguardian-streaming/src/state_backends/rocksdb.rs`
- `python/statguardian/_streaming_state.py`
- `tests/test_streaming_checkpoint.py`

---

### WEEK 5: Resilience & Scaling (Days 21-25)

**Goal:** Automatic recovery, load balancing, Kubernetes integration

**Components to Build:**

1. **rust/statguardian-streaming/src/resilience.rs** (300 lines)
   - `CircuitBreaker` (prevent cascading failures)
   - `RetryPolicy` (exponential backoff)
   - `Bulkhead` (isolation between workers)
   - Failure recovery strategies

2. **Kubernetes integration** (200 lines)
   - Deployment manifest (auto-scaling)
   - HorizontalPodAutoscaler (scale based on metrics)
   - Health checks (liveness, readiness)
   - Graceful shutdown

3. **python/statguardian/_kubernetes.py** (150 lines)
   - Python Kubernetes client
   - Auto-scaling logic (events/sec → worker count)
   - Monitoring integration

4. **Metrics & monitoring** (100 lines)
   - Prometheus exports (events/sec, latency, errors)
   - Grafana dashboards (throughput, latency, errors)
   - Alert rules (high latency, error rate)

**Tests:** 8 unit tests
- Circuit breaker state transitions
- Failure detection
- Recovery after failures
- Retry logic with backoff
- Bulkhead isolation
- Kubernetes scaling calculation
- Metrics emission
- High load handling

**Milestones:**
- ✅ Circuit breaker working (fail-fast on errors)
- ✅ Auto-scaling working (scales to match throughput)
- ✅ Recovery from failures (self-healing)
- ✅ All 8 tests passing

**Files Created:**
- `crates/statguardian-streaming/src/resilience.rs`
- `python/statguardian/_kubernetes.py`
- `k8s/deployment.yaml`
- `k8s/hpa.yaml`
- `k8s/servicemonitor.yaml`
- `tests/test_streaming_resilience.py`

---

### WEEK 6: Integration & Release (Days 26-30)

**Goal:** Complete v3.0.0 release with documentation

**Components to Build:**

1. **End-to-end integration** (200 lines)
   - Stream → Validator → Propagation pipeline
   - Multiple concurrent sources
   - Result emission to multiple sinks (lake, alerts, metrics)

2. **CLI commands** (150 lines)
   - `statguardian stream start` (start streaming validator)
   - `statguardian stream config` (show/update config)
   - `statguardian stream metrics` (show real-time metrics)

3. **Documentation** (10 docs)
   - STREAMING_QUICKSTART.md
   - STREAMING_ARCHITECTURE.md
   - KAFKA_SETUP.md
   - CDC_SETUP.md
   - KUBERNETES_DEPLOYMENT.md
   - MONITORING.md
   - TROUBLESHOOTING.md
   - MIGRATION_V2_TO_V3.md
   - API_REFERENCE_STREAMING.md
   - PERFORMANCE_TUNING.md

4. **Integration tests** (7 tests)
   - End-to-end Kafka → validation → propagation
   - S3 polling → validation
   - CDC → validation
   - Multiple concurrent tables
   - Performance benchmarks
   - Failure recovery workflow
   - Kubernetes deployment

5. **Release preparation**
   - Version bump to v3.0.0
   - CHANGELOG.md
   - GitHub release notes
   - Migration guide (v2→v3)
   - Breaking changes documentation
   - PyPI publishing

**Tests:** 7 integration tests
- Full streaming pipeline
- Multiple event sources concurrently
- Quality propagation end-to-end
- Kubernetes deployment verification
- Performance benchmarks
- Recovery scenario
- Load testing (ramp up to 100K events/sec)

**Milestones:**
- ✅ All 55 tests passing (12+10+8+10+8+7)
- ✅ Documentation complete
- ✅ Performance targets met (<100ms latency)
- ✅ v3.0.0 released to PyPI

**Files Modified:**
- `Cargo.toml` (version bump)
- `python/statguardian/__init__.py` (version bump)
- `CHANGELOG.md`
- `README.md`

---

## Directory Structure

```
statguardian/
├── crates/
│   └── statguardian-streaming/         (NEW CRATE)
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           ├── sources.rs              (600 lines)
│           ├── validator.rs            (500 lines)
│           ├── propagation.rs          (400 lines)
│           ├── checkpoint.rs           (400 lines)
│           ├── state.rs                (200 lines)
│           ├── state_backends/
│           │   ├── mod.rs
│           │   ├── rocksdb.rs
│           │   ├── redis.rs
│           │   └── postgres.rs
│           ├── resilience.rs           (300 lines)
│           └── metrics.rs              (100 lines)
│
├── python/statguardian/
│   ├── _streaming_sources.py           (350 lines, NEW)
│   ├── _streaming_validator.py         (300 lines, NEW)
│   ├── _streaming_propagation.py       (250 lines, NEW)
│   ├── _streaming_state.py             (200 lines, NEW)
│   ├── _kubernetes.py                  (150 lines, NEW)
│   └── _cli.py                         (MODIFIED: add stream commands)
│
├── tests/
│   ├── test_streaming_sources.py       (12 tests, NEW)
│   ├── test_streaming_validator.py     (10 tests, NEW)
│   ├── test_streaming_propagation.py   (8 tests, NEW)
│   ├── test_streaming_checkpoint.py    (10 tests, NEW)
│   ├── test_streaming_resilience.py    (8 tests, NEW)
│   └── test_streaming_integration.py   (7 tests, NEW)
│
├── k8s/                                (NEW DIRECTORY)
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   ├── servicemonitor.yaml
│   └── configmap.yaml
│
└── docs/
    ├── STREAMING_QUICKSTART.md         (NEW)
    ├── STREAMING_ARCHITECTURE.md       (NEW)
    ├── KAFKA_SETUP.md                  (NEW)
    ├── CDC_SETUP.md                    (NEW)
    ├── KUBERNETES_DEPLOYMENT.md        (NEW)
    ├── MONITORING.md                   (NEW)
    ├── TROUBLESHOOTING.md              (NEW)
    └── MIGRATION_V2_TO_V3.md           (NEW)
```

---

## Public API (Available in v3.0)

### Stream Configuration

```python
from statguardian import StreamValidator, KafkaSource, CloudStorageSource

# Kafka-based streaming
kafka_source = KafkaSource(
    brokers=['kafka-1:9092', 'kafka-2:9092'],
    topic='raw_data_events',
    group_id='statguardian',
)

validator = StreamValidator(
    sources=[kafka_source],
    contract_manager=contract_mgr,
    num_workers=4,
    state_backend='rocksdb',
    checkpoint_interval=10000,
)

await validator.start()
```

### Quality Monitoring

```python
from statguardian import QualityMonitor

monitor = QualityMonitor()

# Get current quality for table
quality = await monitor.get_quality('customers_enriched')
print(f"Direct: {quality['direct']:.1%}")
print(f"Effective (with upstream): {quality['effective']:.1%}")

# Get quality timeline
history = await monitor.get_quality_timeline(
    table='orders',
    hours=24,
)
# → [(timestamp1, 0.98), (timestamp2, 0.97), ...]

# Check SLA compliance
sla = await monitor.get_sla('shipments')
if quality['effective'] < sla.minimum:
    await alert_manager.send_critical(
        f"Quality SLA violated: {quality['effective']:.1%} < {sla.minimum:.1%}"
    )
```

### CLI Commands

```bash
# Start streaming validator
$ statguardian stream start \
    --config validator-config.yaml \
    --workers 4 \
    --state-backend rocksdb

# View real-time metrics
$ statguardian stream metrics
Throughput: 12,345 events/sec
Latency (p99): 8.2ms
Errors: 0
Quality scores (live):
  customers_enriched: 0.98
  orders_enriched: 0.96
  shipments: 0.94

# Check quality SLA
$ statguardian quality check --table customers_enriched
✅ Quality: 0.98 (SLA: 0.95)
✅ No violations

# View lineage propagation
$ statguardian lineage propagate --from customers_raw
customers_raw (0.98)
  → customers_cleaned (0.93)
    → customers_enriched (0.88)
      → customer_metrics (0.83)

# Adjust quality thresholds
$ statguardian quality threshold --table orders --set 0.92
Updated quality SLA for orders: 0.92
```

---

## Testing Strategy

### Unit Tests (55 total)

| Component | Tests | Focus |
|-----------|-------|-------|
| Stream Ingestion | 12 | Multi-source support, CDC, checkpointing |
| Validator Core | 10 | Event routing, latency, caching |
| Quality Propagation | 8 | Lineage traversal, SLA checking |
| State Management | 10 | Persistence, recovery, backends |
| Resilience | 8 | Failures, recovery, scaling |
| Integration | 7 | End-to-end workflows, performance |

### Load Testing

```bash
# Simulate 100K events/sec
$ statguardian load-test \
    --rate 100000 \
    --duration 600 \
    --table customers

Results:
  Throughput: 99,847 events/sec (target: 100K)
  Latency (p50): 3.2ms
  Latency (p99): 8.7ms
  Errors: 0
  ✅ PASS
```

---

## Success Criteria

### Correctness
✓ Event validation latency <100ms (p99)  
✓ No missed events (exactly-once semantics)  
✓ Quality propagation accurate  
✓ Recovery from failures (resume without data loss)  

### Performance
✓ Throughput: 100K+ events/sec  
✓ Checkpoint latency: <1sec per 10K events  
✓ Recovery time: <5 minutes  
✓ Memory: <2GB per worker  

### Reliability
✓ 99.99% availability  
✓ Auto-recovery from worker failures  
✓ Graceful degradation under load  
✓ Event replay capability (7-day retention)  

---

## Deployment Checklist

- [ ] Stream source selected (Kafka/S3/CDC)
- [ ] Contracts configured in StatGuardian
- [ ] Kubernetes cluster ready
- [ ] Storage backend configured (RocksDB/Redis/PostgreSQL)
- [ ] Prometheus/Grafana for monitoring
- [ ] Alert manager configured (Slack/PagerDuty)
- [ ] All 55 tests passing
- [ ] Performance benchmarks met
- [ ] Documentation reviewed
- [ ] Migration plan (v2→v3) documented
- [ ] Version bumped to v3.0.0
- [ ] CHANGELOG.md updated
- [ ] GitHub release notes prepared
- [ ] PyPI package published

---

## Cost & Scaling

### Compute Requirements

```
Events/sec    Workers    CPU    Memory    Storage/day
10K           2         4c     8GB       50GB
50K           4         8c     16GB      250GB
100K          8         16c    32GB      500GB
500K          16        32c    64GB      2.5TB
1M            32        64c    128GB     5TB
```

### Storage Costs (CloudSQL/S3)

```
Retention     Events/day    Storage    Monthly Cost
7 days        86.4B         2TB        $100
30 days       86.4B         8.6TB      $430
90 days       86.4B         25.8TB     $1,290
```

---

## Migration Path (v2 → v3)

### Phase 1: Parallel Setup (Week 1)
- Deploy v3.0 streaming validator alongside v2.2 batch
- Configure stream sources (Kafka/S3)
- Run in dry-run mode (no alerts)

### Phase 2: Validation (Week 2)
- Compare batch vs streaming results
- Calibrate quality thresholds
- Train ops team on new metrics

### Phase 3: Cutover (Week 3)
- Switch alerts from batch to streaming
- Decommission batch validation
- Monitor 24/7 for regressions

### Phase 4: Optimization (Week 4+)
- Tune worker count for throughput
- Optimize state backend performance
- Adjust SLA thresholds based on data

---

## Summary

**v3.0 enables real-time data quality at scale:**
- Validate as data arrives (milliseconds)
- Propagate quality through lineage (immediate insights)
- Scale horizontally (Kubernetes)
- Recover from failures (exactly-once semantics)
- Support streaming pipelines (Kafka, S3, CDC)

**Timeline:** 6 weeks  
**Code:** 2,400 lines (Rust + Python)  
**Tests:** 55 unit + 7 integration  
**Status:** ✅ LOCKED & READY TO BUILD

**Next:** v4.0 (Intelligent Automation) depends on v3.0 streaming foundation
