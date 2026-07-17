# StatGuardian v2.3 — ML-Powered Detection

**Date:** 2026-07-17  
**Status:** ARCHITECTURE DESIGN (LOCKED)  
**Timeline:** 4 weeks (2026-08-21 to 2026-09-18)  
**Target Release:** 2026-09-18  
**Priority:** HIGH (Complements v2.2 lineage foundation)  
**Vision:** Predictive data quality — catch problems before they happen

---

## Executive Overview

Build ML-powered anomaly detection layer on top of v2.2 lineage:
- **Drift Prediction:** Predict schema/data drift 1-7 days ahead
- **Seasonal Adjustment:** Handle periodic patterns in data
- **Adaptive Thresholds:** Learn optimal validation constraints per table
- **Confidence Scoring:** Measure how certain we are about predictions

**Impact:**
- Catch data quality issues **before** they affect downstream systems
- Reduce false positives by 40-60% (adaptive thresholds)
- Enable proactive remediation instead of reactive firefighting

---

## Architecture: Three ML Components

### Component 1: Drift Prediction Model

**Problem:** Drift detection is reactive (detect after it happens)

```
Current (Reactive):
  Day 1: New data arrives
  Day 2: Drift detector runs → ALERT (too late, data already bad)

Predicted (Proactive):
  Day 0: Analyze historical patterns
  Day 1: Model predicts "drift likely on Day 3"
  Day 2: Prepare remediation
  Day 3: Drift happens, already handled
```

**Solution:** Time-series model on lineage history

```python
class DriftPredictionModel:
    """
    Predicts schema/data drift 1-7 days ahead
    """
    
    def __init__(self, table_id: str, historical_lineage: List[LineageVersion]):
        # Extract features from lineage history
        self.change_frequency = analyze_change_patterns(historical_lineage)
        self.cyclical_patterns = detect_seasonality(historical_lineage)
        self.severity_trends = trend_severity_changes(historical_lineage)
    
    def predict_drift(self, days_ahead: int = 3) -> DriftPrediction:
        """
        Predict probability of drift in next N days
        
        Returns:
            DriftPrediction {
                probability: 0.0-1.0,  # How likely is drift?
                confidence: 0.0-1.0,   # How sure are we?
                expected_type: str,    # SCHEMA | DATA | BOTH
                expected_severity: str,# LOW | MEDIUM | HIGH
                reason: str,           # Why do we think this?
            }
        """
        
        # Feature extraction
        features = {
            "recent_change_rate": self.change_frequency[-7:].mean(),
            "cyclical_component": self.cyclical_patterns.current_phase,
            "trend_direction": self.severity_trends.slope,
            "days_since_last_change": days_since_last_lineage_change(),
        }
        
        # ML model predicts
        prediction = self.model.predict(features)
        
        return DriftPrediction(
            probability=prediction.drift_probability,
            confidence=prediction.confidence_score,
            expected_type=prediction.change_type,
            expected_severity=prediction.severity,
            reason=generate_explanation(features, prediction),
        )
    
    def train(self, lineage_history: List[LineageVersion], labels: List[DriftEvent]):
        """
        Train on historical lineage + known drift events
        
        Supervised learning:
          Input: Historical lineage features
          Output: Actual drift events that occurred
          Goal: Learn to predict future drift
        """
        
        X = [extract_features(v) for v in lineage_history]
        y = [1 if drift_occurred else 0 for drift in labels]
        
        self.model.fit(X, y)
        self.calibration_curve = calibrate_predictions(self.model)
```

**Training Data:** Use v2.2 lineage history as training set
- Historical LineageVersion records
- Known drift events (from StatGuardian audit logs)
- Timestamps of schema changes
- Severity classifications

---

### Component 2: Seasonal Adjustment

**Problem:** Same metric behaves differently at different times

```
Example: Orders per day
  Weekday avg: 10,000 orders/day
  Weekend avg: 5,000 orders/day
  Weekend with 10,000 orders = ANOMALY (drift)
  Weekday with 5,000 orders = ANOMALY (drift)

Without seasonal adjustment:
  Both flagged as anomalies (false positives)

With seasonal adjustment:
  Weekday 10K = normal, Weekend 5K = normal
  Weekday 5K = anomaly, Weekend 10K = anomaly
```

**Solution:** Decompose time series into components

```python
class SeasonalAdjustmentModel:
    """
    Separates seasonal patterns from anomalies
    """
    
    def __init__(self, table_id: str, metric_history: TimeSeries):
        # Decompose time series
        self.trend = extract_trend(metric_history)           # Long-term movement
        self.seasonal = extract_seasonality(metric_history)  # Repeating patterns
        self.residual = extract_residual(metric_history)     # Everything else
        
        # Typical periods to detect
        self.periods = {
            "daily": 24,      # Hourly variation
            "weekly": 7,      # Day-of-week variation
            "monthly": 30,    # Day-of-month variation
            "yearly": 365,    # Seasonal patterns
        }
    
    def adjust_metric(self, value: float, timestamp: datetime) -> AdjustedMetric:
        """
        Remove seasonal component from metric
        
        adjusted = value - seasonal_component
        """
        
        seasonal_component = self.seasonal.value_at(timestamp)
        adjusted_value = value - seasonal_component
        
        return AdjustedMetric(
            original=value,
            seasonal_component=seasonal_component,
            adjusted=adjusted_value,
            confidence=self.seasonal.confidence_at(timestamp),
        )
    
    def detect_anomaly_adjusted(self, value: float, timestamp: datetime) -> bool:
        """
        Detect anomalies in seasonally-adjusted data
        """
        
        adjusted = self.adjust_metric(value, timestamp)
        
        # Compare adjusted value to baseline
        baseline = self.residual.mean()
        std_dev = self.residual.std()
        
        z_score = (adjusted.adjusted - baseline) / std_dev
        
        # Anomaly if >3 standard deviations from mean
        return abs(z_score) > 3.0
    
    def train(self, metric_history: TimeSeries, periods: Optional[List[int]] = None):
        """
        Train on historical metric data
        
        Uses STL decomposition:
          - Seasonal: Repeating patterns
          - Trend: Long-term movement
          - Residual: Noise + anomalies
        """
        
        self.trend = extract_trend_stl(metric_history)
        self.seasonal = extract_seasonal_stl(metric_history, periods)
        self.residual = metric_history - self.trend - self.seasonal
```

---

### Component 3: Adaptive Thresholds

**Problem:** Static thresholds cause false positives/negatives

```
Example: Completeness validation
  Rule: "completeness(customer_id) > 95%"
  
  Table A (always perfect): 99.5% → PASS (margin: 4.5%)
  Table B (has NULLs): 97% → PASS (margin: 2%)
  Table B next day: 96.8% → PASS (margin: 1.8%)
  Table B next day: 95.1% → PASS (margin: 0.1%)
  Table B next day: 94.9% → FAIL (sudden alert)
  
  Better threshold for B: 93% (learned from history)
```

**Solution:** Learn optimal threshold per table + metric

```python
class AdaptiveThresholdModel:
    """
    Learn optimal validation thresholds from historical data
    """
    
    def __init__(self, table_id: str, metric_history: Dict[str, List[float]]):
        # Learn per-table behavior
        self.baseline_mean = {}
        self.baseline_std = {}
        self.natural_min = {}
        self.natural_max = {}
        
        for metric_name, values in metric_history.items():
            self.baseline_mean[metric_name] = np.mean(values)
            self.baseline_std[metric_name] = np.std(values)
            self.natural_min[metric_name] = np.percentile(values, 5)  # 5th percentile
            self.natural_max[metric_name] = np.percentile(values, 95) # 95th percentile
    
    def suggest_threshold(self, metric_name: str, validation_type: str) -> Threshold:
        """
        Suggest optimal threshold for a metric
        
        validation_type: "minimum" | "maximum" | "both"
        """
        
        mean = self.baseline_mean[metric_name]
        std = self.baseline_std[metric_name]
        
        if validation_type == "minimum":
            # 2 standard deviations below natural minimum
            threshold = self.natural_min[metric_name] - (2 * std)
            
        elif validation_type == "maximum":
            # 2 standard deviations above natural maximum
            threshold = self.natural_max[metric_name] + (2 * std)
            
        else:  # both
            threshold = {
                "min": self.natural_min[metric_name] - (2 * std),
                "max": self.natural_max[metric_name] + (2 * std),
            }
        
        return Threshold(
            value=threshold,
            based_on_samples=len(metric_history[metric_name]),
            confidence=calculate_confidence(mean, std),
            reason=f"Learned from {len(metric_history[metric_name])} historical values",
        )
    
    def detect_anomaly_adaptive(self, metric_name: str, current_value: float) -> AnomalyDetection:
        """
        Detect anomalies using learned thresholds
        """
        
        mean = self.baseline_mean[metric_name]
        std = self.baseline_std[metric_name]
        
        # Z-score: how many standard deviations from mean?
        z_score = (current_value - mean) / std
        
        # Anomaly if beyond 3 standard deviations
        is_anomaly = abs(z_score) > 3.0
        
        return AnomalyDetection(
            is_anomaly=is_anomaly,
            z_score=z_score,
            deviation_from_mean=current_value - mean,
            confidence=1.0 - (1.0 / (1.0 + abs(z_score))),  # Sigmoid confidence
        )
    
    def train(self, metric_history: Dict[str, List[float]]):
        """
        Train on historical metric values
        """
        
        for metric_name, values in metric_history.items():
            self.baseline_mean[metric_name] = np.mean(values)
            self.baseline_std[metric_name] = np.std(values)
            self.natural_min[metric_name] = np.percentile(values, 5)
            self.natural_max[metric_name] = np.percentile(values, 95)
```

---

## ML Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ TRAINING PHASE (Offline)                                   │
│                                                             │
│ Input: v2.2 Lineage history + Metric history               │
│ └─ LineageVersion records (daily snapshots)                │
│ └─ Historical metric values (completeness, drift, etc.)    │
│ └─ Known drift events (tagged in audit logs)               │
│                                                             │
│ Models to train:                                            │
│ ├─ DriftPredictionModel (supervised learning)              │
│ │  └─ Features: change rate, patterns, trends             │
│ │  └─ Labels: drift events that occurred                  │
│ │  └─ Output: probability of future drift                 │
│ │                                                          │
│ ├─ SeasonalAdjustmentModel (time-series decomposition)     │
│ │  └─ Input: historical metrics                           │
│ │  └─ Output: seasonal + trend + residual components     │
│ │                                                          │
│ └─ AdaptiveThresholdModel (statistical learning)           │
│    └─ Input: metric history per table                     │
│    └─ Output: learned thresholds per table                │
└─────────────────────────────────────────────────────────────┘
                        │
        ┌───────────────▼──────────────────┐
        │ MODEL EVALUATION & VALIDATION    │
        │                                  │
        │ ├─ Cross-validation              │
        │ ├─ Precision/recall/F1           │
        │ ├─ Calibration curves            │
        │ └─ Publish models                │
        └───────────────┬──────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│ INFERENCE PHASE (Real-time)                                 │
│                                                             │
│ For each new LineageVersion:                                │
│ ├─ DriftPredictionModel.predict() → Drift probability      │
│ ├─ SeasonalAdjustmentModel.adjust() → Anomaly score        │
│ ├─ AdaptiveThresholdModel.detect() → Violation detection   │
│ └─ If confidence > threshold: ALERT                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

### Correctness
✓ Drift predictions 70%+ accurate within 3-day window  
✓ False positive rate <5% (adaptive thresholds)  
✓ Seasonal adjustments explain 80%+ of variance  
✓ Confidence scores well-calibrated (predicted ≈ actual)  

### Performance
✓ Training: <30 minutes on full lineage history  
✓ Inference: <100ms per prediction  
✓ Model size: <100MB per table  

### User Experience
✓ Predictions explainable ("drift likely because X")  
✓ Actionable alerts (not just probability scores)  
✓ Easy threshold tuning (suggest better defaults)  

---

## Integration with v2.2

```python
# In validation_report.py

from statguardian_ml import DriftPredictionModel, SeasonalAdjustmentModel

report = execute(contract, df)

# NEW: Add ML predictions
predictor = DriftPredictionModel.load("customers_enriched")
drift_prediction = predictor.predict(days_ahead=3)

report.ml_insights = {
    "drift_prediction": {
        "probability": 0.72,
        "confidence": 0.89,
        "expected_type": "SCHEMA",
        "reason": "Pattern suggests schema change coming",
    },
    "recommended_action": "Review and prepare for schema migration",
}

print(report.ml_insights)
```

---

## Week-by-Week Breakdown (4 weeks)

| Week | Component | Lines | Tests | Output |
|------|-----------|-------|-------|--------|
| 1 | Drift Prediction | 400 | 10 | Training/inference pipeline |
| 2 | Seasonal Adjustment | 300 | 8 | Time-series decomposition |
| 3 | Adaptive Thresholds | 250 | 7 | Per-table threshold learning |
| 4 | Integration + Release | 150 | 5 | v2.3.0 + documentation |
| **TOTAL** | **v2.3** | **1,100** | **30** | **Production ML layer** |

---

## Data Requirements

### Training Data (From v2.2 Lineage)
- LineageVersion history: ≥90 days (180+ versions)
- For each table:
  - Schema change events
  - Drift events (flagged in audit logs)
  - Metric values (completeness, uniqueness, etc.)
  - Timestamps of changes

### Model Size
- Per table: 10-50MB (depends on history size)
- Total (1000 tables): 10-50GB
- Storage: Efficient serialization (pickle/joblib)

---

## Summary

**v2.3 transforms StatGuardian from reactive to proactive:**
- Predict drift before it happens
- Handle seasonal patterns automatically
- Learn optimal thresholds per table
- Never alert on noise again

Ready for v3.0 (distributed validation) and v4.0 (intelligent automation).
