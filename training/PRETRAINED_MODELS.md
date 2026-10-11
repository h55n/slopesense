# Published-model search, October11 2026

Real small weights exist. They are not automatically compatible with this project.
No external pretrained model has been validated here or installed in production.
NASA license accepted for research; full input compatibility remains unresolved.

| Candidate | Actual release/license | Target and inputs | Evidence/decision |
|---|---|---|---|
| [NASA LHASA](https://github.com/nasa/LHASA) | Official `model.json`,1099810bytes, commitb8036f7ad4ae27d3faa333c809ecb1de7b218d4a; NOSAv1.3 | Daily~1km rainfall-triggered hazard. Ordered Lithology/Slope/PGA/profile wetness/2day antecedent/rain normalized by local99th percentile; static grids plus IMERG/SMAP or GEOS | Downloaded research copy, not executed/redistributed. Our shallow ERA5 moisture and rainfall sums are NOT trained inputs. License includes use-triggered waiver/indemnity; user accepted research use on October11 2026. Current2024model trained on additional inventories, so2017+NASA reports may overlap its training. Cannot claim independent validation. |
| [Sciamlab LFM2.5-VL450M](https://huggingface.co/Sciamlab/LFM2.5-VL-450M-landslide-GGUF) | Actual430MBGGUF+182MBvision projector; model card links LiquidAI LFM1.0 license | Image-text generated hazard/exposure labels from seven Sentinel2composites RGB/SWIR/NIR/NDMI/NDVI/BSI/TCTwetness, exact order | Card reports training loss1.015, not independently measured warning recall/calibration. Heuristic combination of ordinal hazard/exposure labels is not failure probability. No matching historic imagery/QA inputs; not downloaded or used. |
| [DL_LSM](https://github.com/HuangWBill/DL_LSM) | GitHub source, no weight file in inspected tree; no detected explicit license | Conv-SE-LSTM Sichuan-Tibet susceptibility, conditioning-factor layers | README claims global AUC0.8813 and annual response accuracy93.33%. Not India daily warning validation. No downloadable checkpoint verified, not used. |
| [GeoPhysAdapter](https://github.com/Liu-Zhihang/geophysadapter) | Code tree, no task checkpoint found/no detected explicit license | Cross-domain landslide image mapping with foundation model and geophysical priors | Landslide extent detection/mapping, not pre-event warning. Foundation weights alone do not provide the published task model; not used. |
| [Nepal susceptibility30m](https://zenodo.org/records/8307964) | CC-BY4.0,721.7MBraster ZIP plus readme, no executable weights | Fuzzy-logic relative susceptibility map within Nepal | A published output map, not an India event-warning model. Not downloaded or rebranded as pretrained weights. |

## NASA exact implementation

[Weights](https://raw.githubusercontent.com/nasa/LHASA/b8036f7ad4ae27d3faa333c809ecb1de7b218d4a/model.json),
[license](https://raw.githubusercontent.com/nasa/LHASA/b8036f7ad4ae27d3faa333c809ecb1de7b218d4a/LICENSE.pdf),
[input code](https://github.com/nasa/LHASA/blob/master/lhasa.py),
[changelog](https://github.com/nasa/LHASA/blob/master/CHANGELOG.md).
Static files are linked by original README at
https://gpm.nasa.gov/sites/default/files/data/landslides/static.zip .
Reproduction must preserve exact feature definitions, rain normalization, moisture
product/version, grid aggregation and time cutoff. No renamed ERA5 columns.
Current weights may include test-event training overlap; obtain upstream training
inventory/split lineage before presenting a benchmark as external confirmation.

Stage3's2017+test outcomes have already been viewed. Any new model comparison on
those rows is post-hoc comparative analysis, not untouched confirmation. Published
paper metrics do not validate this deployment. No warning gate changes.

[All research stages and source notices](INDEX.md) | [Repository overview](../README.md)
