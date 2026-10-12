# Larger retrospective NASA comparison and sampled-data calibration

Frozen October12 2026 before new model predictions. This is post-hoc research,
not independent validation: NASA's pretrained2015-2018training overlap is known,
current2.1membership unresolved, and previous SlopeSense tests have been viewed.
No production safety gate can clear from this comparison.

Eligible: official Stage3complete terrain events from2015-04-05onward, original
whole-group backgrounds. Exclude all five prior NASA pilot groups. Assign spatial
groups via SHA256('lhasa-larger-v1:'+spatial_group)mod3 to calibration, threshold
selection and comparison. Within each partition choose first30event groups by
SHA256('lhasa-order-v1:'+event_id), fixed before inference. Preserve all original
rows. Group/spatial disjointness assertions required. Total planned90events,
roughly360rows. Whole-group exclusions only for genuinely missing/invalid inputs,
never low/high model score; no replacement chosen after results.

Exact NASA static grids and original pinned300tree weights. Historic IMERG actual
Early current day and Late two preceding days liquid rainfall, actual archive
version logged,0.1mm divided by10, rain normalized by exact NASA99thpercentile;
SMAP total-profile wetness nearest upstream3hour interval toD-2days-1hour. Never
Finalrain/ERA5substitutes. Cropped raw raster caches with original ZIP source/hash
retained, no silent zeros/sentinels or unavailable-date reconstruction.

Prespecified calibration: logistic Platt fit on clipped logit(rawNASA score),
calibration partition only, regularizedC1. Threshold chosen only on selection:
highest threshold with>=90%reported-event recall and<=10%sampled-backgroundFPR.
If none, threshold absent and failed screen reported. Comparison untouched during
calibrator/threshold selection. Report raw/calibrated fixed0.5 and selected-threshold
metrics, AUC/PR/Brier/constant baseline and event-group bootstrap95%intervals.
No tuning on comparison results, no search over alternative calibrators.

Calibration is for the sampled case-control distribution only, not population
probability/base rates. Current-day rainfall implies nowcast, no warning lead time.
A nominal screen pass still does not prove independence/safety/operational accuracy.
Website may show real timestamped observations and clearly labeled research results,
not official warnings, calibrated real-world probabilities or prospective forecasts.
