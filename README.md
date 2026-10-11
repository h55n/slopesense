# SlopeSense

[Live research demo](https://slopesense-olive.vercel.app/) | [Research trace: data -> protocol -> results](training/INDEX.md)

SlopeSense is an experimental landslide research application. It is not an official
warning service and is not validated for safety decisions. Real risk scoring returns
503 until the independent data and operational validation gates clear.

## Current capabilities

- Six representative locations receive real Open-Meteo provider snapshots on an
  hourly retrieval plan. These are modeled weather/soil data, not local gauges,
  NASA satellite inputs or a validated regional landslide forecast.
- API keys and contacts use persistent storage. Alert delivery is disabled even
  when credentials are present. CAP examples are Test, not government warnings.
- Reports prominently label sample material. Retrospective validation reports
  not_validated rather than fabricated success or confidence intervals.
- Three research stages retain real datasets, frozen protocols, failures and fitted
  exploratory models. Stage3 uses the official current NASA COOLR catalog.

[Read every stage and download its artifacts](training/INDEX.md). None passed the
90%recall/10%matched-background false-positive research screen. Stage3 unseen2017+
confirmations caught27.9%temporal and23.5%spatial reported events at the fixed0.5
threshold. They are case-control classification results, not population probabilities.

The old1km/FPI,24-48hour warning, calibrated95%confidence, NDMA compatibility,
retrospective success and alert-delivery performance claims are not established.
There is no validated warning lead time, field-tested coverage or zero-downtime guarantee.

## Reproduce the research

Start with [Stage1 sources/protocol](training/README.md), [Stage2 protocol](training/STAGE2_PROTOCOL.md)
and [Stage3 protocol](training/STAGE3_PROTOCOL.md). Results:
[Stage1](training/RESULTS_EXPLORATORY.md), [Stage2](training/STAGE2_RESULTS.md),
[Stage3](training/STAGE3_RESULTS.md). Source licenses and archive paths are in the
[research index](training/INDEX.md). NASA provenance does not prove event precision,
monitored non-events/base rates, pre-event terrain or prospective operational performance.

[Pretrained-model candidates and limitations](training/PRETRAINED_MODELS.md).
External model weights remain their authors' work, not SlopeSense's model.

## Development

Backend: FastAPI/Python. Frontend: Next.js. Database: PostgreSQL. Review
`backend/config.py`, `docker-compose.yml`, `requirements.txt` and `frontend/package.json`
for configuration. Keep credentials out of the repository. Do not add payment cards
or paid services for this noncommercial research deployment.

```bash
pip install -r requirements.txt
pytest
uvicorn backend.api.main:app --reload
cd frontend
npm install
npm run dev
```

Legacy synthetic trainers are not the current research route. Offline fitted
artifacts under training/ are not wired to production warning scoring.

## License and attribution

Project code: [Apache2.0](LICENSE). Source data and third-party models retain their
own licenses; see [source notices](training/INDEX.md). This project does not claim
NASA or GSI endorsement. NASA LHASA uses NOSAv1.3, not the project's Apache license.
