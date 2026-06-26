"""
SlopeSense — Retrospective Validation CLI

Run the FPI model on historical events and publish results.

Usage:
    python -m scripts.retrospective                   # all 6 events
    python -m scripts.retrospective --event wayanad_2024
    python -m scripts.retrospective --synthetic       # use synthetic data (no NASA credentials needed)
    python -m scripts.retrospective --list            # list available events
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows to avoid cp1252 UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="SlopeSense Retrospective Validation")
    parser.add_argument("--event", type=str, help="Run single event by ID")
    parser.add_argument("--synthetic", action="store_true", default=True,
                        help="Use synthetic data (no NASA credentials required)")
    parser.add_argument("--real", action="store_true",
                        help="Use real satellite archive data (requires NASA/Copernicus credentials)")
    parser.add_argument("--list", action="store_true", help="List available events")
    parser.add_argument("--output", type=str, default="data/retrospective",
                        help="Output directory for results")
    args = parser.parse_args()

    from backend.model.retrospective import RetrospectiveRunner, HISTORICAL_EVENTS

    if args.list:
        print("\nAvailable historical events:")
        for e in HISTORICAL_EVENTS:
            print(f"  {e['id']:25s}  {e['name']:35s}  {e['date'][:10]}  Deaths: {e['deaths']}")
        return

    use_synthetic = not args.real

    runner = RetrospectiveRunner()
    runner.OUTPUT_DIR = Path(args.output)
    runner.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.event:
        logger.info(f"Running retrospective for: {args.event}")
        result = runner.run_event(args.event, use_synthetic=use_synthetic)
        from dataclasses import asdict
        print("\n" + "=" * 60)
        print(f"EVENT: {result.event_name}")
        print(f"DATE:  {result.event_date}")
        print(f"DEATHS: {result.deaths}")
        print(f"\nFPI @ T-24h: {result.fpi_t24:.3f if result.fpi_t24 else 'N/A'}")
        print(f"FPI @ T-12h: {result.fpi_t12:.3f if result.fpi_t12 else 'N/A'}")
        print(f"FPI @ event: {result.fpi_at_event:.3f if result.fpi_at_event else 'N/A'}")
        print(f"\nTarget FPI:  {result.target_fpi}")
        print(f"Flagged @T-24h: {'✅ YES' if result.flagged_at_t24 else '❌ NO'}")
        print(f"Lead time: {result.lead_time_hours}h" if result.lead_time_hours else "Lead time: Not flagged")
        print("=" * 60)
    else:
        logger.info("Running retrospective validation for all 6 events...")
        summary = runner.run_all(use_synthetic=use_synthetic)

        print("\n" + "=" * 70)
        print("SLOPESENSE RETROSPECTIVE VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Model version: {summary['model_version']}")
        print(f"Run at: {summary['run_at']}")
        criterion_display = summary['pass_criterion'].replace('\u2265', '>=').replace('\u2264', '<=')
        print(f"\nPass criterion: {criterion_display}")
        print(f"Result: {summary['flagged_at_t24']}/{summary['total_events']} flagged at T-24h")
        passed_str = 'PASS' if summary['passed'] else 'FAIL -- recalibration required'
        print(f"Status: {'[OK]' if summary['passed'] else '[!!]'} {passed_str}")
        print("\nEvent results:")
        print(f"  {'Event':<35} {'FPI@T-24h':>10} {'Flagged':>10} {'Lead':>8}")
        print("  " + "-" * 65)
        for r in summary["results"]:
            if "error" in r:
                print(f"  {r['event_id']:<35} {'ERROR':>10}")
                continue
            fpi_str = f"{r['fpi_t24']:.3f}" if r.get("fpi_t24") else "N/A"
            flagged = "✅ YES" if r.get("flagged_at_t24") else "❌ NO"
            lead = f"{r['lead_time_hours']}h" if r.get("lead_time_hours") else "—"
            print(f"  {r['event_name']:<35} {fpi_str:>10} {flagged:>10} {lead:>8}")

        print("\n" + "=" * 70)
        output_path = runner.OUTPUT_DIR / "summary.json"
        print(f"Full results saved to: {output_path}")


if __name__ == "__main__":
    main()
