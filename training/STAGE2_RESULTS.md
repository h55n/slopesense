# Stage2 diagnostic research, October11 2026

Copernicus public2021 DSM joins:534 of544 events,2072 matched rows. Ten tile-border
windows fail closed, recorded by event ID in terrain_errors.json. Native30m pixels
in35x35 windows are differentiated with local metric spacing; edge slopes excluded.
Elevation, slope mean/p90 and relief added, fixed logistic C1 and held-out partitions.
Release postdates events, includes vegetation/buildings; not pre-event evidence.
Initial patch bytes were hashed but not retained; STAC assets/window metadata cached
for redownload. Updated extractor saves raw patch NPY for subsequent uncached work.

Validation threshold: NONE satisfies90% recall with<=10% matched-background FPR.
Research screen fails. At unchanged0.5: temporal recall19.9%, background FPR4.83%,
ROC-AUC0.7915, PR-AUC0.5197, Brier0.1540; spatial recall28.6%, FPR4.28%,
ROC-AUC0.7505, PR-AUC0.5400, Brier0.1586. Full metrics/calibration/bootstrap retained.
No test-tuned threshold or model search. Case-control scores are NOT population
failure probabilities. Holdouts were viewed in Stage1, so these are not a fresh
independent confirmation. Calibration-set threshold selection is optimistic too.

NDVI pilot: official ORNL MOD13Q1 bands/dates/subsets respond without authentication.
250m16day composites, start<=target-35days, reliable pixels only, minimum25%patch.
30 event groups requested, only3 have acceptable quality in ALL matched windows.
Do not relax QA after observing these results. Excluding90% would create major
coverage/selection bias;3 groups cannot support train/calibration/test evaluation.
No NDVI model fit or invented values. Source raw responses and rejection log retained.
Products are reprocessed retrospectively, not proof of historical warning availability.

Authoritative catalog still unresolved: Bhukosh official page states registration
needed to download; Bhusanket advertises field-validated inventory but shows unable
to fetch data, direct TLS connection failed. No credentials/accounts created. The
NASA mirror remains unverified. Research code/results only; production scoring,
publication and notification paths remain unchanged and disabled.

Sources:
- https://registry.opendata.aws/copernicus-dem/
- https://copernicus-dem-30m.s3.amazonaws.com/readme.html
- https://earth-search.aws.element84.com/v1/collections/cop-dem-glo-30
- https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf
- https://modis.ornl.gov/data/modis_webservice.html
- https://modis.ornl.gov/documentation.html
- https://daac.ornl.gov/LAND_VAL/guides/MODIS_Web_Service_C6_V2.html
- https://bhukosh.gsi.gov.in/Bhukosh/MapViewer.aspx
- https://bhusanket.gsi.gov.in/
