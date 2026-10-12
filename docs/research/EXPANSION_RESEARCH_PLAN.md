# SlopeSense: India coverage and next research plan
12 October 2026. Research plan recorded before implementation. See INDIA_EXPANSION.md for the subsequently implemented 22-point scope.

## Decision
Expand factual provider snapshots across the19states/UTs identified by GSI, then replace town-centre representatives with susceptibility-footprint/site anchors as official geometry becomes available. Build a separate experimental physical-feature dataset. Use global landslide evidence to enlarge development/calibration data, but report India performance only on untouched India evidence. Do not unlock public warnings or describe sampled scores as failure probabilities.

## Coverage
GSI's August2025 parliamentary answer names19states/UTs with landslide-prone mapped areas. It reports4.3lakh square kilometres mapped,91,000historical records and33,904field-validated records. These totals do not establish that exact-day recent rainfall labels are downloadable today. Official recovery through NGDR/Bhukosh/Bhusanket remains the highest-value route.

Proposed representative places: Araku Valley(AP), Itanagar(Arunachal), Haflong(Assam), Valpoy(Goa), Shimla(HP), Ramban(J&K), Madikeri(Karnataka), Kalpetta(Kerala), Kargil(Ladakh), Mahabaleshwar(Maharashtra), Ukhrul(Manipur), Shillong(Meghalaya), Aizawl(Mizoram), Kohima(Nagaland), Gangtok(Sikkim), Ooty(Tamil Nadu), Ambassa(Tripura), Rudraprayag(Uttarakhand), Darjeeling(West Bengal).

The attached candidate JSON has live-geocoded coordinates, approximate geocode precision and native NASA slope screens. Imphal's basin-centre candidate was rejected(1.99degrees) and replaced with Ukhrul(21.46degrees). Others have slopes6.39-38.15degrees in the NASA native cells. These are screening values, NOT evidence that the exact place is an official high-susceptibility site. Do not claim all major failure points, full-state coverage or district-wide warnings. Preserve existing six points; candidate replacements must not silently move current monitored points. Where they overlap, retain existing IDs and coordinates or expose a separately named new point.

After the baseline, add the remaining named districts in GSI's2025forecast coverage list(21districts), then national susceptibility polygons/high-susceptibility grid cells if legally and technically accessible. Distinguish operational official bulletins from experimental ground-testing bulletins. SlopeSense experimental output must never impersonate either.

## Features and meanings
|Dimension|Verified source/route|Meaning and constraints|
|---|---|---|
|Current rain and antecedent rain|Actual NASA IMERG Early current-day/Late preceding-two-days archive, PPS access already working|Keep NASA LHASA normalization by nativep99 and six-input semantics unchanged. Retain units, versions, raw hashes, pixel footprint and date-window provenance. No Open-Meteo replacement inside NASA inference.|
|Profile wetness|Actual SMAP L4 profile wetness, version8 with historical/current minor versions|Not shallow0-1cm moisture. SMAP begins2015, so earlier full-stack inference unavailable.|
|Slope|Actual NASA native staticSlope.nc4|Existing model requires this exact layer. New30m-derived slope belongs to a separately trained experiment.|
|Elevation/relief/aspect/curvature|Copernicus GLO-30 globalDSM, free license; publicAWSCOG route documented|Includes canopy/buildings, not bare-earthDTM. Verify tiles, nodata, CRS, metres-based derivatives and aggregation footprint before adding features. Retain required adapted-data notice.|
|Soil texture/bulk density|SoilGrids2.0,250m predictions,CC-BY4, six standard depth intervals|Show prediction/uncertainty labels. Depth intervals are sampling layers, NOT soil thickness.|
|Absolute depth to bedrock|Actual legacy2017BDTICM_M_250m_ll.tif,ODbL1.0 per exact metadata/2017FAQ|Live file200 and range206; successfully sampled all19candidates privately. This is predicted bedrock depth, NOT measured regolith or failure-plane depth. Values7.85-110.16m illustrate why it must not be passed blindly into a shallow-slide formula. Separate data license/attribution/derived-database obligations from code license.|
|Material/strength/hydraulic parameters|Site investigations, field measurements or documented validated regional estimates|Not currently available for these points. Cohesion, friction angle, unit weight, conductivity/diffusivity and pore pressure cannot be invented from SoilGrids texture alone.|

### Formulas
For a new terrain experiment, use projected-metre derivatives: slope=atan(sqrt((dz/dx)^2+(dz/dy)^2)); local relief=max(z)-min(z) over declared fixed physical windows. Curvature/aspect must have an explicit convention, datum and nodata handling. Do not mix30mterrain with coarse rainfall as though both resolve individual slopes.

For transient physical stability, USGS TRIGRS provides a documented infiltration/soil-stability framework. Its scientific implementation and assumptions should be reused and benchmarked instead of inventing a weighted percentage formula. A factor-of-safety model needs actual/material-supported cohesion/friction/weight/thickness/hydrology. Until those exist, show descriptive terrain and research covariates, not site FoS or a physical failure probability.

## Inventory feasibility
NASA COOLR live query contains77global reports dated2021onward, including21with blank country names, and3India reports. Latest observed date is18May2025. A full77row extraction confirms64rain-associated reports after normalizing case/labels,19ofthese with blank country names. The first exact-code query found47; Rain, Rainfall, Heavy Rain and Heavy Rainfall explain the additional17. Blank countries require geographic validation; do not silently count them as independent foreign examples. This is a source coverage gap, not absence of landslides.

NewAizawl workbook:19rows,10distinct dates;16rows on7dates in2021-2025. Eight rows share28May2024Remal, two share2July2024, two share30May2025.16coordinates are locality estimates, only3reported coordinates. Quarry, wall, road, rockfall and debris-slide mechanisms are mixed. An official Mizoram release corroborates theRemal date and multiple localities; other rows need cited-source verification. Store storm and location groups, reject out-of-target events and compare with existing inventories before admitting labels. Do not treat19rows as19independent storms.

GLaD4CD offers174global-event information in a294.7MBarchive underCC-BY4. Its source list includesNASA, earthquake events and image-change-detection inventories; it is not automatically a rainfall-day training set or independent ofNASApretraining. Download/extract only needed metadata, audit triggers/date precision/overlap. SouthernSikkim inventory is another lead, but publication year2023does not make its historical mapping dates current event days.

## Iterative modeling protocol
1. Assemble a versioned label ledger with event date and precision, trigger, location uncertainty, source URLs, storm group, duplicate group and priorNASA/LHASAoverlap status. Preserve unavailable fields rather than inventing them.
2. Retain the existing NASA stack as the frozen baseline. Create one prespecified new feature stack and missingness policy. Add physical features only where actual source data pass checks.
3. Split BEFORE new inference by event/storm, time and geography. Development loops may use nested/grouped folds to choose features, weighting and calibration. Global calibration requires country-aware validation and India-specific transfer checks.
4. Freeze a new comparison set of newly verified India events, unseen in previous analyses. Do not recycle the viewed84-event test as independent confirmation. Freeze threshold choice on development/selection data before comparison.
5. Run predict-error-review-calibrate loops only inside development data. Record every feature/configuration, exclusion and iteration; evaluate the final frozen choice once on the untouched comparison. If a new iteration uses its outcomes, that comparison becomes exploratory and needs a fresh future holdout.
6. Report event-recall, sampled-backgroundFPR,ROC/PR, calibration metrics and storm/group bootstrap intervals. Sampled unreported dates are not confirmed negatives; case-controlPlatt calibration is not population failure probability. Establish monitored exposure/verified negatives and prospective timing to claim real-world warning performance.
7. Warning gate remains closed. Last larger study had noselectionthreshold meeting90%recall/<=10%sampledFPR; calibrated comparison64.3%recall at0.5does not qualify. Recall alone would not establish reliability, lead time or acceptable false alerts.

## Implementation and tests, after plan acceptance
- Add a versioned point manifest and provider snapshots without changing research-warning state.
- Unit/integration checks: coordinates/state identities, unique IDs, units, missing values, timezone/date boundaries,provider windows, model-vs-observedlabels, geometry precision, source ages andattribution.
- API contract/UI checks: existing points preserved, allnewpoints selectable, source timestamp perpoint, missingdataexplicit, mobilemap/list accessibility and attribution.
- Research checks: point/gridcoordinate assertions, nofuture-window leakage, exactversionmatch, rain-footprint/cell checks, grouped split overlap zero, frozen threshold/configuration hashed before comparison.
- No paid source, credentials disclosure, unattended cardstep or fabricated fallback. Deployment stays coordinated separately against the current remote frontend.
