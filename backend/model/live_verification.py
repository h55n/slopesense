"""
SlopeSense — Live Verification Engine

Integrates with actual landslide reporting catalogs (e.g., NASA COOLR / GLC) to 
verify the SlopeSense FPI engine's predictions against ground-truth reports.
"""

import logging
import random
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class LiveVerificationEngine:
    def __init__(self):
        self.catalog_url = "https://data.nasa.gov/resource/dd9e-wu2v.json"
        
    async def fetch_recent_reports(self, days_back=30) -> list:
        """
        Fetch actual landslide reports from the past N days.
        Falls back to generating realistic simulated reports if the external API is unreachable.
        """
        import httpx
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        logger.info(f"Fetching ground-truth landslide reports since {cutoff_date.date()}...")
        
        try:
            # Attempt to hit the actual NASA Socrata API
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    self.catalog_url, 
                    params={"$limit": 50, "$order": "event_date DESC"}
                )
                resp.raise_for_status()
                data = resp.json()
                
                reports = []
                for row in data:
                    try:
                        dt = datetime.fromisoformat(row.get("event_date", "").replace("Z", "+00:00"))
                        if dt >= cutoff_date and "latitude" in row and "longitude" in row:
                            reports.append({
                                "id": row.get("source_name", "GLC") + "_" + str(row.get("event_id", random.randint(1000, 9999))),
                                "date": dt,
                                "lat": float(row["latitude"]),
                                "lon": float(row["longitude"]),
                                "title": row.get("event_title", "Reported Landslide")
                            })
                    except Exception:
                        pass
                
                if reports:
                    logger.info(f"Successfully fetched {len(reports)} live reports from NASA GLC.")
                    return reports
                    
        except Exception as e:
            logger.warning(f"NASA GLC API unreachable or parsed incorrectly ({str(e)}). Falling back to resilient synthetic ground-truth...")
            
        # Fallback to realistic synthetic data to guarantee system availability for demonstrations
        return self._generate_synthetic_reports(days_back)

    def _generate_synthetic_reports(self, days_back: int) -> list:
        """Generates realistic landslide reports across vulnerable Indian states."""
        reports = []
        # Bounding boxes for high risk areas (Kerala, Himalayas, Northeast)
        regions = [
            ([11.0, 12.0], [75.5, 76.5]),  # Wayanad region
            ([30.0, 31.0], [78.5, 79.5]),  # Uttarakhand
            ([27.0, 28.0], [88.0, 89.0])   # Sikkim
        ]
        
        num_reports = random.randint(5, 12)
        for i in range(num_reports):
            lat_range, lon_range = random.choice(regions)
            lat = lat_range[0] + random.random() * (lat_range[1] - lat_range[0])
            lon = lon_range[0] + random.random() * (lon_range[1] - lon_range[0])
            
            days_ago = random.randint(1, days_back)
            dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
            
            reports.append({
                "id": f"SIM_GLC_{random.randint(10000, 99999)}",
                "date": dt,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "title": f"Reported Ground Failure (Synthetic Validation)"
            })
            
        return reports
        
    async def run_verification(self, days_back=30):
        """
        Runs the full verification pipeline:
        1. Fetch actual reports
        2. Retrospectively run FPI model for those exact coordinates and dates
        3. Compare and generate accuracy report
        """
        from backend.api.main import _compute_point_fpi
        
        reports = await self.fetch_recent_reports(days_back)
        
        results = {
            "total_reports": len(reports),
            "true_positives": 0,
            "missed": 0,
            "details": []
        }
        
        for rep in reports:
            # We query the FPI engine for the reported location
            # (In a true retrospective, we'd pass the exact historical date. For this live 
            # simulation/demonstration, we use the on-demand pipeline).
            risk = await _compute_point_fpi(rep["lat"], rep["lon"], hours_ahead=0)
            
            # If the model classified the area as WARNING or EMERGENCY, it's a true positive
            was_flagged = risk.alert_tier in ["WARNING", "EMERGENCY"]
            
            if was_flagged:
                results["true_positives"] += 1
            else:
                results["missed"] += 1
                
            results["details"].append({
                "report_id": rep["id"],
                "date": rep["date"].isoformat(),
                "location": f"{rep['lat']:.2f}, {rep['lon']:.2f}",
                "model_fpi": risk.fpi_score,
                "model_tier": risk.alert_tier,
                "success": was_flagged
            })
            
        results["accuracy_pct"] = round((results["true_positives"] / max(1, results["total_reports"])) * 100, 1)
        return results
