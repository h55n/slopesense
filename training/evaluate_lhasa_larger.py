"""Prespecified sampled-data Platt comparison, not population calibration or safety validation."""

import json
import pathlib
import re
import pandas as pd
import numpy as np
import xgboost as xgb
import argparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

parser = argparse.ArgumentParser()
parser.add_argument("--inputs", type=pathlib.Path, required=True)
parser.add_argument("--model", type=pathlib.Path, required=True)
args = parser.parse_args()
out = args.inputs
rows = json.load(open(out / "rows_smap_ready.json"))
smap = json.load(open(out / "smap_raw.json"))
values = {}
bad = set(r["event_id"] for r in rows if "smap_error" in r)
reasons = []
for entry in smap:
    if entry.get("status") != 200:
        bad.update(r[0] for r in entry["rows"])
        reasons.append(
            {"source": entry["url"], "error": entry.get("error", entry.get("status"))}
        )
        continue
    # DAP ASCII repeats same names for multiple subsets; preserve returned sequence.
    moist = [
        float(v)
        for v in re.findall(
            r"/Geophysical_Data/sm_profile_wetness\[\d+\], ([^\n]+)", entry["text"]
        )
    ]
    lat = [float(v) for v in re.findall(r"cell_lat\[\d+\], ([^\n]+)", entry["text"])]
    lon = [float(v) for v in re.findall(r"cell_lon\[\d+\], ([^\n]+)", entry["text"])]
    if (
        len(moist) != len(entry["rows"])
        or len(lat) != len(moist)
        or len(lon) != len(moist)
    ):
        bad.update(r[0] for r in entry["rows"])
        reasons.append(
            {"source": entry["url"], "error": "ambiguous multi-subset response"}
        )
        continue
    for key, m, la, lo in zip(entry["rows"], moist, lat, lon):
        values[tuple(key)] = (m, la, lo)
rain = {}
for p in (out / "rain_crops").glob("*.json"):
    j = json.load(open(p))
    if "values" in j:
        rain[j["key"]] = j
for r in rows:
    key = (r["event_id"], r["target_date"])
    try:
        m, la, lo = values[key]
        assert (
            0 <= m <= 1
            and abs(la - r["static_lat"]) < 0.2
            and abs(lo - r["static_lon"]) < 0.2
            and r["mask"] > 0
            and r["p99"] > 0
        )
        r["gwetprof"] = m
        v = []
        for age in range(3):
            v.append(
                next(
                    v["mm"]
                    for v in rain[r["rainkey" + str(age)]]["values"]
                    if v["event_id"] == r["event_id"]
                )
            )
        r["rain"] = v[0] / r["p99"]
        r["antecedent"] = v[1] + v[2]
    except Exception as e:
        bad.add(r["event_id"])
        reasons.append(
            {"event": r["event_id"], "date": r["target_date"], "error": str(e)}
        )
df = pd.DataFrame([r for r in rows if r["event_id"] not in bad])
features = ["Lithology", "Slope", "pga", "gwetprof", "antecedent", "rain"]
assert np.isfinite(df[features]).all().all()
assert df.groupby("event_id").study_split.nunique().max() == 1
assert df.groupby("spatial_group").study_split.nunique().max() == 1
b = xgb.Booster()
b.load_model(str(args.model))
assert b.feature_names == features
df["raw"] = b.predict(xgb.DMatrix(df[features], feature_names=features))


def logit(p):
    return np.log(
        np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6))
    ).reshape(-1, 1)


cal = df[df.study_split == "calibration"]
model = LogisticRegression(C=1, random_state=42).fit(logit(cal.raw.values), cal.label)
# Persist calibration and selection choice BEFORE reading comparison metrics.
df["calibrated"] = model.predict_proba(logit(df.raw.values))[:, 1]
sel = df[df.study_split == "selection"]
test = df[df.study_split == "comparison"]


def metric(y, p, t=0.5):
    y = np.asarray(y)
    p = np.asarray(p)
    return {
        "recall": float((p[y == 1] >= t).mean()),
        "sampled_background_fpr": float((p[y == 0] >= t).mean()),
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "positives": int(y.sum()),
        "backgrounds": int((y == 0).sum()),
    }


threshold = None
for t in sorted(set(sel.calibrated), reverse=True):
    m = metric(sel.label, sel.calibrated, t)
    if m["recall"] >= 0.9 and m["sampled_background_fpr"] <= 0.1:
        threshold = float(t)
        break
json.dump(
    {
        "coefficient": float(model.coef_[0, 0]),
        "intercept": float(model.intercept_[0]),
        "threshold": threshold,
        "comparison_metrics_read": False,
    },
    open(out / "calibration_selection_before_comparison.json", "w"),
    indent=2,
)
result = {
    "status": "posthoc_sampled_data_calibration_not_independent_safety_validation",
    "planned_events": 90,
    "complete_events": df.event_id.nunique(),
    "excluded_event_ids": sorted(bad),
    "exclusions": reasons,
    "split_counts": df.groupby("study_split")
    .agg(events=("event_id", "nunique"), rows=("event_id", "size"))
    .to_dict(),
    "calibrator": {
        "method": "Platt logit raw C1",
        "coefficient": float(model.coef_[0, 0]),
        "intercept": float(model.intercept_[0]),
    },
    "selection_threshold": threshold,
    "comparison_raw_fixed05": metric(test.label, test.raw),
    "comparison_calibrated_fixed05": metric(test.label, test.calibrated),
    "warning_enabled": False,
    "population_calibrated": False,
    "independent_confirmation": False,
}
if threshold is not None:
    result["comparison_selected_threshold"] = metric(
        test.label, test.calibrated, threshold
    )
rng = np.random.default_rng(87123)
ids = test.event_id.unique()
samples = []
for _ in range(300):
    f = pd.concat(
        [test[test.event_id == g] for g in rng.choice(ids, len(ids), replace=True)]
    )
    samples.append(
        metric(f.label, f.calibrated, threshold if threshold is not None else 0.5)
    )
result["comparison_group_bootstrap95"] = {
    k: np.quantile([v[k] for v in samples], [0.025, 0.975]).tolist()
    for k in ["recall", "sampled_background_fpr", "brier", "roc_auc", "pr_auc"]
}
result["comparison_constant_calibration_prevalence_brier"] = float(
    brier_score_loss(test.label, np.full(len(test), cal.label.mean()))
)
df.to_csv(out / "predictions.csv", index=False)
json.dump(result, open(out / "metrics.json", "w"), indent=2)
print(json.dumps(result, indent=2))
