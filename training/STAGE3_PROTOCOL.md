# Stage3 official-source protocol, frozen before fitting

October11 2026. Source: NASA COOLR public Reports Points current /portal service.
1741India-designated reports downloaded;775nonmissing-date rain-trigger reports at
catalog<=5km accuracy. Country and precision are reported claims, not field proof.
Deduplicate calendar-date/coordinate and event_id; preserve all source IDs/logs.
Event timestamps stored UTC, but local event timezone/exact-time interpretation
not documented. Calendar features end two UTC days before reported day. Do not
claim exact lead time. All India reports exclude nearby background windows.

Feature/model choices fixed: ERA5 precipitation3/7/14day and shallow-soil3/14day;
Copernicus2021DSM elevation, slope mean/p90 and relief. Logistic standardized C1,
separate Platt calibration. NDVI omitted due failed coverage, no relaxed QA.
Record post-event DSM on historic events; even2017-2022event terrain vintage varies
and2021release is not the acquisition date. Historical ERA5 is hindsight.

Partitions determined ONLY by event year and fixed hash of rounded1degree group:
- Train:<=2012, nonspatialholdout.
- Platt calibration:2013, nonspatialholdout.
- Threshold selection:2014, nonspatialholdout, distinct from calibration.
- Legacy temporal diagnostic:2015-2016, nonspatialholdout (previously viewed in
  earlier model work; NEVER independent confirmation).
- Clean temporal confirmation:>=2017, nonspatialholdout.
- Clean spatial confirmation:>=2017, fixed20% spatial groups (SHA256 modulo5).
- Older spatial holdout:<=2016, diagnostic only, never fitting/selection.

No row/event group crosses partitions. Whole-group fail-closed exclusion if any
weather row missing or terrain unavailable. Freeze split manifest BEFORE fitting.
Some>=2017reports may share locations/storms with earlier reports; temporal test
is not spatial independence. Spatial test must have groups absent from training.

Highest threshold meeting>=90%recall and<=10%matched-background FPR on2014only.
If absent, screen fails; no test-threshold search. Report unchanged0.5 too.
Research screen requires EACH clean confirmation set recall>=90%, event-group
bootstrap95%lower recall>=80%, FPR<=10%, Brier lower than constant training
prevalence. Minimum30positive events EACH; otherwise insufficient evidence,
not pass.300fixed-seed event-group bootstrap draws; report calibration bins.
Model/feature choices are already informed by Stage1/2; clean confirmations here
are unseen outcomes of the frozen Stage3 fit, not an untouched research program.

Independent gates remain: monitored non-events/population base rates, prospective
operational weather-source validation, defensible pre-event inputs, source/location
and time audits, competent safety review. Research screen is not a regulatory or
expert-established safety standard. Every gate must clear before real warnings.
Research fitted artifact stays separate from production. No paid/card paths.

[All research stages, source licenses and artifacts](INDEX.md) | [Repository overview](../README.md)
