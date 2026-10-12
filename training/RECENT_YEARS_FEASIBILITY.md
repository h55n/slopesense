# Recent-years training feasibility, October12 2026

Current official NASA COOLR India layer was re-read live after the user's request
to train on the last2-5years.1741India-tagged reports; only3dated2021-2026:

| Year | Reports | Rain-triggered /1kmeligible |
|---|---|---|
| 2021 | 2 | 2 |
| 2022 | 1 | 1 |
| 2023-2026 | 0in this source | 0 |

Taliye21029, Mizoram20598, Maliyekkal21212. Latest event29August2022.
Server-side date-filter count independently returned3. These are all LRC reports.
Source: https://gis.earthdata.nasa.gov/portal/rest/services/Landslides/COOLR_Reports_Points/FeatureServer/0

Three positive groups cannot sustain a defensible train/calibration/threshold/test
split. Do not train a convincing-looking recent-years model on them. Zero rows
in this source does not mean zero landslides, and a source label is not precision,
base-rate or local-event-time verification. Recover a larger independent recent
inventory first. GSI dated machine-readable inventory/reuse permission was requested,
not granted; no GSI data has been reproduced. Public PDF counts are not training labels.

IMERG/SMAP availability cannot replace missing event labels. The separately frozen
90eventhistorical pretrained comparison stays unchanged: it is post-hoc with known
or unresolved NASA training overlap. Even a good sampled score cannot be called
prospective performance or calibrated real-world failure probability.

Real timestamped weather/source observations can update the website independently;
keep any research nowcast distinct from operational warnings and lead-time claims.

Current source-access checks succeeded: PPS Early07C October2026directory lists
October1-11daily data; NASA CMR returns SMAP8minor8011granule for October8/9.
This confirms recent input access, not complete uninterrupted2021-2026coverage.
A full gap audit is unnecessary until enough real dated event labels are obtained.
