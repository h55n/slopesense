# Weather-only exploratory baseline, October 11, 2026

Status: real computed research results, NOT a validated warning model. Do not deploy
these sampled-classification scores as Failure Probability Index or government alerts.

544 quality-filtered candidate reported rainfall events and 1,568 matched background
windows produced 2,112 feature rows. Inventory is an unverified third-party NASA GLC
mirror, 2007-2016, described in README. Weather is actual provider ERA5 reanalysis
(~28km), not observed gauge/satellite ground truth or historical issued forecasts.
No random/synthetic feature negatives or zero fill. Final request/coverage errors:0.

Baseline: standardized logistic regression, fixed C=1, no tuned hyperparameters;
training <=2012 (689 rows/179 events); separate2013 sigmoid/Platt calibration
(270 rows/72 events). Temporal test >=2014 (706 rows/179 events). Fixed20% of1degree
spatial groups held out from both training and calibration (447 rows/114 events).
All event/background groups kept together. Features: preceding3/7/14day precipitation
and3/14day mean0-7cm soil moisture, ending two calendar days before target date.

| Untouched test partition | ROC-AUC | PR-AUC | Brier | Constant-sample baseline Brier | Recall at fixed0.5 | Precision at0.5 | Background false-positive fraction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Temporal |0.792|0.512|0.154|0.189|24.6%|57.1%|6.3%|
| Spatial |0.754|0.545|0.157|0.190|27.2%|72.1%|3.6%|

Event-group bootstrap95% ranges (300 fixed-seed resamples): temporal ROC-AUC0.756-0.823,
PR-AUC0.463-0.574, Brier0.145-0.165; spatial ROC-AUC0.713-0.802,
PR-AUC0.469-0.636, Brier0.145-0.169. These ranges describe this sampling design,
not national operational warning reliability. Spatial/storm correlation may remain.

The baseline misses roughly three quarters of reported events at the predetermined
threshold. Its apparent discrimination is not enough for safety-critical warnings.
No test-threshold tuning was performed to conceal that result. Earlier230-event
partial metrics were inspected for progress; no features/model/threshold were changed
based on them, but this should still be disclosed when treating the full evaluation
as evidence. More rigorous preregistered external validation is needed.

## Blocking scientific gaps

- Authoritative inventory bytes/provenance/license confirmation unresolved.
- No exact event time or reliable timezone; cannot prove exact24h warning lead time.
- Missing reports do not prove no landslide. Matched case-control calibration is not
  population-base-rate failure probability, so published probabilities are not valid.
- ERA5 hindsight reanalysis differs from operational provider forecasts and latency.
- No verified terrain, vegetation, susceptibility/lithology features in this baseline.
- Need independent dated regional inventories/non-event monitoring frames, event/storm
  cluster holdouts, target-base-rate correction, threshold selection on validation
  only, and review of miss/false-alarm costs before any operational publication.

Production warnings remain blocked, retrospective API remains not_validated. These
results are research artifacts only, not replacements for official safety advice.

[All research stages, source licenses and artifacts](INDEX.md) | [Repository overview](../README.md)
