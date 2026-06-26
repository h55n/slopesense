"""CLI for training and saving the SlopeSense LightGBM FPI model."""

import argparse
from pathlib import Path

from backend.model.train import ModelTrainer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-glc", action="store_true", help="Download NASA GLC India events")
    parser.add_argument("--events-csv", type=Path, help="Local CSV with lat, lon, event_date")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path("data/model"))
    args = parser.parse_args()

    trainer = ModelTrainer()
    if args.download_glc:
        events = trainer.download_nasa_glc()
    elif args.events_csv:
        import pandas as pd

        events = pd.read_csv(args.events_csv)
        events["event_date"] = pd.to_datetime(events["event_date"], utc=True)
    else:
        raise SystemExit("Provide --download-glc or --events-csv")

    X, y = trainer.build_training_dataset(events)
    metrics = trainer.train_and_evaluate(X, y, epochs=args.epochs)
    model_path = trainer.save_model(metrics["model"], metrics, args.output)
    printable = {key: value for key, value in metrics.items() if key != "model"}
    print({"model_path": str(model_path), **printable})


if __name__ == "__main__":
    main()
