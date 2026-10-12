# Research trace: data -> protocol -> results

No stage passed the research screening bar. None is an operational warning model.
Sample case-control scores are not calibrated real-world landslide probabilities.

| Stage | Data and protocol | Results | Reproducible archive |
|---|---|---|---|
| 1: weather baseline | [Source audit and protocol](README.md), [inventory audit](audit_inventory.py), [weather join](build_weather_dataset.py), [evaluator](evaluate_baseline.py) | [Exploratory result](RESULTS_EXPLORATORY.md) | [Stage1 dataset/caches/model/metrics](artifacts/exploratory-weather-baseline.zip) |
| 2: terrain + NDVI pilot | [Frozen protocol](STAGE2_PROTOCOL.md), [terrain join](add_terrain.py), [quality-gated NDVI](add_ndvi.py), [evaluator](evaluate_stage2.py) | [Terrain/NDVI result](STAGE2_RESULTS.md) | [Stage2 archive](artifacts/stage2-terrain-ndvi.zip) |
| 3: official NASA source | [Frozen protocol](STAGE3_PROTOCOL.md), [official audit](prepare_official.py), [weather join](build_official_weather.py), [evaluator](evaluate_official.py) | [Official-source result](STAGE3_RESULTS.md) | [Source catalogs + permission/NOTICE](artifacts/stage3-official-catalogs.zip), [training archive](artifacts/stage3-training.zip) |

| 4: post-hoc boosting comparison | [Frozen protocol](STAGE4_PROTOCOL.md), [evaluator](evaluate_technique.py) | [Post-hoc results](STAGE4_RESULTS.md) | [Stage4 archive](artifacts/stage4-comparison.zip) |

Archive contents are source data, raw provider caches, exclusion logs, manifests,
frozen splits, research-only fitted models, predictions and full metrics. Stage3
source archive includes `nasa-official-stage3/PERMISSION.txt`, `NOTICE.txt`,
`source_item_metadata.json`, `schema.json`, `manifest.json` and `audit.json`.
The secondary `fatal-landslide-pilot` directory includes dataset metadata,
`OGL-v2.txt` and `NOTICE.txt`. ZIP paths are archive-relative, not separate files.
Do not treat repository Apache2 license as overriding any source-data/model license.

## Sources and use conditions

- [Official current NASA COOLR report layer](https://gis.earthdata.nasa.gov/portal/rest/services/Landslides/COOLR_Reports_Points/FeatureServer/0).
  [Actual layer metadata and reuse permission](https://gis.earthdata.nasa.gov/portal/sharing/rest/content/items/b1b68a19b51342bf83260fbb3d9588f5?f=json).
  Free reuse/derivation/distribution with permission copy, marked changes and
  retained notices. Catalog reports are not a complete monitored population.
- [Official NASA legacy export](https://data.nasa.gov/dataset/global-landslide-catalog-export).
  Stage1/2 third-party mirror was not byte-verified; Stage3 replaces it with the
  current official source. Do not retroactively relabel old data as verified.
- [Open-Meteo historical API](https://open-meteo.com/en/docs/historical-weather-api),
  [terms](https://open-meteo.com/en/terms): free API noncommercial limits apply.
  ERA5 hindsight reanalysis, not issued forecast or local gauge ground truth.
- [Copernicus DSM source/release](https://registry.opendata.aws/copernicus-dem/),
  [license](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf).
  Native30m DSM includes vegetation/buildings;2021release not proved pre-event.
- [ORNL MODIS API](https://modis.ornl.gov/data/modis_webservice.html): historic
  completed composites and good-pixel QA only.3of30complete groups passed; omitted.
- [Froude/Petley layer license](https://www.arcgis.com/sharing/rest/content/items/e69ab992a3144fdc9a13bad633f08ea1?f=json),
  [OGLv2](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/2/),
  [paper](https://nhess.copernicus.org/articles/18/2161/2018/).
  Fatal-event-only corroboration, not training augmentation or base rates.
- [GSI Bhusanket terms](https://bhusanket.gsi.gov.in/terms.html): prior reproduction
  permission requested, not yet granted. No GSI dataset bundled.

## Interpretation

Stage1/2 tests informed later work. Stage3's2017+confirmation outcomes had not been
viewed before its frozen fit, but they have now been evaluated. Reusing them for a
new pretrained comparison is post-hoc comparison, not a new independent test.
Official source provenance does not prove source accuracy, precise event timezone,
base rates, real non-events, prospective source compatibility or safety fitness.
Research screen success, were it to occur, would not clear those independent gates.

[Main README](../README.md) | [Pretrained-model research](PRETRAINED_MODELS.md)

## NASA compatible-input research

[Larger frozen comparison](LHASA_LARGER_PROTOCOL.md) -> [processing](LHASA_LARGER_PROCESSING.md) -> [results](LHASA_LARGER_RESULTS.md).
[Recent-years inventory feasibility](RECENT_YEARS_FEASIBILITY.md). No safety gate passed.
