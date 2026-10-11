# Stage2 screening protocol, before viewing expanded-feature test results

This is a research screening bar, not a validated public-safety standard.
Keep previous temporal/spatial partitions; fit transforms on training only.
Weather variables, logistic C1 and Platt method stay fixed. Add static elevation,
local slope mean/p90 and relief from publicly licensed DEM native pixels.
Select threshold using2013 validation data only: highest threshold achieving>=90%
validation sensitivity, with matched-background false-positive fraction<=10%.
If no threshold exists, screening fails without searching test thresholds.
Report both unchanged0.5 and validation-selected threshold on both held-out tests.
Research screening additionally requires test sensitivity>=90%, its event-group
bootstrap95% lower bound>=80%, matched-background FPR<=10%, and calibrated Brier
better than constant training prevalence in EACH test partition. Report calibration
bins and sample design. No test-driven feature/model/threshold optimization.

Independent publication gates: official dated inventory provenance/license;
verified event and non-event monitoring/base rates; pre-event feature availability
(including terrain vintage); operational forecast/source compatibility; regional
external prospective validation and competent safety review. Every gate must clear
before real-warning publication. Case-control success cannot establish calibrated
population probabilities or operational false-alarm rates. Existing tests have
already been viewed, so Stage2 tests are NOT a fresh independent confirmation.

Static features are shared by each event and its matched background locations.
They cannot alone resolve time-varying warning triggers. Copernicus DEM2021 is
post-event for2007-2016 candidates and includes canopy/buildings. It is suitable
for diagnostic research only until pre-event terrain/source-compatibility is shown.
Do not pretend it was measured at event time or independent of landslide changes.

NDVI extension, before any NDVI-expanded test result: ORNL MOD13Q1 250m16day
composites; select latest composite START<=target minus35days (ends<=minus20days).
Use fixed1km above/below and left/right subset (~2km square). Accept only NDVI
valid[-2000,10000] and pixel_reliability0 (good); require>=25% of patch pixels.
Scale0.0001, retain mean and quality fraction/raw metadata. No cloudy-pixel zero
fill. Exclude entire event group if ANY matched row lacks NDVI, reporting selection
counts/bias. Reprocessed historic products remain hindsight, not proof of historic
operational availability. Same logistic C1, splits and threshold rules.

[All research stages, source licenses and artifacts](INDEX.md) | [Repository overview](../README.md)
