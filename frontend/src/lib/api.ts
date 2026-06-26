// SlopeSense API Client

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export interface Alert {
  id: string;
  alert_code: string;
  state_code: string;
  state_name: string;
  district_code: string;
  district_name: string;
  block_code: string;
  block_name: string;
  fpi_score: number;
  fpi_ci_lower: number;
  fpi_ci_upper: number;
  fpi_24h: number;
  tier: 'NORMAL' | 'WATCH' | 'WARNING' | 'EMERGENCY' | 'MONITORING';
  is_active: boolean;
  is_suppressed: boolean;
  consecutive_cycles: number;
  dominant_signals: Array<{ signal: string; value: number }>;
  rainfall_3d_mm: number;
  soil_moisture_percentile: number;
  cell_count_total: number;
  cell_count_breached: number;
  breach_fraction: number;
  issued_at: string;
}

export interface RiskPoint {
  lat: number;
  lon: number;
  cell_id: string;
  district?: string;
  block?: string;
  fpi_score: number;
  fpi_ci_lower: number;
  fpi_ci_upper: number;
  fpi_24h?: number;
  fpi_48h?: number;
  alert_tier: string;
  dominant_signal?: string;
  rainfall_3d_mm?: number;
  soil_moisture_pct?: number;
  slope_degrees?: number;
  run_timestamp: string;
}

export interface RetroResult {
  event_id: string;
  event_name: string;
  event_date: string;
  district: string;
  state: string;
  deaths: number;
  fpi_t24?: number;
  fpi_t12?: number;
  fpi_t6?: number;
  fpi_at_event?: number;
  dominant_signal_t24?: string;
  rainfall_3d_at_t24_mm?: number;
  target_fpi: number;
  flagged_at_t24: boolean;
  lead_time_hours?: number;
  data_source: string;
  notes: string;
}

export interface RetroSummary {
  run_at: string;
  model_version: string;
  total_events: number;
  flagged_at_t24: number;
  pass_criterion: string;
  passed: boolean;
  results: RetroResult[];
}

export interface GeoJSONFeature {
  type: 'Feature';
  geometry: { type: string; coordinates: number[] };
  properties: {
    fpi: number;
    fpi_24h?: number;
    tier: string;
    district?: string;
    block?: string;
    rainfall_3d_mm?: number;
    soil_moisture_pct?: number;
  };
}

// ── API functions ─────────────────────────────────────────────────────────────

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    next: { revalidate: 300 }, // 5 min cache
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  health: () => fetchJSON<{ status: string; active_alerts: number; last_model_run: string | null }>('/'),

  activeAlerts: (params?: { min_fpi?: number; tier?: string; state?: string }) => {
    const qs = new URLSearchParams();
    if (params?.min_fpi) qs.set('min_fpi', String(params.min_fpi));
    if (params?.tier) qs.set('tier', params.tier);
    if (params?.state) qs.set('state', params.state);
    return fetchJSON<{ count: number; alerts: Alert[]; run_timestamp: string }>(`/v1/alerts/active?${qs}`);
  },

  alertDetail: (id: string) => fetchJSON<Alert>(`/v1/alerts/${id}`),

  riskPoint: (lat: number, lon: number, hoursAhead = 0) =>
    fetchJSON<RiskPoint>(`/v1/risk?lat=${lat}&lon=${lon}&hours_ahead=${hoursAhead}`),

  stateDistricts: (stateCode: string) =>
    fetchJSON<{ state_code: string; count: number; districts: Alert[] }>(`/v1/districts/${stateCode}`),

  retrospectiveSummary: () => fetchJSON<RetroSummary>('/v1/retrospective'),

  retrospectiveEvent: (eventId: string) => fetchJSON<RetroResult>(`/v1/retrospective/${eventId}`),

  fpiGeoJSON: (params?: { state?: string; min_fpi?: number }) => {
    const qs = new URLSearchParams();
    if (params?.state) qs.set('state', params.state);
    if (params?.min_fpi) qs.set('min_fpi', String(params.min_fpi));
    return fetchJSON<{ type: string; features: GeoJSONFeature[] }>(`/v1/geojson/fpi?${qs}`);
  },

  registerContact: (data: {
    name: string;
    role: string;
    whatsapp_number: string;
    state_code: string;
    district_code?: string;
    language?: string;
    min_tier?: string;
  }) =>
    fetchJSON('/v1/contacts/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  districtReportUrl: (districtCode: string) =>
    apiUrl(`/v1/districts/${encodeURIComponent(districtCode)}/report.pdf`),
};

// ── Colour helpers ─────────────────────────────────────────────────────────────

export function tierColor(tier: string): string {
  const map: Record<string, string> = {
    EMERGENCY: '#ef4444',
    WARNING:   '#f97316',
    WATCH:     '#eab308',
    MONITORING:'#6b7280',
    NORMAL:    '#10b981',
  };
  return map[tier] || '#6b7280';
}

export function fpiColor(score: number): string {
  if (score >= 0.80) return '#ef4444'; // Red
  if (score >= 0.65) return '#f97316'; // Amber/Orange
  if (score >= 0.40) return '#eab308'; // Yellow
  return '#10b981'; // Green
}

export function fpiLabel(score: number): string {
  if (score >= 0.80) return 'CRITICAL';
  if (score >= 0.65) return 'HIGH';
  if (score >= 0.40) return 'ELEVATED';
  return 'NORMAL';
}

export function formatFPI(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function tierBadgeClass(tier: string): string {
  const map: Record<string, string> = {
    EMERGENCY: 'bg-red-500 text-white border-transparent',
    WARNING:   'bg-orange-500 text-white border-transparent',
    WATCH:     'bg-yellow-500 text-white border-transparent',
    MONITORING:'bg-slate-500 text-white border-transparent',
    NORMAL:    'bg-emerald-500 text-white border-transparent',
  };
  return map[tier] || 'bg-white text-black border border-slate-200';
}
