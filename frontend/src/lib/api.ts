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
  centroid_lat?: number;
  centroid_lon?: number;
  issued_at: string;
  // Human-readable risk fields (enriched by API)
  risk_label?: string;     // e.g. "CRITICAL", "HIGH", "ELEVATED"
  risk_short?: string;     // e.g. "Very High Risk"
  risk_description?: string; // Plain English explanation
  risk_action?: string;    // What to do
  risk_color?: string;     // Semantic hex color
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
    fpi_pct?: number;
    fpi_24h?: number;
    tier: string;
    district?: string;
    block?: string;
    block_code?: string;
    state_code?: string;
    rainfall_3d_mm?: number;
    soil_moisture_pct?: number;
    risk_label?: string;
    risk_short?: string;
    risk_color?: string;
    risk_description?: string;
  };
}

export interface DistrictGeoJSONFeature {
  type: 'Feature';
  geometry: { type: string; coordinates: number[] };
  properties: {
    district_code: string;
    district_name: string;
    state_code: string;
    state_name: string;
    max_fpi: number;
    max_fpi_pct: number;
    max_fpi_24h: number;
    block_count: number;
    risk_label: string;
    risk_short: string;
    risk_color: string;
    risk_description: string;
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
    if (params?.min_fpi !== undefined) qs.set('min_fpi', String(params.min_fpi));
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
    if (params?.min_fpi !== undefined) qs.set('min_fpi', String(params.min_fpi));
    return fetchJSON<{ type: string; features: GeoJSONFeature[] }>(`/v1/geojson/fpi?${qs}`);
  },

  districtsGeoJSON: (params?: { state?: string; min_fpi?: number }) => {
    const qs = new URLSearchParams();
    if (params?.state) qs.set('state', params.state);
    if (params?.min_fpi !== undefined) qs.set('min_fpi', String(params.min_fpi));
    return fetchJSON<{ type: string; features: DistrictGeoJSONFeature[] }>(`/v1/geojson/districts?${qs}`);
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

// ── Risk Level Helpers (client-side fallback if API doesn't return them) ───────

export interface RiskLevel {
  label: string;    // e.g. "HIGH"
  short: string;    // e.g. "Very High Risk"
  color: string;    // hex color
  bgColor: string;  // light background
  emoji: string;
  description: string;
  action: string;
}

const RISK_LEVELS: RiskLevel[] = [
  {
    label: 'CRITICAL', short: 'Landslide Imminent',
    color: '#dc2626', bgColor: '#fef2f2', emoji: '🆘',
    description: 'Landslide is imminent or already occurring. Immediate evacuation required.',
    action: 'Evacuate all households on or below slopes immediately. Do not wait.',
  },
  {
    label: 'HIGH', short: 'Very High Risk',
    color: '#ea580c', bgColor: '#fff7ed', emoji: '🔴',
    description: 'Very high probability of landslide within 24–48 hours. Conditions are dangerous.',
    action: 'Pre-position NDRF/SDRF. Issue public advisory. Pre-evacuate highest-risk households.',
  },
  {
    label: 'ELEVATED', short: 'Elevated Risk',
    color: '#d97706', bgColor: '#fffbeb', emoji: '⚠️',
    description: 'Elevated landslide risk. Soil is saturated and terrain is primed.',
    action: 'Alert DDMA. Monitor slopes closely. Warn communities on steep terrain.',
  },
  {
    label: 'MODERATE', short: 'Moderate Risk',
    color: '#65a30d', bgColor: '#f7fee7', emoji: '🟡',
    description: 'Some risk factors are present but conditions are not yet dangerous.',
    action: 'Stay informed. Review evacuation routes. No immediate action needed.',
  },
  {
    label: 'LOW', short: 'Low Risk',
    color: '#16a34a', bgColor: '#f0fdf4', emoji: '✅',
    description: 'No significant landslide risk indicators at this time.',
    action: 'Normal monitoring. No action required.',
  },
];

export function getRiskLevel(fpiScore: number): RiskLevel {
  if (fpiScore >= 0.80) return RISK_LEVELS[0];
  if (fpiScore >= 0.65) return RISK_LEVELS[1];
  if (fpiScore >= 0.40) return RISK_LEVELS[2];
  if (fpiScore >= 0.20) return RISK_LEVELS[3];
  return RISK_LEVELS[4];
}

export function getRiskLabel(fpiScore: number): string {
  return getRiskLevel(fpiScore).label;
}

export function getRiskShort(fpiScore: number): string {
  return getRiskLevel(fpiScore).short;
}

export function getRiskColor(fpiScore: number): string {
  return getRiskLevel(fpiScore).color;
}

export function getRiskDescription(fpiScore: number): string {
  return getRiskLevel(fpiScore).description;
}

// ── Colour helpers (updated with semantic colors) ─────────────────────────────

/** Returns the semantic color for a tier string. */
export function tierColor(tier: string): string {
  const map: Record<string, string> = {
    EMERGENCY:  '#dc2626', // red-600 — critical
    WARNING:    '#ea580c', // orange-600 — high
    WATCH:      '#d97706', // amber-600 — elevated
    MONITORING: '#6b7280', // gray-500 — suppressed/uncertain
    NORMAL:     '#16a34a', // green-600 — safe
  };
  return map[tier] || '#6b7280';
}

/** Returns the semantic color for an FPI score (for gradient coloring). */
export function fpiColor(score: number): string {
  if (score >= 0.80) return '#dc2626'; // red-600   — critical
  if (score >= 0.65) return '#ea580c'; // orange-600 — high
  if (score >= 0.40) return '#d97706'; // amber-600  — elevated
  if (score >= 0.20) return '#65a30d'; // lime-600   — moderate
  return '#16a34a';                    // green-600  — low
}

/** Returns a label for display (used in fpiLabel, kept for backward compat). */
export function fpiLabel(score: number): string {
  if (score >= 0.80) return 'CRITICAL';
  if (score >= 0.65) return 'HIGH';
  if (score >= 0.40) return 'ELEVATED';
  if (score >= 0.20) return 'MODERATE';
  return 'LOW';
}

export function formatFPI(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/** CSS classes for tier badge. Now semantically correct. */
export function tierBadgeClass(tier: string): string {
  const map: Record<string, string> = {
    EMERGENCY:  'bg-red-600 text-white border-transparent',
    WARNING:    'bg-orange-600 text-white border-transparent',
    WATCH:      'bg-amber-600 text-white border-transparent',
    MONITORING: 'bg-slate-500 text-white border-transparent',
    NORMAL:     'bg-green-600 text-white border-transparent',
  };
  return map[tier] || 'bg-white text-black border border-slate-200';
}

/** FPI progress bar color class (Tailwind inline style compatible). */
export function fpiBarColor(score: number): string {
  if (score >= 0.80) return '#dc2626';
  if (score >= 0.65) return '#ea580c';
  if (score >= 0.40) return '#d97706';
  if (score >= 0.20) return '#65a30d';
  return '#16a34a';
}
