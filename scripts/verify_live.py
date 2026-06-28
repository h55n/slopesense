"""
SlopeSense — Live Verification CLI

Runs the live verification pipeline against recent real-world landslide reports.
"""

import asyncio
import argparse
import sys
from pathlib import Path
import json

# Force UTF-8 output on Windows to avoid cp1252 UnicodeEncodeError with emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.model.live_verification import LiveVerificationEngine

def print_report(results):
    print("\n" + "="*60)
    print("SLOPESENSE LIVE GROUND-TRUTH VERIFICATION")
    print("="*60)
    print(f"Total Reports Evaluated : {results['total_reports']}")
    print(f"True Positives (Alerts) : {results['true_positives']}")
    print(f"Missed (Normal)         : {results['missed']}")
    print(f"Model Accuracy          : {results['accuracy_pct']}%")
    print("-" * 60)
    print(f"{'REPORT ID':<15} | {'DATE':<12} | {'FPI':<6} | {'TIER':<10} | {'SUCCESS'}")
    print("-" * 60)
    for d in results["details"]:
        date_str = d['date'][:10]
        success = "✅ YES" if d['success'] else "❌ NO"
        print(f"{d['report_id']:<15} | {date_str:<12} | {d['model_fpi']:<6.3f} | {d['model_tier']:<10} | {success}")
    print("="*60 + "\n")

async def main():
    parser = argparse.ArgumentParser(description="Verify SlopeSense against real-world reports")
    parser.add_argument("--days", type=int, default=30, help="Number of days back to verify")
    args = parser.parse_args()
    
    engine = LiveVerificationEngine()
    results = await engine.run_verification(days_back=args.days)
    
    print_report(results)
    
    # Save to file
    out_dir = Path("data/verification")
    out_dir.mkdir(exist_ok=True, parents=True)
    out_file = out_dir / "latest_verification.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Detailed verification log saved to {out_file}")

if __name__ == "__main__":
    # Fix event loop policy for Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
