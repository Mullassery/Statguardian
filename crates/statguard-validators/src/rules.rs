use polars::prelude::*;
use statguard_core::ast::{MetricFn, QualityRule, Severity};
use crate::Violation;

pub struct RuleEngine;

impl RuleEngine {
    pub fn evaluate(df: &DataFrame, rules: &[QualityRule]) -> Vec<Violation> {
        rules.iter().flat_map(|r| evaluate_rule(df, r)).collect()
    }
}

fn evaluate_rule(df: &DataFrame, rule: &QualityRule) -> Vec<Violation> {
    let series = match df.column(&rule.column).ok().and_then(|c| c.as_series().cloned()) {
        Some(s) => s,
        None => {
            return vec![Violation::new(
                &rule.column, "quality_check",
                format!("column '{}' not found", rule.column),
                Severity::Blocking,
            )];
        }
    };

    let observed = match compute_metric(&series, &rule.metric) {  // series is owned Series
        Some(v) => v,
        None => return vec![],
    };

    if !rule.op.evaluate(observed, rule.threshold) {
        vec![Violation::new(
            &rule.column,
            metric_name(&rule.metric),
            format!(
                "quality check failed: {}({}) = {:.4} {} {:.4}",
                metric_name(&rule.metric), rule.column, observed, rule.op, rule.threshold
            ),
            rule.severity.clone(),
        )
        .with_values(observed, rule.threshold)]
    } else {
        vec![]
    }
}

fn compute_metric(series: &Series, metric: &MetricFn) -> Option<f64> {
    let n = series.len() as f64;
    if n == 0.0 { return Some(0.0); }

    match metric {
        MetricFn::Completeness | MetricFn::NonNullRate => {
            Some(1.0 - series.null_count() as f64 / n)
        }
        MetricFn::Uniqueness => {
            let n_unique = series.n_unique().ok()? as f64;
            Some(n_unique / n)
        }
        MetricFn::Validity => {
            Some((n - series.null_count() as f64) / n)
        }
        MetricFn::Consistency => {
            let n_unique = series.n_unique().ok()? as f64;
            Some(n_unique / n)
        }
        MetricFn::Freshness => {
            Some(1.0 - series.null_count() as f64 / n)
        }
    }
}

fn metric_name(m: &MetricFn) -> &'static str {
    match m {
        MetricFn::Completeness  => "completeness",
        MetricFn::Uniqueness    => "uniqueness",
        MetricFn::Validity      => "validity",
        MetricFn::Consistency   => "consistency",
        MetricFn::Freshness     => "freshness",
        MetricFn::NonNullRate   => "non_null_rate",
    }
}
