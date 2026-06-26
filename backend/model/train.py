"""LightGBM training pipeline for SlopeSense FPI calibration."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from backend.model.fpi_engine import FEATURE_WEIGHTS
from backend.processing.preprocessor import DataPreprocessor


class ModelTrainer:
    """Train a LightGBM landslide classifier from historical India event data."""

    GLC_URL = "https://maps.nccs.nasa.gov/download/landslides/nasa_global_landslide_catalog_point.csv"

    def download_nasa_glc(self) -> pd.DataFrame:
        """Download NASA Global Landslide Catalog rows for India."""
        df = pd.read_csv(self.GLC_URL)
        lat_col = "latitude" if "latitude" in df.columns else "lat"
        lon_col = "longitude" if "longitude" in df.columns else "lon"
        date_col = "event_date" if "event_date" in df.columns else "date"
        india = df[
            df[lat_col].between(6, 38)
            & df[lon_col].between(66, 98)
        ].copy()
        india["event_date"] = pd.to_datetime(india[date_col], errors="coerce", utc=True)
        india = india.dropna(subset=[lat_col, lon_col, "event_date"])
        india = india.rename(columns={lat_col: "lat", lon_col: "lon"})
        return india[["lat", "lon", "event_date"]].reset_index(drop=True)

    def extract_features_for_event(self, lat: float, lon: float, event_date: datetime) -> dict:
        """Extract feature values for the grid cell nearest an event at T-24h."""
        run_time = event_date - timedelta(hours=24)
        bbox = {"min_lat": lat - 0.15, "max_lat": lat + 0.15, "min_lon": lon - 0.15, "max_lon": lon + 0.15}
        grid = DataPreprocessor(bbox=bbox).build_feature_grid(run_time=run_time)
        i = int(np.argmin(np.abs(grid.lats - lat)))
        j = int(np.argmin(np.abs(grid.lons - lon)))
        return {
            "rainfall_3d_mm": float(grid.rainfall_3d_mm[i, j]),
            "soil_moisture_pct": float(grid.soil_moisture_pct[i, j]),
            "slope_degrees": float(grid.slope_degrees[i, j]),
            "susceptibility_class": float(grid.susceptibility_class[i, j]),
            "forecast_24h_mm": float(grid.forecast_24h_mm[i, j]),
            "ndvi_delta": float(grid.ndvi_delta[i, j]),
        }

    def build_training_dataset(
        self,
        events: pd.DataFrame,
        negative_ratio: int = 5,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Build positive event rows plus random synthetic non-event negatives."""
        rows = []
        for event in events.itertuples(index=False):
            features = self.extract_features_for_event(event.lat, event.lon, event.event_date.to_pydatetime())
            features["label"] = 1
            rows.append(features)

        rng = np.random.default_rng(42)
        for _ in range(max(1, len(rows) * negative_ratio)):
            features = {
                "rainfall_3d_mm": float(rng.uniform(0, 120)),
                "soil_moisture_pct": float(rng.uniform(10, 75)),
                "slope_degrees": float(rng.uniform(5, 35)),
                "susceptibility_class": float(rng.integers(1, 5)),
                "forecast_24h_mm": float(rng.uniform(0, 70)),
                "ndvi_delta": float(rng.uniform(-0.08, 0.12)),
                "label": 0,
            }
            rows.append(features)

        df = pd.DataFrame(rows)
        return df[list(FEATURE_WEIGHTS.keys())].fillna(0), df["label"].astype(int)

    def train_and_evaluate(self, X: pd.DataFrame, y: pd.Series, epochs: int = 300) -> dict:
        """Train LightGBM, cross-validate once, and return operating metrics."""
        import lightgbm as lgb
        from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
        from sklearn.model_selection import train_test_split

        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        model = lgb.LGBMClassifier(
            n_estimators=epochs,
            learning_rate=0.05,
            max_depth=6,
            num_leaves=31,
            class_weight="balanced",
            random_state=42,
            verbose=-1,
        )
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_val)[:, 1]
        preds = probs >= 0.65
        return {
            "model": model,
            "auc": float(roc_auc_score(y_val, probs)),
            "precision_at_065": float(precision_score(y_val, preds, zero_division=0)),
            "recall_at_065": float(recall_score(y_val, preds, zero_division=0)),
            "f1_at_065": float(f1_score(y_val, preds, zero_division=0)),
            "n_train": int(len(X_train)),
            "n_val": int(len(X_val)),
        }

    def save_model(self, model, metrics: dict, output_dir: Path = Path("data/model")) -> Path:
        """Save model plus metadata."""
        import joblib

        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / "fpi_lgbm_india_v01.pkl"
        metadata_path = output_dir / "fpi_lgbm_india_v01_metrics.json"
        joblib.dump(model, model_path)
        metadata = {key: value for key, value in metrics.items() if key != "model"}
        metadata["saved_at"] = datetime.now(timezone.utc).isoformat()
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return model_path


def main():
    """CLI entry point: python -m backend.model.train"""
    import argparse

    parser = argparse.ArgumentParser(description="SlopeSense Model Trainer")
    parser.add_argument("--download", action="store_true", help="Download NASA GLC events")
    parser.add_argument("--epochs", type=int, default=300, help="LightGBM epochs")
    parser.add_argument("--negative-ratio", type=int, default=5, help="Negative sample ratio")
    parser.add_argument("--output", type=str, default="data/model", help="Output directory")
    args = parser.parse_args()

    trainer = ModelTrainer()

    if args.download:
        print("Downloading NASA Global Landslide Catalog for India...")
        events = trainer.download_nasa_glc()
        print(f"  Found {len(events)} events in India")
        if len(events) < 10:
            print("  Too few events — building training set from synthetic defaults")
            import pandas as pd
            events = pd.DataFrame({
                "lat": [11.583, 10.15, 13.05, 9.58, 12.92],
                "lon": [76.083, 77.15, 80.25, 76.25, 75.55],
                "event_date": pd.to_datetime([
                    "2024-07-30", "2023-08-15", "2021-12-18", "2019-08-08", "2024-06-22",
                ], utc=True),
            })

        print("Building training dataset...")
        X, y = trainer.build_training_dataset(events, negative_ratio=args.negative_ratio)
        print(f"  X: {X.shape}, y: {y.sum()} positives / {(y == 0).sum()} negatives")

        print("Training LightGBM model...")
        metrics = trainer.train_and_evaluate(X, y, epochs=args.epochs)
        print(f"  AUC: {metrics['auc']:.4f}")
        print(f"  Precision@0.65: {metrics['precision_at_065']:.4f}")
        print(f"  Recall@0.65: {metrics['recall_at_065']:.4f}")
        print(f"  F1@0.65: {metrics['f1_at_065']:.4f}")

        output_path = trainer.save_model(metrics["model"], metrics, output_dir=Path(args.output))
        print(f"  Model saved to: {output_path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
