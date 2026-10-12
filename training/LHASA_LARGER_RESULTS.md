# Larger NASA retrospective comparison

[Frozen protocol](LHASA_LARGER_PROTOCOL.md) | [Processing audit](LHASA_LARGER_PROCESSING.md) | [Recent-years feasibility](RECENT_YEARS_FEASIBILITY.md)

84of90frozen groups/324real rows completed. Six whole-group exclusions because
an original background date precedes true SMAPcoverage; no score-based replacement.
29events calibration,27selection,28comparison, spatial and group disjoint.

No selection threshold achieved90%recall/<=10%sampled-backgroundFPR.
The research screen failed. No production-warning change.

| Comparison at fixed0.5 | RawNASA | Sampled-data Platt score |
|---|---|---|
| Caught reported events | 10/28 (35.7%) | 18/28 (64.3%) |
| Background dates flagged | 1/84 (1.19%) | 7/84 (8.33%) |
| AUC | 0.8529 | 0.8529 |
| PR-AUC | 0.7242 | 0.7242 |
| Brier | 0.1437 | 0.1367 |

Constant calibration-prevalence Brier0.1879. Calibrated recall95%event-bootstrap
46.4-82.1%, sampledFPR1.19-16.7%. Platt logitC1slope0.442204/intercept0.857165.
Calibration/selection choice stored before comparison metrics read.

Post-hoc sampled-data calibration, not independent safety validation: known/unresolved
NASAtraining overlap, unverified non-event dates/base rates, historical reprocessing,
product-version differences, event-day rainfall/no lead time. Do not display64.3%as
operational accuracy or calibrated population probability. It missed10of28events.

Study archive retains sourceZIPURLs/hashes, cropped liquidrainrasters, exactNASAstatic
hashes, rawSMAPresponses including rejected400attempts, before-prediction manifest,
split membership, predictions, calibrator parameters and full metrics. NASAweights
retain NOSA1.3/NASAattribution, not rebranded as our own trained model.

Publication path: the full study archive is
[training/artifacts/lhasa-larger-comparison.zip](https://github.com/h55n/slopesense/blob/master/training/artifacts/lhasa-larger-comparison.zip).
These are retrospective research results only. They are not a real-world failure probability and not an advance warning.

[All studies](INDEX.md)
