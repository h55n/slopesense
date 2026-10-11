# Real-data training workstream

Status October 11, 2026: source discovery and quality audit, NOT trained or validated.
No scientific validation claims or operational warnings may follow from this stage.

## Intended target

Reported rainfall-triggered landslide occurrence at a specified place/day. Exclude
GLOF, earthquake, rock/ice avalanches, imprecisely dated imagery-only occurrences.
Catalog reporting bias and unreported landslides mean an absent report is not a
confirmed non-event. Until a defensible sampling frame/base rate is available,
calibration applies only to sampled reported-event classification, not real-world
landslide failure probability.

## Sources and vintage

- Official NASA GLC portal: https://data.nasa.gov/dataset/global-landslide-catalog-export
  Explicit snapshot as of March 7, 2016. Metadata updated 2025 does NOT establish
  current event coverage. Download listed by official metadata currently fails
  TLS/timeout from this execution environment.
- Current NASA COOLR guide: https://gpm.nasa.gov/applications/landslides/coolr
  Reports and event inventories differ. Published Earthdata REST endpoints returned
  404 here; older NCCS service currently network-unreachable. Access remains unresolved.
- https://zenodo.org/records/8169506: southern Sikkim inventory, many entries dated
  by first visible image YEAR, mixes rockfalls; unsuitable for daily calibration.
- https://www.isro.gov.in/Landslide_Atlas_India.html: 1998-2022 seasonal/event/route
  inventory. Total count is not a count of precisely dated rain-triggered events.
- https://bharatlas.com/view/gsi_landslide_inventory: third-party GSI mirror;
  upstream license and exact date-field provenance not yet verified.
- https://zenodo.org/records/7653639: CC BY 4.0 research derivatives of NASA GLC
  (precipitation and fire history). DOI/source lineage verified; event fields and
  data completeness must be inspected before adopting a derived inventory.
- https://open-meteo.com/en/docs/historical-weather-api: ERA5/ERA5-Land reanalysis,
  not a historical forecast issued at warning time. Pin dataset/model and timestamps.
  https://open-meteo.com/en/terms: current noncommercial-only free API terms.

## Experimental protocol

1. Preserve raw data, exact URLs, retrieval time, checksums, licensing and citations.
2. Filter by documented trigger/date/location precision. Deduplicate by event and
   geographic cluster; retain exclusion log, do not infer missing dates.
3. Build real dated weather joins, no fabricated feature vectors or zero fill.
   All features must end before the prediction cutoff. Archive reanalysis supports
   a hindcast association study, not proof of 24h operational warning performance.
4. Sample background dates from a documented frame, exclude catalog event windows
   within geographic neighborhoods. Label background as unreported, not confirmed safe.
5. Hold out whole time periods and spatial/event clusters. Fit transformations on
   training only; calibrate with a separate held-out set; untouched test set remains
   untouched by feature/threshold choice. Report sample counts and split manifests.
6. Baseline logistic model before gradient boosting. Report PR-AUC, ROC-AUC, Brier,
   calibration curve, precision/recall, false-positive fraction, CIs and sensitivity
   to reporting bias/background sampling. Do not choose thresholds on test outcomes.
7. Publish real reproducible artifacts and failure cases, including null/poor results.
   Enable operational scoring only after peer review/appropriate validation and
   deployment-source compatibility. Until then production warning publication stays blocked.

Legacy backend/model/train.py generates synthetic negative features and uses random
train/test splits. It is not a valid training/calibration route for this workstream.


## Historical-weather pilot findings

The candidate GitHub mirror at
https://github.com/erikanagamine/autonomousdatabase contains 11,033 records,
1,265 India rows; after rain-trigger/<=5km accuracy/date filters and one exact
location/date duplicate removal, 544 candidates remain (2007-2016). Mirror file
commit 6487003c8dbb28baaef1c986287bac7429621cf1; SHA256
2c4898899dd4f373c4320e121c5b655ebb5394d431fa42e57ec4828d07d48b04.
This lineage remains UNVERIFIED against official NASA bytes. No exact event-time
values exist in these candidates. Country/date/source links are dataset claims,
not independently confirmed event observations.

Pilot ERA5-Land precipitation_sum returned nulls while soil was present; rejected
without filling. ERA5 explicitly selected instead (0.25 degree, approximately28km).
It returns real provider reanalysis precipitation+soil. Script caches raw responses
with URLs/timestamps and rejects invalid/missing coverage. Features end two calendar
days before the candidate event date, which reduces day/time uncertainty but does
not prove exact lead time or real-time availability. Calendar event timezone is
not reliably documented. These are hindsight reanalysis associations only.

Background dates are fixed-seed, within +/-90 days of an event and same calendar
year, with all India catalog reports used to exclude nearby +/-30day event windows.
This is a matched case-control design, not population-base-rate calibration. Dates
without reports may contain unreported landslides. Scores cannot be marketed as
real-world failure probabilities. No zero-valued or random synthetic feature vectors.

[All research stages, source licenses and artifacts](INDEX.md) | [Repository overview](../README.md)
