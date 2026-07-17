# StatGuardian v3.0 — Streaming & Distributed Validation

**Date:** 2026-07-17  
**Status:** ARCHITECTURE DESIGN (LOCKED)  
**Timeline:** 6 weeks (2026-09-25 to 2026-11-06)  
**Target Release:** 2026-11-06  
**Priority:** HIGH (Foundation for continuous data quality)  
**Vision:** Real-time validation at scale — catch quality issues before they propagate

---

## Executive Overview

Move from batch validation (daily/hourly snapshots) to streaming validation (continuous):
- **Real-time validation:** Validate data as it arrives (milliseconds latency)
- **Distributed execution:** Process validation across multiple nodes
- **Scalable architecture:** Handle 100K+ events/second
- **Quality propagation:** Quality scores flow through lineage in real-time
- **Cost optimized:** Process only changed data (delta validation)

**Impact:**
- Detect data quality issues in **minutes**, not hours/days
- Enable SLA-based remediation (catch issues before user impact)
- Support streaming ETL/ELT pipelines
- Enable real-time data contracts

---

## Architecture: Four Layers

### Layer 1: Stream Ingestion (Event Sources)

**Problem:** Data quality validation was batch-only; real-time pipelines had no quality feedback

**Solution:** Pluggable stream sources → Unified validation pipeline

```python
class StreamSource(ABC):
    """Abstract interface for event streams"""
    
    async def connect(self) -> AsyncIterator[DataEvent]:
        """Connect to stream, yield events"""
        pass
    
    async def checkpoint(self, event_id: str) -> None:
        """Persist processing progress (for recovery)"""
        pass


class KafkaSource(StreamSource):
    """Read from Kafka topics"""
    
    def __init__(self, brokers: List[str], topic: str):
        self.brokers = brokers
        self.topic = topic
        self.consumer = None
    
    async def connect(self) -> AsyncIterator[DataEvent]:
        """Subscribe to topic, yield events"""
        
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.brokers,
            auto_offset_reset='earliest',
            group_id='statguardian_validator',
        )
        
        await self.consumer.start()
        
        try:
            async for msg in self.consumer:
                yield DataEvent(
                    source='kafka',
                    topic=self.topic,
                    key=msg.key,
                    value=json.loads(msg.value),
                    timestamp=msg.timestamp,
                )
        finally:
            await self.consumer.stop()
    
    async def checkpoint(self, event_id: str) -> None:
        """Save offset"""
        await self.consumer.commit()


class CloudStorageSource(StreamSource):
    """Read from cloud storage (S3, GCS, etc.)"""
    
    def __init__(self, bucket: str, prefix: str, poll_interval_sec: int = 60):
        self.bucket = bucket
        self.prefix = prefix
        self.poll_interval = poll_interval_sec
        self.client = None
    
    async def connect(self) -> AsyncIterator[DataEvent]:
        """Poll for new files, yield rows as events"""
        
        seen_files = set()
        
        while True:
            # List new files
            objects = await self.client.list_objects(
                Bucket=self.bucket,
                Prefix=self.prefix,
            )
            
            for obj in objects.get('Contents', []):
                key = obj['Key']
                
                if key in seen_files:
                    continue
                
                seen_files.add(key)
                
                # Download and parse file
                body = await self.client.get_object(Bucket=self.bucket, Key=key)
                
                for row in parse_file(body):
                    yield DataEvent(
                        source='cloud_storage',
                        bucket=self.bucket,
                        key=key,
                        value=row,
                        timestamp=datetime.now(),
                    )
            
            await asyncio.sleep(self.poll_interval)


class DatabaseChangeStreamSource(StreamSource):
    """Read from database change streams (CDC)"""
    
    def __init__(self, db_config: Dict, table: str):
        self.config = db_config
        self.table = table
        self.conn = None
    
    async def connect(self) -> AsyncIterator[DataEvent]:
        """Subscribe to CDC stream"""
        
        # Database-specific CDC
        if self.config['type'] == 'postgres':
            async for event in self._postgres_logical_decoding():
                yield event
        elif self.config['type'] == 'mysql':
            async for event in self._mysql_binlog():
                yield event
        elif self.config['type'] == 'mongodb':
            async for event in self._mongodb_change_stream():
                yield event
    
    async def _postgres_logical_decoding(self) -> AsyncIterator[DataEvent]:
        """PostgreSQL logical decoding via replication slot"""
        
        async with await asyncpg.connect(**self.config) as conn:
            await conn.execute(
                f"CREATE PUBLICATION IF NOT EXISTS sg_pub FOR TABLE {self.table}"
            )
            
            slot_name = f"sg_slot_{self.table}"
            
            async for message in conn.cursor(
                f"SELECT data FROM pg_logical_slot_get_changes('{slot_name}', NULL, NULL)"
            ):
                event = parse_wal_record(message['data'])
                
                yield DataEvent(
                    source='postgres_cdc',
                    table=self.table,
                    operation=event.operation,  # INSERT/UPDATE/DELETE
                    value=event.data,
                    timestamp=event.timestamp,
                )
```

---

### Layer 2: Distributed Validation Engine

**Problem:** Batch validation took minutes/hours; need sub-second latency at scale

**Solution:** Distributed validation with local state + periodic sync

```python
class ValidationWorker:
    """
    Independent validator that processes events
    Can run on any node in cluster
    """
    
    def __init__(self, 
                 worker_id: str, 
                 contracts: Dict[str, DataContract],
                 state_store: StateStore):
        self.worker_id = worker_id
        self.contracts = contracts
        self.state_store = state_store
        self.local_cache = {}  # Per-worker cache of recent state
    
    async def validate_event(self, event: DataEvent) -> ValidationResult:
        """
        Validate single event against contract
        Latency target: <10ms
        """
        
        # 1. Route to correct contract
        table_id = event.table_id
        contract = self.contracts.get(table_id)
        
        if not contract:
            # Unknown table - log and skip
            return ValidationResult(
                event_id=event.id,
                status='UNKNOWN_TABLE',
                passed=False,
                reason=f"No contract for {table_id}",
            )
        
        # 2. Check local cache first (hot path)
        cache_key = f"{table_id}:{event.partition_key}"
        
        if cache_key in self.local_cache:
            last_state = self.local_cache[cache_key]
        else:
            # 3. Fetch from state store if not cached
            last_state = await self.state_store.get_row_state(
                table_id, 
                event.partition_key
            )
            self.local_cache[cache_key] = last_state
        
        # 4. Validate event
        violations = []
        
        for rule in contract.rules:
            if not rule.evaluate(event.value, last_state):
                violations.append(ValidationViolation(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    reason=rule.explain_failure(event.value, last_state),
                ))
        
        result = ValidationResult(
            event_id=event.id,
            table_id=table_id,
            worker_id=self.worker_id,
            timestamp=datetime.now(),
            passed=len(violations) == 0,
            violations=violations,
        )
        
        # 5. Update local state
        self.local_cache[cache_key] = event.value
        
        # 6. Async: persist to state store (doesn't block)
        asyncio.create_task(
            self.state_store.set_row_state(table_id, event.partition_key, event.value)
        )
        
        return result


class DistributedValidator:
    """
    Orchestrates validation across multiple workers
    Handles worker failure, rebalancing, scaling
    """
    
    def __init__(self, 
                 num_workers: int = 4,
                 state_store: StateStore = None):
        self.workers = [
            ValidationWorker(f"worker-{i}", contracts={}, state_store=state_store)
            for i in range(num_workers)
        ]
        self.event_queue = asyncio.Queue(maxsize=10000)
        self.result_queue = asyncio.Queue()
        self.worker_assignments = {}  # table → worker mapping
    
    async def start(self, stream_source: StreamSource, contract_manager: ContractManager):
        """Start validation pipeline"""
        
        # Load contracts into all workers
        for worker in self.workers:
            worker.contracts = await contract_manager.load_all()
        
        # Start 3 concurrent tasks:
        # 1. Read from stream
        # 2. Distribute events to workers (load-balanced)
        # 3. Collect results
        
        tasks = [
            asyncio.create_task(self._consume_stream(stream_source)),
            asyncio.create_task(self._distribute_events()),
            asyncio.create_task(self._collect_results()),
        ]
        
        await asyncio.gather(*tasks)
    
    async def _consume_stream(self, source: StreamSource):
        """Read events from source, add to queue"""
        
        async for event in source.connect():
            await self.event_queue.put(event)
            
            # Periodic checkpoint for recovery
            if event.sequence_number % 10000 == 0:
                await source.checkpoint(event.id)
    
    async def _distribute_events(self):
        """Route events to workers (partitioned by key)"""
        
        while True:
            event = await self.event_queue.get()
            
            # Hash by partition key to ensure consistent routing
            # (same key always goes to same worker = better cache locality)
            partition_key = event.partition_key or event.id
            worker_idx = hash(partition_key) % len(self.workers)
            
            worker = self.workers[worker_idx]
            
            # Validate (non-blocking)
            result = await worker.validate_event(event)
            
            # Queue result for emission
            await self.result_queue.put(result)
    
    async def _collect_results(self):
        """Emit validation results (to data lake, alerting, etc.)"""
        
        while True:
            result = await self.result_queue.get()
            
            # Emit to multiple sinks
            await asyncio.gather(
                self._emit_to_lake(result),
                self._check_alerts(result),
                self._update_metrics(result),
            )
    
    async def _emit_to_lake(self, result: ValidationResult):
        """Write result to data lake for analysis"""
        
        # Partitioned by date/table for efficient querying
        partition = f"table={result.table_id}/date={result.timestamp.date()}"
        
        await self.lake_writer.write(
            path=f"validation_results/{partition}/",
            data=result.to_dict(),
        )
    
    async def _check_alerts(self, result: ValidationResult):
        """Emit alerts for failures"""
        
        if not result.passed:
            await self.alert_manager.send(
                severity='warning' if len(result.violations) == 1 else 'critical',
                message=f"Validation failed for {result.table_id}: {result.violations[0].reason}",
                table_id=result.table_id,
                event_id=result.event_id,
            )
    
    async def _update_metrics(self, result: ValidationResult):
        """Update quality metrics (async)"""
        
        metrics = {
            'validation_timestamp': result.timestamp,
            'table_id': result.table_id,
            'event_id': result.event_id,
            'passed': result.passed,
            'violation_count': len(result.violations),
            'violation_types': [v.rule_name for v in result.violations],
        }
        
        await self.metrics_store.record(metrics)
```

---

### Layer 3: Lineage & Quality Propagation

**Problem:** Quality issues in upstream table invisible to downstream consumers

**Solution:** Real-time quality propagation through lineage

```python
class QualityPropagator:
    """
    Propagate quality scores through lineage in real-time
    """
    
    def __init__(self, 
                 lineage_graph: LineageGraph,
                 quality_store: QualityStore):
        self.lineage = lineage_graph
        self.quality_store = quality_store
        self.propagation_cache = {}  # Cache impact chains
    
    async def on_validation_result(self, result: ValidationResult):
        """
        When validation result comes in, update quality and propagate
        """
        
        table_id = result.table_id
        quality_score = 1.0 if result.passed else 0.0
        
        # 1. Save quality score
        await self.quality_store.record_quality(
            table_id=table_id,
            quality=quality_score,
            violations=result.violations,
            timestamp=result.timestamp,
        )
        
        # 2. Propagate to downstream tables
        downstream = self.lineage.get_downstream(table_id)
        
        for downstream_table in downstream:
            # Propagated quality = upstream quality × lineage transfer score
            transfer_score = 0.95  # Assume 95% quality transfer (5% improvement in transformation)
            propagated_quality = quality_score * transfer_score
            
            await self.quality_store.record_propagated_quality(
                table_id=downstream_table,
                source_table=table_id,
                quality=propagated_quality,
                timestamp=result.timestamp,
            )
        
        # 3. Check SLAs
        await self._check_sla_violations(table_id, quality_score)
    
    async def _check_sla_violations(self, table_id: str, quality: float):
        """Check if quality SLA is violated"""
        
        sla = await self.quality_store.get_sla(table_id)
        
        if not sla:
            return
        
        if quality < sla.minimum_quality:
            # SLA violated!
            await self.alert_manager.send_critical(
                f"Quality SLA violated for {table_id}: {quality:.1%} < {sla.minimum_quality:.1%}",
                table_id=table_id,
                quality=quality,
                sla_requirement=sla.minimum_quality,
            )
    
    async def get_propagated_quality(self, table_id: str) -> Dict[str, float]:
        """
        Get quality score for table considering all upstream dependencies
        
        Returns: {
            'direct': 0.98,  # Quality of this table
            'propagated_from_upstream': 0.92,  # Worst upstream quality
            'effective': 0.90,  # Minimum of direct + propagated
        }
        """
        
        direct_quality = await self.quality_store.get_quality(table_id)
        upstream = self.lineage.get_upstream(table_id)
        
        propagated_qualities = []
        
        for upstream_table in upstream:
            upstream_quality = await self.quality_store.get_quality(upstream_table)
            transfer_score = 0.95
            propagated = upstream_quality * transfer_score
            propagated_qualities.append(propagated)
        
        propagated_worst = min(propagated_qualities) if propagated_qualities else 1.0
        
        return {
            'direct': direct_quality,
            'propagated_from_upstream': propagated_worst,
            'effective': min(direct_quality, propagated_worst),
        }
```

---

### Layer 4: Scalability & Resilience

**Problem:** Single validator node = bottleneck; no recovery from failures

**Solution:** Distributed system with checkpointing, load balancing, auto-scaling

```python
class StatefulValidator:
    """
    Stateful validator with checkpointing for recovery
    """
    
    def __init__(self, 
                 state_backend: StateBackend,  # RocksDB, Redis, etc.
                 checkpoint_interval: int = 10000):  # Checkpoint every N events
        self.state = state_backend
        self.checkpoint_interval = checkpoint_interval
        self.event_counter = 0
    
    async def process_event(self, event: DataEvent) -> ValidationResult:
        """Process with state management"""
        
        # 1. Process event
        result = await self._validate(event)
        
        # 2. Update state
        await self.state.put(f"row:{event.table_id}:{event.partition_key}", event.value)
        
        # 3. Periodic checkpoint
        self.event_counter += 1
        if self.event_counter % self.checkpoint_interval == 0:
            await self._checkpoint()
        
        return result
    
    async def _checkpoint(self):
        """Save checkpoint for recovery"""
        
        checkpoint_id = f"checkpoint-{datetime.now().isoformat()}"
        
        # Flush state to persistent storage
        await self.state.flush(checkpoint_id)
        
        # Save metadata for recovery
        await self.checkpoint_store.save(
            checkpoint_id=checkpoint_id,
            event_offset=self.event_counter,
            timestamp=datetime.now(),
        )


class KubernetesValidator:
    """
    Kubernetes-native validator with auto-scaling
    """
    
    def __init__(self, namespace: str = "default"):
        self.k8s_client = kubernetes.client.AppsV1Api()
        self.namespace = namespace
    
    async def scale_to_throughput(self, target_throughput: int):
        """
        Auto-scale validator based on throughput requirements
        
        Calculates: required_workers = target_throughput / events_per_worker_per_sec
        """
        
        # Each worker can handle ~1000 events/sec
        events_per_worker = 1000
        
        required_workers = max(1, target_throughput // events_per_worker)
        
        # Update deployment replica count
        deployment = await self.k8s_client.read_namespaced_deployment(
            name="statguardian-validator",
            namespace=self.namespace,
        )
        
        deployment.spec.replicas = required_workers
        
        await self.k8s_client.patch_namespaced_deployment(
            name="statguardian-validator",
            namespace=self.namespace,
            body=deployment,
        )
        
        print(f"Scaled validator to {required_workers} replicas")


class CircuitBreaker:
    """
    Prevent cascading failures when downstream is slow
    """
    
    def __init__(self, failure_threshold: int = 100, timeout_sec: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout_sec
        self.failure_count = 0
        self.state = 'CLOSED'  # CLOSED (normal) → OPEN (fail-fast) → HALF_OPEN (recovering)
    
    async def call(self, fn, *args, **kwargs):
        """
        Call function with circuit breaker protection
        """
        
        if self.state == 'OPEN':
            # Circuit is broken - fail fast
            raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = await fn(*args, **kwargs)
            
            if self.state == 'HALF_OPEN':
                # Recovery successful
                self.state = 'CLOSED'
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            self.failure_count += 1
            
            if self.failure_count >= self.failure_threshold:
                # Too many failures - open circuit
                self.state = 'OPEN'
                asyncio.create_task(self._recover_after_timeout())
            
            raise
    
    async def _recover_after_timeout(self):
        """Try to recover after timeout"""
        
        await asyncio.sleep(self.timeout)
        self.state = 'HALF_OPEN'
        self.failure_count = 0
```

---

## System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ STREAM SOURCES                                               │
│                                                              │
│ ├─ Kafka (pub/sub)                                          │
│ ├─ S3/GCS (cloud storage polling)                           │
│ ├─ PostgreSQL (CDC via logical decoding)                    │
│ ├─ MySQL (CDC via binlog)                                  │
│ └─ MongoDB (change streams)                                 │
└─────────────────┬──────────────────────────────────────────┘
                  │ (Events)
                  ▼
┌──────────────────────────────────────────────────────────────┐
│ EVENT QUEUE (Kafka/Pulsar)                                   │
│ ├─ Partitioned by table ID (for ordering)                    │
│ ├─ Retention: 7 days (replay on validation failure)         │
│ └─ Throughput: 100K+ events/sec                             │
└─────────────────┬──────────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────────────────┐
│ DISTRIBUTED VALIDATORS (Kubernetes)                          │
│                                                              │
│ ┌─────────────┬─────────────┬─────────────┐                │
│ │  Worker-1   │  Worker-2   │  Worker-N   │ (Auto-scaled)  │
│ │             │             │             │                │
│ │ Contract:   │ Contract:   │ Contract:   │                │
│ │ customers   │ orders      │ shipments   │                │
│ │             │             │             │                │
│ │ LocalCache  │ LocalCache  │ LocalCache  │                │
│ └──────┬──────┴──────┬──────┴──────┬──────┘                │
│        │ (Validation Results)      │                        │
└────────┼─────────────────────────┼─────────────────────────┘
         │                         │
         ▼                         ▼
┌──────────────────┐     ┌──────────────────┐
│ Quality Store    │     │ Result Lake      │
│ (Time-series)    │     │ (Data Lake)      │
└────────┬─────────┘     └──────┬───────────┘
         │                      │
         ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│ QUALITY PROPAGATION                                          │
│                                                              │
│ Lineage Graph:                                              │
│   raw_orders → cleaned_orders → enhanced_orders             │
│   ↓ quality   ↓ quality        ↓ quality                    │
│   0.98        0.96             0.93 (propagated)           │
│                                                              │
│ Effective Quality = MIN(direct, propagated_from_upstream)  │
└────────────────────┬─────────────────────────────────────┬──┘
                     │                                     │
                     ▼                                     ▼
            ┌──────────────────┐           ┌────────────────────┐
            │ SLA Monitoring   │           │ Alert Manager      │
            │ (Quality < SLA?) │           │ (Slack/PagerDuty)  │
            └──────────────────┘           └────────────────────┘
```

---

## Comparison: Batch vs Streaming

| Aspect | Batch (v2.2) | Streaming (v3.0) |
|--------|--------------|-----------------|
| Validation Latency | Hours/minutes | <100ms |
| Data Freshness | Stale (snapshot) | Real-time |
| Quality Visibility | Delayed | Immediate |
| Remediation Time | Hours to days | Minutes |
| Cost | Fixed (daily runs) | Variable (event-based) |
| Scale | 1M rows/run | 100K+ events/sec |
| State Management | Snapshot only | Streaming state |
| Lineage Updates | Batch sync | Real-time propagation |

---

## Deployment Scenarios

### Scenario 1: Kafka-based (Recommended)

```yaml
# Kafka topic setup
topics:
  - name: raw_data_events
    partitions: 32  # One per table shard
    retention: 7d
  - name: validation_results
    partitions: 16
    retention: 30d

# Validator deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: statguardian-validator
  namespace: data-quality
spec:
  replicas: 4  # Auto-scales based on lag
  selector:
    matchLabels:
      app: statguardian-validator
  template:
    metadata:
      labels:
        app: statguardian-validator
    spec:
      containers:
      - name: validator
        image: statguardian:v3.0
        env:
        - name: KAFKA_BROKERS
          value: "kafka-1:9092,kafka-2:9092,kafka-3:9092"
        - name: INPUT_TOPIC
          value: "raw_data_events"
        - name: OUTPUT_TOPIC
          value: "validation_results"
        - name: STATE_BACKEND
          value: "rocksdb"
        - name: NUM_WORKERS
          value: "4"
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
```

### Scenario 2: Cloud Storage (S3/GCS)

```yaml
# Poll S3 for new parquet/delta files
source:
  type: s3
  bucket: my-data-lake
  prefix: raw/
  poll_interval_sec: 60
  format: parquet
  
output:
  type: bigquery
  project: my-gcp-project
  dataset: data_quality
  table: validation_results
```

### Scenario 3: Database CDC (MySQL/PostgreSQL)

```yaml
# Logical decoding for PostgreSQL
source:
  type: postgres_cdc
  host: postgres.internal
  database: analytics
  tables:
    - customers
    - orders
    - products
  replication_slot: statguardian_slot

validator:
  contracts:
    customers: /contracts/customers.yaml
    orders: /contracts/orders.yaml
```

---

## Success Criteria

### Correctness
✓ Validation latency <100ms (p99)  
✓ No missed events (exactly-once semantics)  
✓ Quality scores consistent across workers  
✓ Lineage propagation accurate  

### Performance
✓ Throughput: 100K+ events/sec per validator cluster  
✓ Checkpoint latency: <1sec per 10K events  
✓ Recovery time: <5 minutes  
✓ Memory: <2GB per worker  

### Reliability
✓ 99.99% availability  
✓ Auto-recovery from worker failures  
✓ Graceful degradation under load  
✓ Event replay capability  

---

## Week-by-Week Breakdown (6 weeks)

| Week | Component | Lines | Tests | Output |
|------|-----------|-------|-------|--------|
| 1 | Stream sources (Kafka/S3/CDC) | 600 | 12 | Multi-source ingestion |
| 2 | Distributed validator core | 500 | 10 | Event validation pipeline |
| 3 | Quality propagation + lineage | 400 | 8 | Real-time quality flow |
| 4 | State management + checkpointing | 400 | 10 | Distributed state |
| 5 | Resilience + scaling | 300 | 8 | Circuit breakers, K8s |
| 6 | Integration + release | 200 | 7 | v3.0.0 + documentation |
| **TOTAL** | **v3.0** | **2,400** | **55** | **Streaming validation** |

---

## Integration with v2.x

### Backward Compatibility
- Batch validation (v2.2) still works unchanged
- Contracts from v2.2 used directly
- Quality scores stored alongside streaming results

### Data Flow
```
v2.2 Batch              v3.0 Streaming
(Daily snapshots)       (Real-time events)
      ↓                        ↓
   Quality Store (time-series + real-time combined)
      ↓
   Lineage Graph (synced from v2.2)
      ↓
   Propagated Quality Scores
```

---

## Summary

**v3.0 transforms StatGuardian into a real-time data quality platform:**
- Validate at source (as data arrives)
- Propagate quality through lineage (immediate downstream impact)
- Scale horizontally (Kubernetes)
- Recover from failures (checkpointing + replay)
- Support streaming ETL/ELT pipelines

**Depends on:** v2.2 lineage + v2.3 ML predictions
**Unlocks:** Real-time data contracts, SLA enforcement, proactive remediation

Ready for v4.0 (Intelligent Automation) and v5.0 (Governance & Compliance).
