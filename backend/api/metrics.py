from prometheus_client import Counter, Histogram, Gauge, generate_latest

MODEL_RUNS = Counter("slopesense_model_runs_total", "Total model pipeline runs")
MODEL_RUN_DURATION = Histogram(
    "slopesense_model_run_seconds", "Model run duration",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)
ACTIVE_ALERTS = Gauge("slopesense_active_alerts", "Current active alerts", ["tier"])
MESSAGES_SENT = Counter(
    "slopesense_whatsapp_messages_total", "WhatsApp messages sent", ["status"],
)
FPI_SCORES = Histogram(
    "slopesense_fpi_score", "FPI score distribution",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 0.9, 1.0],
)
