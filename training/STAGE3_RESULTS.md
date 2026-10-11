# Official-source Stage3 results, October11 2026

Research screen failed. No2014threshold meets90%recall at<=10%matched-background
false positives. Scores classify sampled reported events, not population failure
probabilities. Production warnings remain blocked.

Official current NASA COOLR:1741India-designated rows,775rain/<=5km/date candidates,
770after exact date/location/event ID dedup.768complete weather groups after two
groups excluded for three read timeouts.752terrain-complete groups/2887rows after
16terrain failures. All whole-group exclusions kept; no cloudy NDVI or missing
weather/terrain fill. Labels/background exclusions rebuilt from official rows.
Provider raw request caches reused only by exact model/location/date parameter hash.
Some reused terrain patches retain source/window/hash but not initial raw NPY bytes;
newly fetched patches have NPY. The2021DSM is not proved pre-event terrain.

Frozen splits after coverage: train178events/683rows; Platt2013 69/258; threshold
2014 31/116; unseen temporal2017+172/635; unseen spatial2017+34/136. Old diagnostic
sets156/620 and112/439, previously viewed, never treated as clean confirmation.
Split manifest saved and SHA256edc0503e23d96ef14a0aa4757d86df7fd6988ab05343f2a6db8950fafd72a152
before fitting. Test predictions only evaluated once; no model/threshold tuning.

At unchanged0.5 on temporal confirmation: recall27.9%, precision57.1%, matched
background FPR7.78%, ROC-AUC0.6566, PR-AUC0.4619, Brier0.1873. Recall event-group
bootstrap95%20.3-35.2%.48events caught,124missed. Spatial confirmation: recall23.5%,
precision47.1%, FPR8.82%, ROC-AUC0.6912, PR-AUC0.3986, Brier0.1783. Recall95%
11.8-38.2%.8events caught,26missed. Spatial sample small and intervals broad.
Report full calibration bins/metrics and constant baseline in artifact metrics.json.

Current official NASA schema differs from old mirror.1504event IDs overlap,1502
calendar dates match,1482latitudes/1487longitudes match. It does not byte-verify the
legacy CSV. Use new official export and preserve old provenance label unchanged.
Official layer date storage is UTC, not proof of local reported event timezone or
true warning lead time. Event/source/country/accuracy fields remain catalog claims,
not independent field verification. Global/frame monitored non-events missing.

Independent warning gates remain failed: true non-event/base rate monitoring,
prospective operational weather validation, defensible pre-event terrain, exact
local time/source precision audits, competent safety review. License permits use,
not a warranty of safety. Source/permission/NOTICE in catalog archive.

No Froude/Petley augmentation: fatal-event-only bias and row-specific precision
unavailable. Retained623India-designated dated rainfall-fatal points as corroboration
lead, licensed OGLv2 by actual layer metadata. NDVI remains out:3of30complete
quality-passed event groups. No new paid/auth path necessary.

Sources:
https://gis.earthdata.nasa.gov/portal/rest/services/Landslides/COOLR_Reports_Points/FeatureServer/0
https://gis.earthdata.nasa.gov/portal/apps/experiencebuilder/experience/?id=a7b17eff544a4ce5ae045c32dbb99f7b
https://registry.opendata.aws/copernicus-dem/
https://open-meteo.com/en/docs/historical-weather-api
