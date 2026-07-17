# StatGuardian v2.3 — ML-Powered Detection Roadmap

**Date:** 2026-07-17  
**Status:** LOCKED & READY TO BUILD  
**Timeline:** 4 weeks (2026-08-21 to 2026-09-18)  
**Target Release:** 2026-09-18  
**Dependency:** v2.2 (lineage APIs available)  
**Blocking:** v3.0 (streaming validation needs ML predictions)

---

## Executive Overview

Build ML-powered predictive layer on v2.2 lineage foundation:
- Drift prediction (1-7 days ahead)
- Seasonal decomposition (handle periodic patterns)
- Adaptive thresholds (learn per-table constraints)
- Production-ready inference (<100ms)

**Impact:** Move from reactive (detect problems) to proactive (predict problems)

---

## Week-by-Week Breakdown

### WEEK 1: Drift Prediction Foundation (Days 1-5)

**Goal:** ML pipeline for predicting schema/data drift

**Components to Build:**

1. **rust/statguardian-ml/src/drift_predictor.rs** (400 lines)
   - `DriftPredictionModel` struct
   - Feature extraction from lineage history
   - Time-series analysis (autocorrelation, trend detection)
   - Statistical forecasting (ARIMA-like approach)

2. **python/statguardian/_ml_drift.py** (350 lines)
   - Python bindings for drift model
   - `DriftPredictionModel` class
   - `predict_drift(days_ahead)` method
   - Confidence scoring

3. **python/statguardian/_ml_training.py** (200 lines)
   - Training pipeline from lineage history
   - Label generation from audit logs
   - Model persistence (save/load)
   - Cross-validation

4. **Database schema for ML** (100 lines SQL)
   - `ml_drift_predictions` table (predictions + confidence)
   - `ml_model_metadata` table (model version, train date, accuracy)

**Tests:** 10 unit tests
- Drift prediction accuracy
- Feature extraction
- Confidence calibration
- Model persistence
- Edge cases (sparse history, new tables)

**Milestones:**
- ✅ Feature extraction working
- ✅ Model training pipeline working
- ✅ Predictions accurate (70%+ precision)
- ✅ All 10 tests passing

**Files Created:**
- `crates/statguardian-ml/src/drift_predictor.rs`
- `python/statguardian/_ml_drift.py`
- `python/statguardian/_ml_training.py`
- Database schema SQL

---

### WEEK 2: Seasonal Adjustment (Days 6-10)

**Goal:** Decompose metrics into seasonal + trend + residual

**Components to Build:**

1. **rust/statguardian-ml/src/seasonal_decomposition.rs** (300 lines)
   - STL decomposition (Seasonal and Trend decomposition using Loess)
   - Extracts seasonal, trend, and residual components
   - Handles multiple periods (daily, weekly, monthly, yearly)

2. **python/statguardian/_ml_seasonal.py** (280 lines)
   - `SeasonalAdjustmentModel` class
   - `adjust_metric(value, timestamp)` method
   - `detect_anomaly_adjusted()` method
   - Training on historical metrics

3. **Integration with metrics** (150 lines)
   - Extract metric history from validation reports
   - Compute seasonal components
   - Store for future lookups

**Tests:** 8 unit tests
- STL decomposition correctness
- Seasonal pattern detection
- Anomaly detection post-adjustment
- Multi-period handling (daily + weekly)
- Edge cases (short history, constant metrics)

**Milestones:**
- ✅ STL decomposition working
- ✅ Seasonal patterns detected (80%+ variance explained)
- ✅ Anomaly detection improved (false positives down 40%)
- ✅ All 8 tests passing

**Files Created:**
- `crates/statguardian-ml/src/seasonal_decomposition.rs`
- `python/statguardian/_ml_seasonal.py`

---

### WEEK 3: Adaptive Thresholds (Days 11-15)

**Goal:** Learn optimal validation thresholds per table + metric

**Components to Build:**

1. **rust/statguardian-ml/src/threshold_learning.rs** (250 lines)
   - Statistical analysis of metric distributions
   - Percentile-based threshold calculation
   - Confidence scoring (based on sample size)

2. **python/statguardian/_ml_thresholds.py** (220 lines)
   - `AdaptiveThresholdModel` class
   - `suggest_threshold(metric_name)` method
   - `detect_anomaly_adaptive()` method
   - Threshold persistence

3. **Threshold database** (100 lines)
   - `adaptive_thresholds` table (per table + metric)
   - Historical threshold values (track changes)
   - Suggestion confidence scores

4. **Integration with validation** (100 lines)
   - Use adaptive thresholds in execute()
   - Fall back to manual thresholds if no learned threshold
   - Report threshold source (manual vs. learned)

**Tests:** 7 unit tests
- Threshold learning accuracy
- Percentile calculation
- Anomaly detection with adaptive thresholds
- Confidence scoring
- Edge cases (single value, all same values)

**Milestones:**
- ✅ Thresholds learned from history
- ✅ False positive rate <5%
- ✅ Thresholds make sense (reviewed manually)
- ✅ All 7 tests passing

**Files Created:**
- `crates/statguardian-ml/src/threshold_learning.rs`
- `python/statguardian/_ml_thresholds.py`

---

### WEEK 4: Integration & Release (Days 16-20)

**Goal:** Complete v2.3.0 release with documentation

**Components to Build:**

1. **Integration with validation report** (150 lines)
   - Add `ml_predictions` section to ValidationReport
   - Include drift probability, seasonal adjustments, threshold suggestions
   - Format as human-readable recommendations

2. **CLI updates** (100 lines)
   - `statguardian ml-predict` command
   - `statguardian ml-train` command
   - `statguardian ml-explain` (explain predictions)

3. **Documentation** (5 docs)
   - ML_PREDICTIONS.md (how to use predictions)
   - THRESHOLD_LEARNING.md (how thresholds work)
   - SEASONAL_ADJUSTMENT.md (seasonal patterns)
   - API_REFERENCE_ML.md
   - MIGRATION_V2_3.md

4. **Integration Tests** (5 tests)
   - End-to-end prediction workflow
   - Validation report includes predictions
   - CLI commands working
   - Multiple table types (different patterns)

5. **Release Preparation**
   - Version bump to v2.3.0
   - CHANGELOG.md update
   - GitHub release notes
   - PyPI publishing

**Tests:** 5 integration tests
- Full prediction pipeline
- Report generation
- CLI functionality
- Performance benchmarks

**Milestones:**
- ✅ All 30 tests passing (10+8+7+5)
- ✅ Documentation complete
- ✅ Performance targets met (<100ms)
- ✅ v2.3.0 released to PyPI

**Files Modified:**
- `validation_report.py` (add ML predictions)
- `_cli.py` (add ML commands)
- `__init__.py` (version bump)

---

## Directory Structure

```
statguardian/
├── crates/
│   └── statguardian-ml/                  (NEW CRATE)
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           ├── drift_predictor.rs        (400 lines)
│           ├── seasonal_decomposition.rs (300 lines)
│           ├── threshold_learning.rs     (250 lines)
│           └── metrics.rs                (100 lines)
│
├── python/statguardian/
│   ├── _ml_drift.py                      (350 lines, NEW)
│   ├── _ml_seasonal.py                   (280 lines, NEW)
│   ├── _ml_thresholds.py                 (220 lines, NEW)
│   ├── _ml_training.py                   (200 lines, NEW)
│   ├── validation_report.py              (MODIFIED: add ML section)
│   └── _cli.py                           (MODIFIED: add ML commands)
│
├── tests/
│   ├── test_ml_drift.py                  (10 tests, NEW)
│   ├── test_ml_seasonal.py               (8 tests, NEW)
│   ├── test_ml_thresholds.py             (7 tests, NEW)
│   └── test_ml_integration.py            (5 tests, NEW)
│
└── docs/
    ├── ML_PREDICTIONS.md                 (NEW)
    ├── THRESHOLD_LEARNING.md             (NEW)
    ├── SEASONAL_ADJUSTMENT.md            (NEW)
    └── MIGRATION_V2_3.md                 (NEW)
```

---

## Public API (Available in v2.3)

### Drift Prediction

```python
from statguardian import DriftPredictionModel

# Load model for a table
predictor = DriftPredictionModel.load("customers_enriched")

# Predict drift 3 days ahead
prediction = predictor.predict(days_ahead=3)
# → DriftPrediction {
#     probability: 0.72,
#     confidence: 0.89,
#     expected_type: "SCHEMA",
#     expected_severity: "HIGH",
#     reason: "Pattern suggests schema change coming"
#   }

# Train new model from lineage history
DriftPredictionModel.train(
    table_id="customers_enriched",
    lineage_history=get_lineage_history("customers_enriched"),
    drift_labels=get_labeled_drift_events("customers_enriched"),
)
```

### Seasonal Adjustment

```python
from statguardian import SeasonalAdjustmentModel

# Load model
model = SeasonalAdjustmentModel.load("orders")

# Adjust metric for seasonality
adjusted = model.adjust_metric(
    value=5000,  # orders/day
    timestamp=datetime.now(),
)
# → AdjustedMetric {
#     original: 5000,
#     seasonal_component: 2000,  # Weekend effect
#     adjusted: 3000,
#     confidence: 0.92
#   }

# Detect anomalies in adjusted data
is_anomaly = model.detect_anomaly_adjusted(5000, datetime.now())
```

### Adaptive Thresholds

```python
from statguardian import AdaptiveThresholdModel

# Load model
model = AdaptiveThresholdModel.load("customers_enriched")

# Get suggested threshold
threshold = model.suggest_threshold(
    metric_name="completeness",
    validation_type="minimum",
)
# → Threshold {
#     value: 0.93,
#     confidence: 0.94,
#     reason: "Learned from 180 historical values"
#   }

# Detect anomalies using learned threshold
anomaly = model.detect_anomaly_adaptive("completeness", 0.85)
# → AnomalyDetection {
#     is_anomaly: True,
#     z_score: -2.3,
#     confidence: 0.96
#   }
```

### Integration in ValidationReport

```python
report = execute(contract, df)

# NEW: ML predictions included
if report.ml_insights:
    print(f"Drift probability: {report.ml_insights['drift_prediction']['probability']}")
    print(f"Recommended action: {report.ml_insights['recommended_action']}")
```

---

## Testing Strategy

### Unit Tests (30 total)

| Component | Tests | Focus |
|-----------|-------|-------|
| Drift Prediction | 10 | Accuracy, feature extraction, calibration |
| Seasonal Adjustment | 8 | STL correctness, pattern detection, anomaly scoring |
| Adaptive Thresholds | 7 | Threshold learning, confidence, edge cases |
| Integration | 5 | End-to-end workflows, CLI, report generation |

### Manual Testing

- Real drift event scenario (verify prediction)
- Seasonal patterns (daily, weekly, yearly)
- Edge cases (sparse data, new tables, constant metrics)
- Performance benchmarks (training time, inference latency)

---

## Success Criteria

### Correctness
✓ Drift predictions 70%+ accurate within 3-day window  
✓ False positive rate <5% (adaptive thresholds work)  
✓ Seasonal decomposition explains 80%+ variance  
✓ Confidence scores well-calibrated  

### Performance
✓ Training: <30 minutes on 180+ days of lineage history  
✓ Inference: <100ms per prediction  
✓ Model size: <50MB per table  

### User Experience
✓ Predictions explainable (include "why")  
✓ Actionable alerts (suggest next steps)  
✓ Threshold suggestions make sense  
✓ Documentation clear with examples  

---

## Metrics

| Metric | Target | Priority |
|--------|--------|----------|
| Code Coverage | 90%+ | HIGH |
| Test Pass Rate | 100% | HIGH |
| Prediction Accuracy | 70%+ | HIGH |
| False Positive Rate | <5% | HIGH |
| Inference Latency | <100ms | MEDIUM |
| Training Time | <30 min | MEDIUM |

---

## Release Checklist

- [ ] All 30 tests passing
- [ ] Code coverage 90%+
- [ ] Performance targets met
- [ ] Documentation reviewed
- [ ] Example notebooks created
- [ ] Version bumped to v2.3.0
- [ ] CHANGELOG.md updated
- [ ] GitHub release notes prepared
- [ ] PyPI package published
- [ ] Migration guide prepared

---

## Summary

**v2.3 adds intelligence to StatGuardian:**
- Predict drift before it happens (70%+ accuracy)
- Handle seasonality automatically (80%+ variance explained)
- Learn optimal thresholds per table (<5% false positives)
- Production-ready inference (<100ms)

**Timeline:** 4 weeks  
**Code:** 1,100 lines (Rust + Python)  
**Tests:** 30 unit + 5 integration  
**Status:** ✅ LOCKED & READY TO BUILD

**Next:** v3.0 (Streaming & Distributed Validation) depends on v2.3 predictions
