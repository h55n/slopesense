"""Prespecified post-hoc comparison: same splits, no new untouched confirmation."""

import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss
from training.build_weather_dataset import FEATURES as WEATHER
from training.add_terrain import TERRAIN_FEATURES
from training.evaluate_stage2 import metrics

FEATURES = WEATHER + TERRAIN_FEATURES + ["rain_max_daily_14d", "api_decay_085_14d"]


def bootstrap(frame, p, threshold, draws=300):
    rng = np.random.default_rng(87123)
    ids = frame.event_id.unique()
    samples = []
    for _ in range(draws):
        selected = rng.choice(ids, size=len(ids), replace=True)
        ix = np.concatenate(
            [np.flatnonzero(frame.event_id.values == g) for g in selected]
        )
        y = frame.label.values[ix]
        if len(np.unique(y)) < 2:
            continue
        m = metrics(y, p[ix], threshold)
        samples.append(
            [
                m["recall_at_0_5"],
                m["background_false_positive_fraction_at_0_5"],
                m["brier"],
                m["pr_auc"],
                m["roc_auc"],
            ]
        )
    q = np.quantile(samples, [0.025, 0.975], axis=0)
    return {
        k: {"lower": float(q[0, i]), "upper": float(q[1, i])}
        for i, k in enumerate(
            ["recall", "background_fpr", "brier", "pr_auc", "roc_auc"]
        )
    }


def evaluate(path, out):
    out.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(path)
    if not np.isfinite(data[FEATURES]).all().all():
        raise ValueError("Missing data: no fill")
    if data.groupby("event_id").split.nunique().max() != 1:
        raise ValueError("Event split leakage")
    frames = {k: v for k, v in data.groupby("split")}
    train = frames["train"]
    cal = frames["calibration"]
    selection = frames["threshold"]
    if set(train.spatial_group) & set(frames["spatial_confirmation"].spatial_group):
        raise ValueError("Spatial leakage")
    if (
        pd.to_datetime(data.feature_end_date) >= pd.to_datetime(data.target_date)
    ).any():
        raise ValueError("Future weather")
    model = HistGradientBoostingClassifier(
        max_iter=100,
        learning_rate=0.05,
        max_leaf_nodes=7,
        l2_regularization=1,
        min_samples_leaf=20,
        random_state=42,
        early_stopping=False,
    )
    weight = np.where(
        train.label.eq(1),
        len(train) / (2 * train.label.sum()),
        len(train) / (2 * (len(train) - train.label.sum())),
    )
    model.fit(train[FEATURES], train.label, sample_weight=weight)
    calibrated = CalibratedClassifierCV(model, method="sigmoid", cv="prefit")
    calibrated.fit(cal[FEATURES], cal.label)
    v = calibrated.predict_proba(selection[FEATURES])[:, 1]
    threshold = None
    for t in sorted(set(v), reverse=True):
        m = metrics(selection.label, v, t)
        if (
            m["recall_at_0_5"] >= 0.9
            and m["background_false_positive_fraction_at_0_5"] <= 0.1
        ):
            threshold = float(t)
            break
    result = {
        "status": "post_hoc_technique_comparison_not_independent_confirmation",
        "warning_publication_enabled": False,
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "protocol": "training/STAGE4_PROTOCOL.md",
        "features": FEATURES,
        "validation_selected_threshold": threshold,
        "threshold_dataset": "2014distinct_from2013Platt",
        "research_screen_passed": False,
        "split_counts": {
            k: {
                "events": int(v.event_id.nunique()),
                "rows": len(v),
                "positives": int(v.label.sum()),
            }
            for k, v in frames.items()
        },
        "metrics": {},
        "independent_gates": {
            "inventory_provenance": "official_source_obtained",
            "verified_non_events_base_rates": False,
            "prospective_operational_validation": False,
            "pre_event_terrain_verified": False,
            "exact_local_event_times_verified": False,
            "competent_safety_review": False,
        },
    }
    rows = []
    passes = []
    for name in [
        "legacy_temporal_diagnostic",
        "legacy_spatial_diagnostic",
        "temporal_confirmation",
        "spatial_confirmation",
    ]:
        f = frames[name]
        p = calibrated.predict_proba(f[FEATURES])[:, 1]
        baseline = float(brier_score_loss(f.label, np.full(len(f), train.label.mean())))
        d = {
            "at_0_5": metrics(f.label, p),
            "constant_training_prevalence_brier": baseline,
            "bootstrap_at_0_5": bootstrap(f, p, 0.5),
            "clean_confirmation": False,
        }
        passed = False
        if threshold is not None:
            selected = metrics(f.label, p, threshold)
            ci = bootstrap(f, p, threshold)
            d["at_validation_threshold"] = selected
            d["bootstrap_at_validation_threshold"] = ci
            passed = bool(
                f.label.sum() >= 30
                and selected["recall_at_0_5"] >= 0.9
                and selected["background_false_positive_fraction_at_0_5"] <= 0.1
                and ci["recall"]["lower"] >= 0.8
                and selected["brier"] < baseline
            )
        if name.endswith("confirmation"):
            passes.append(passed)
        d["research_screen_passed"] = passed
        result["metrics"][name] = d
        r = f.copy()
        r["prediction"] = p
        rows.append(r)
    result["research_screen_passed"] = bool(all(passes))
    (out / "metrics.json").write_text(json.dumps(result, indent=2))
    pd.concat(rows).to_csv(out / "test_predictions.csv", index=False)
    joblib.dump(calibrated, out / "exploratory_hgb_api.joblib")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    evaluate(a.dataset, a.output)
