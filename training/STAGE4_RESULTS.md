# Stage4 post-hoc technique comparison

[Frozen protocol](STAGE4_PROTOCOL.md) | [All stages](INDEX.md)

Same official rows and splits. No new untouched confirmation. No valid2014threshold,
screen failed; no production warning change. Fixed0.5 diagnostics:

| Split | Recall | Matched-background FPR | AUC | Recall95%event-bootstrap CI |
|---|---|---|---|---|
| legacy_temporal_diagnostic | 0.397 | 0.097 | 0.784 | 0.317-0.465 |
| legacy_spatial_diagnostic | 0.420 | 0.110 | 0.785 | 0.321-0.509 |
| temporal_confirmation | 0.302 | 0.147 | 0.651 | 0.227-0.366 |
| spatial_confirmation | 0.382 | 0.137 | 0.711 | 0.220-0.559 |

[Artifacts including model/data/predictions/full metrics](artifacts/stage4-comparison.zip).
Do not interpret sampled classifier scores as real-world event probabilities.
Added maximum preceding14day rainfall and decay0.85antecedent index; trained a
small class-balanced gradient booster without test-driven parameter search.
This did not meet the recall/false-alarm gate. A new technique must earn new
independent confirmation, not recycle these test scores as unbiased evidence.
