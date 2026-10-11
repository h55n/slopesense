"""Exploratory, separate temporal/spatial holdouts. Never a deployment model."""

import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
    precision_score,
    recall_score,
    confusion_matrix,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from training.build_weather_dataset import FEATURES


def metrics(y, p):
    pred = p >= 0.5  # predetermined, never tuned on test outcomes
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    observed, predicted = calibration_curve(y, p, n_bins=5, strategy="quantile")
    return {
        "count": len(y),
        "positives": int(y.sum()),
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "precision_at_0_5": float(precision_score(y, pred, zero_division=0)),
        "recall_at_0_5": float(recall_score(y, pred, zero_division=0)),
        "background_false_positive_fraction_at_0_5": float(fp / (fp + tn)),
        "confusion_at_0_5": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
        "calibration_bins": [
            {"mean_probability": float(a), "event_fraction": float(b)}
            for a, b in zip(predicted, observed)
        ],
    }


def group_bootstrap(frame, probability, draws=300):
    """Event-group resampling, not misleading independent-row confidence."""
    rng = np.random.default_rng(87123)
    ids = frame.event_id.unique()
    samples = []
    for _ in range(draws):
        selected = rng.choice(ids, size=len(ids), replace=True)
        index = np.concatenate(
            [np.flatnonzero(frame.event_id.values == group) for group in selected]
        )
        y = frame.label.values[index]
        if len(np.unique(y)) < 2:
            continue
        p = probability[index]
        samples.append(
            [average_precision_score(y, p), roc_auc_score(y, p), brier_score_loss(y, p)]
        )
    bounds = np.quantile(np.array(samples), [0.025, 0.975], axis=0)
    return {
        name: {"lower": float(bounds[0, i]), "upper": float(bounds[1, i])}
        for i, name in enumerate(["pr_auc", "roc_auc", "brier"])
    }


def evaluate(path, output):
    data = pd.read_csv(path)
    if data[FEATURES].isna().any().any():
        raise ValueError("Missing data; no fill or guessed values")
    # Use parent's positive event year, not each matched-background year, for grouping.
    event_year = (
        data[data.label.eq(1)].set_index("event_id").target_date.str[:4].astype(int)
    )
    data = data[data.event_id.isin(event_year.index)].copy()
    data["event_year"] = data.event_id.map(event_year)
    # Spatial holdout is independent of feature/outcome, fixed before fitting.
    data["spatial_holdout"] = data.spatial_group.map(
        lambda x: int(hashlib.sha256(x.encode()).hexdigest()[:8], 16) % 5 == 0
    )
    train = data[(data.event_year <= 2012) & ~data.spatial_holdout]
    cal = data[data.event_year.eq(2013) & ~data.spatial_holdout]
    temporal = data[(data.event_year >= 2014) & ~data.spatial_holdout]
    spatial = data[data.spatial_holdout]
    for name, frame in [
        ("train", train),
        ("calibration", cal),
        ("temporal_test", temporal),
        ("spatial_test", spatial),
    ]:
        if len(frame) < 30 or frame.label.nunique() != 2:
            raise ValueError(
                f"Insufficient {name} observations; do not fabricate metrics"
            )
    model = make_pipeline(
        StandardScaler(), LogisticRegression(max_iter=2000, C=1.0, random_state=42)
    )
    model.fit(train[FEATURES], train.label)
    calibrated = CalibratedClassifierCV(model, method="sigmoid", cv="prefit")
    calibrated.fit(cal[FEATURES], cal.label)
    result = {
        "status": "exploratory_only_not_validated",
        "operational_publication_enabled": False,
        "inventory_provenance": "unverified_third_party_mirror",
        "weather": "ERA5 reanalysis 0.25degree",
        "target": "reported_event_vs_matched_unreported_background_not_failure_probability",
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "features": FEATURES,
        "model": "standardized logistic regression C1; separate2013 Platt calibration",
        "split_counts": {
            name: {
                "rows": len(frame),
                "events": frame.event_id.nunique(),
                "positives": int(frame.label.sum()),
            }
            for name, frame in [
                ("train", train),
                ("calibration", cal),
                ("temporal_test", temporal),
                ("spatial_test", spatial),
            ]
        },
        "splits": {
            "train": "<=2012, non-spatial-holdout",
            "calibration": "2013, non-spatial-holdout",
            "temporal_test": ">=2014, non-spatial-holdout",
            "spatial_test": "fixed20% spatial groups, all dates",
        },
        "metrics": {},
        "limitations": [
            "reported events incompletely observed",
            "unknown event-time/timezone",
            "matched background is not verified non-event",
            "reanalysis not available in real time",
            "no terrain/NDVI/susceptibility inputs",
            "spatial groups1degree may not fully remove storm dependence",
        ],
    }
    predictions = []
    for name, frame in [("temporal_test", temporal), ("spatial_test", spatial)]:
        p = calibrated.predict_proba(frame[FEATURES])[:, 1]
        result["metrics"][name] = {
            "calibrated": metrics(frame.label, p),
            "uncalibrated": metrics(
                frame.label, model.predict_proba(frame[FEATURES])[:, 1]
            ),
            "constant_training_prevalence_brier": float(
                brier_score_loss(frame.label, np.full(len(frame), train.label.mean()))
            ),
        }
        result["metrics"][name]["event_group_bootstrap_95pct"] = group_bootstrap(
            frame, p
        )
        rows = frame.copy()
        rows["prediction"] = p
        rows["split"] = name
        predictions.append(rows)
    output.mkdir(parents=True, exist_ok=True)
    (output / "metrics.json").write_text(json.dumps(result, indent=2))
    pd.concat(predictions).to_csv(output / "test_predictions.csv", index=False)
    joblib.dump(calibrated, output / "exploratory_baseline.joblib")
    data.assign(
        split=np.select(
            [
                data.index.isin(train.index),
                data.index.isin(cal.index),
                data.index.isin(temporal.index),
                data.index.isin(spatial.index),
            ],
            ["train", "calibration", "temporal_test", "spatial_test"],
            "excluded",
        )
    ).to_csv(output / "split_manifest.csv", index=False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    evaluate(a.dataset, a.output)
