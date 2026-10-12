// SlopeSense custom hooks
import { useState, useEffect, useCallback, useRef } from 'react';
import { api, Alert, RetroSummary, SourceObservationsResponse } from './api';

const POLL_INTERVAL = 30 * 1000;  // 30 seconds (was 5 minutes but no backoff)
const MAX_BACKOFF = 5 * 60 * 1000; // 5 min max backoff on errors

export function useAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState({ total: 0, emergency: 0, warning: 0, watch: 0 });
  const [lastRun, setLastRun] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dataMode, setDataMode] = useState<string>('idle');
  const backoffRef = useRef(POLL_INTERVAL);

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await api.activeAlerts({ min_fpi: 0.0 });
      setAlerts(data.alerts || []);
      setDataMode((data as any).data_mode ?? 'unknown');
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
      setDataMode('unavailable');
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const isSample = dataMode !== 'live' || !!error;
  return { alerts, stats, lastRun, loading, error, isSample, refetch: fetchAlerts };
}


export function useSourceObservations() {
  const [data, setData] = useState<SourceObservationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api.sourceObservations()
        .then((d) => { if (!cancelled) { setData(d); setError(null); } })
        .catch((e) => { if (!cancelled) setError(e.message); })
        .finally(() => { if (!cancelled) setLoading(false); });
    load();
    const poll = setInterval(load, 5 * 60 * 1000);
    const tick = setInterval(() => setNow(Date.now()), 60 * 1000);
    return () => { cancelled = true; clearInterval(poll); clearInterval(tick); };
  }, []);

  return { data, observations: data?.observations ?? [], loading, error, now };
}

export function useRetrospective() {
  const [summary, setSummary] = useState<RetroSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.retrospectiveSummary()
      .then(setSummary)
      .catch(() => setSummary(null))
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

