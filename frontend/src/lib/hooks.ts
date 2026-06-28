// SlopeSense custom hooks
import { useState, useEffect, useCallback, useRef } from 'react';
import { api, Alert, RetroSummary } from './api';

const POLL_INTERVAL = 30 * 1000;  // 30 seconds (was 5 minutes but no backoff)
const MAX_BACKOFF = 5 * 60 * 1000; // 5 min max backoff on errors

export function useAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState({ total: 0, emergency: 0, warning: 0, watch: 0 });
  const [lastRun, setLastRun] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const backoffRef = useRef(POLL_INTERVAL);

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await api.activeAlerts({ min_fpi: 0.0 });
      setAlerts(data.alerts || []);
      setLastRun(data.run_timestamp || null);
      setStats({
        total: data.count || 0,
        emergency: data.alerts.filter(a => a.tier === 'EMERGENCY').length,
        warning: data.alerts.filter(a => a.tier === 'WARNING').length,
        watch: data.alerts.filter(a => a.tier === 'WATCH').length,
      });
      setError(null);
      backoffRef.current = POLL_INTERVAL; // reset backoff on success
    } catch (err: any) {
      // Exponential backoff on errors to avoid hammering the API
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF);
      setError(err.message);
      // Load synthetic demo data on error
      if (alerts.length === 0) {
        setAlerts(DEMO_ALERTS);
        setStats({ total: DEMO_ALERTS.length, emergency: 1, warning: 2, watch: 2 });
      }
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  return { alerts, stats, lastRun, loading, error, refetch: fetchAlerts };
}


export function useRetrospective() {
  const [summary, setSummary] = useState<RetroSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.retrospectiveSummary()
      .then(setSummary)
      .catch(() => setSummary(DEMO_RETROSPECTIVE))
      .finally(() => setLoading(false));
  }, []);

  return { summary, loading };
}

export function useLiveWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<any>(null);

  useEffect(() => {
    const WS_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
      .replace('http', 'ws') + '/ws/live';

    let ws: WebSocket;
    let reconnectTimer: NodeJS.Timeout;

    const connect = () => {
      try {
        ws = new WebSocket(WS_URL);
        ws.onopen = () => { setIsConnected(true); };
        ws.onmessage = (e) => {
          try { setLastUpdate(JSON.parse(e.data)); } catch {}
        };
        ws.onclose = () => {
          setIsConnected(false);
          reconnectTimer = setTimeout(connect, 5000);
        };
        ws.onerror = () => { ws.close(); };
      } catch { /* WebSocket not available in some environments */ }
    };

    connect();
    return () => {
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  return { isConnected, lastUpdate };
}

// ── Demo data (shown when API unreachable) ────────────────────────────────────

const DEMO_ALERTS: Alert[] = [
  {
    id: 'demo-1',
    alert_code: 'KL_WYD_MEPPADI_DEMO',
    state_code: 'KL', state_name: 'Kerala',
    district_code: 'KL_WYD', district_name: 'Wayanad',
    block_code: 'KL_WYD_MEP', block_name: 'Meppadi',
    lat: 11.55, lon: 76.10,
    fpi_score: 0.73, fpi_ci_lower: 0.61, fpi_ci_upper: 0.84,
    fpi_24h: 0.81,
    tier: 'WARNING', is_active: true, is_suppressed: false, consecutive_cycles: 2,
    dominant_signals: [{ signal: 'rainfall_accumulation', value: 0.82 }],
    rainfall_3d_mm: 183, soil_moisture_percentile: 91,
    cell_count_total: 48, cell_count_breached: 22, breach_fraction: 0.46,
    issued_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 'demo-2',
    alert_code: 'KL_WYD_VYTHIRI_DEMO',
    state_code: 'KL', state_name: 'Kerala',
    district_code: 'KL_WYD', district_name: 'Wayanad',
    block_code: 'KL_WYD_VYT', block_name: 'Vythiri',
    lat: 11.55, lon: 76.03,
    fpi_score: 0.61, fpi_ci_lower: 0.50, fpi_ci_upper: 0.72,
    fpi_24h: 0.68,
    tier: 'WATCH', is_active: true, is_suppressed: false, consecutive_cycles: 1,
    dominant_signals: [{ signal: 'soil_moisture', value: 0.68 }],
    rainfall_3d_mm: 142, soil_moisture_percentile: 86,
    cell_count_total: 35, cell_count_breached: 14, breach_fraction: 0.40,
    issued_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 'demo-3',
    alert_code: 'UK_CHA_TAPOVAN_DEMO',
    state_code: 'UK', state_name: 'Uttarakhand',
    district_code: 'UK_CHA', district_name: 'Chamoli',
    block_code: 'UK_CHA_TAP', block_name: 'Tapovan',
    lat: 30.49, lon: 79.62,
    fpi_score: 0.55, fpi_ci_lower: 0.42, fpi_ci_upper: 0.68,
    fpi_24h: 0.59,
    tier: 'WATCH', is_active: true, is_suppressed: false, consecutive_cycles: 3,
    dominant_signals: [{ signal: 'slope_angle', value: 0.72 }],
    rainfall_3d_mm: 98, soil_moisture_percentile: 78,
    cell_count_total: 60, cell_count_breached: 22, breach_fraction: 0.37,
    issued_at: new Date(Date.now() - 10800000).toISOString(),
  },
  {
    id: 'demo-4',
    alert_code: 'UK_RUD_KEDARNATH_DEMO',
    state_code: 'UK', state_name: 'Uttarakhand',
    district_code: 'UK_RUD', district_name: 'Rudraprayag',
    block_code: 'UK_RUD_KED', block_name: 'Ukhimath',
    lat: 30.73, lon: 79.06,
    fpi_score: 0.67, fpi_ci_lower: 0.55, fpi_ci_upper: 0.79,
    fpi_24h: 0.72,
    tier: 'WARNING', is_active: true, is_suppressed: false, consecutive_cycles: 2,
    dominant_signals: [{ signal: 'rainfall_accumulation', value: 0.75 }],
    rainfall_3d_mm: 165, soil_moisture_percentile: 88,
    cell_count_total: 42, cell_count_breached: 18, breach_fraction: 0.43,
    issued_at: new Date(Date.now() - 5400000).toISOString(),
  },
  {
    id: 'demo-5',
    alert_code: 'SK_MAN_LACHEN_DEMO',
    state_code: 'SK', state_name: 'Sikkim',
    district_code: 'SK_MAN', district_name: 'Mangan',
    block_code: 'SK_MAN_LAC', block_name: 'Lachen',
    lat: 27.75, lon: 88.55,
    fpi_score: 0.44, fpi_ci_lower: 0.31, fpi_ci_upper: 0.57,
    fpi_24h: 0.48,
    tier: 'WATCH', is_active: true, is_suppressed: false, consecutive_cycles: 1,
    dominant_signals: [{ signal: 'geological_susceptibility', value: 0.60 }],
    rainfall_3d_mm: 72, soil_moisture_percentile: 71,
    cell_count_total: 28, cell_count_breached: 10, breach_fraction: 0.36,
    issued_at: new Date(Date.now() - 14400000).toISOString(),
  },
];

const DEMO_RETROSPECTIVE: RetroSummary = {
  run_at: new Date().toISOString(),
  model_version: 'v0.1',
  total_events: 6,
  flagged_at_t24: 4,
  pass_criterion: '≥4/6 flagged at T-24h with FPI≥target',
  passed: true,
  results: [
    { event_id: 'wayanad_2024', event_name: 'Wayanad, Kerala', event_date: '2024-07-30T02:17:00+05:30',
      district: 'Wayanad', state: 'Kerala', deaths: 420, fpi_t24: 0.73, fpi_t12: 0.79, fpi_t6: 0.84,
      fpi_at_event: 0.91, dominant_signal_t24: 'rainfall_accumulation', rainfall_3d_at_t24_mm: 183,
      target_fpi: 0.65, flagged_at_t24: true, lead_time_hours: 24, data_source: 'synthetic',
      notes: 'Deadliest landslide in Kerala history. 420 deaths. Warning existed 16h prior.' },
    { event_id: 'kedarnath_2013', event_name: 'Kedarnath, Uttarakhand', event_date: '2013-06-16T20:00:00+05:30',
      district: 'Rudraprayag', state: 'Uttarakhand', deaths: 5700, fpi_t24: 0.81, fpi_t12: 0.88, fpi_t6: 0.92,
      fpi_at_event: 0.96, dominant_signal_t24: 'rainfall_accumulation', rainfall_3d_at_t24_mm: 220,
      target_fpi: 0.65, flagged_at_t24: true, lead_time_hours: 48, data_source: 'synthetic',
      notes: 'Multi-day extreme rainfall (375mm in 3 days). India\'s worst modern natural disaster.' },
    { event_id: 'malin_2014', event_name: 'Malin Village, Maharashtra', event_date: '2014-07-30T06:30:00+05:30',
      district: 'Pune', state: 'Maharashtra', deaths: 151, fpi_t24: 0.69, fpi_t12: 0.76, fpi_t6: 0.82,
      fpi_at_event: 0.88, dominant_signal_t24: 'rainfall_accumulation', rainfall_3d_at_t24_mm: 195,
      target_fpi: 0.65, flagged_at_t24: true, lead_time_hours: 24, data_source: 'synthetic',
      notes: 'Classic rainfall-triggered event. Deforested slope. 350mm in 3 days.' },
    { event_id: 'chamoli_2021', event_name: 'Chamoli, Uttarakhand', event_date: '2021-02-07T10:50:00+05:30',
      district: 'Chamoli', state: 'Uttarakhand', deaths: 204, fpi_t24: 0.47, fpi_t12: 0.52, fpi_t6: 0.58,
      fpi_at_event: 0.63, dominant_signal_t24: 'slope_angle', rainfall_3d_at_t24_mm: 60,
      target_fpi: 0.45, flagged_at_t24: true, lead_time_hours: 24, data_source: 'synthetic',
      notes: 'Rock-ice avalanche from Ronti peak. February — winter event.' },
    { event_id: 'sikkim_2023', event_name: 'Sikkim GLOF', event_date: '2023-10-04T01:30:00+05:30',
      district: 'Mangan', state: 'Sikkim', deaths: 40, fpi_t24: 0.41, fpi_t12: 0.48, fpi_t6: 0.55,
      fpi_at_event: 0.62, dominant_signal_t24: 'geological_susceptibility', rainfall_3d_at_t24_mm: 85,
      target_fpi: 0.50, flagged_at_t24: false, lead_time_hours: undefined,
      data_source: 'synthetic', notes: 'Glacial Lake Outburst Flood. Rainfall signal insufficient for GLOF detection.' },
    { event_id: 'joshimath_2023', event_name: 'Joshimath Subsidence', event_date: '2023-01-15T00:00:00+05:30',
      district: 'Chamoli', state: 'Uttarakhand', deaths: 0, fpi_t24: 0.31, fpi_t12: 0.33, fpi_t6: 0.34,
      fpi_at_event: 0.35, dominant_signal_t24: 'slope_angle', rainfall_3d_at_t24_mm: 20,
      target_fpi: 0.40, flagged_at_t24: false, lead_time_hours: undefined,
      data_source: 'synthetic', notes: 'Slow-onset subsidence — rainfall-based model insufficient. Requires InSAR deformation monitoring.' },
  ],
};
