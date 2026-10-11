# Published-model search, October11 2026

Real small weights exist. They are not automatically compatible with this project.
No external pretrained model has been validated here or installed in production.
NASA license accepted for research; full input compatibility remains unresolved.

| Candidate | Actual release/license | Target and inputs | Evidence/decision |
|---|---|---|---|
| [NASA LHASA](https://github.com/nasa/LHASA) | Official `model.json`,1099810bytes, commitb8036f7ad4ae27d3faa333c809ecb1de7b218d4a; NOSAv1.3 | Daily~1km rainfall-triggered hazard. Ordered Lithology/Slope/PGA/profile wetness/2day antecedent/rain normalized by local99th percentile; static grids plus IMERG/SMAP or GEOS | Research weights downloaded and loaded; no predictions or redistribution. Our shallow ERA5 moisture and rainfall sums are NOT trained inputs. License includes use-triggered waiver/indemnity; user accepted research use on October11 2026. Current2024model trained on additional inventories, so2017+NASA reports may overlap its training. Cannot claim independent validation. |
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

## Exact input-access pilot

NOSA research use accepted on October11 2026. The unmodified weights loaded as an
XGBoost Booster:300trees, exact six feature names. SHA256:
`3f8cad8693cea2d3b7222ebacf009bf2afe46440b08f76ae470d5d732e75e6a9`.
No prediction was made, because no complete matched real-input row exists yet.

- NASA static.zip HTTP200,1560793847bytes; range retrieval works. Archive contains
  exact `Lithology.nc4`, `Slope.nc4`, `pga.nc4`, `mask.nc4`, `p99.nc4`, `p99geos.nc4`.
  Exact rain-percentile file extracted,12412015bytes. Not generic replacements.
- [SMAP8coverage](https://nsidc.org/data/spl4smgp/versions/8) starts31March2015,
  so exact NRT stack cannot populate our2013calibration/2014threshold sets.
  Current upstream defaultminor8011produced authenticated404 for a2019granule.
  NASA CMR discovery instead found real8010historical files, then authenticated
  [official OPeNDAP granule](https://opendap.earthdata.nasa.gov/collections/C3480440870-NSIDC_CPRD/granules/SMAP_L4_SM_gph_20190731T223000_Vv8010_001.h5)
  returned profile wetness0.685816 at latitude19.5377/longitude76.7894. This is
  an access pilot only, not a landslide test row or model evaluation.
- [GEOS assimilation metadata](https://opendap.nccs.nasa.gov/dods/GEOS-5/fp/0.25_deg/assim/tavg1_2d_lnd_Nx.das)
  begins1December2017 at this endpoint, also missing2013/14selection years.
  A constrained profile-wetness query returned0.7837882 at35N/77.5E. This does
  not substitute GEOS for NRT SMAP or verify older historical coverage elsewhere.
- IMERG early07Cprotected GIS URLs returned401; even documented email/email
  credentials require a registered PPS account. [PPS registration](https://registration.pps.eosdis.nasa.gov/registration/)
  mandates product/status emails. Separate registration/confirmation pending;
  no form submitted during this access pilot.
- [Original LHASA2paper](https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2021.640043/full)
  trained on2015-2018GLC and India Thrissur2018, evaluated2019-2020. Current2.1
  adds more inventories.2017-2018NASA catalog rows cannot be called independent
  validation, and current2.1training membership remains unresolved.

Thus a future NASA-only fixed-threshold2015+retrospective diagnostic must use its
own prespecified compatible-data study, not pretend to pass the existing2014
selection protocol. Input access is progress, not evaluation or warning clearance.
