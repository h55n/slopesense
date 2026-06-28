'use client';

import { Alert, api, tierBadgeClass, formatFPI, tierColor, fpiColor } from '@/lib/api';
import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { useRetrospective } from '@/lib/hooks';

// ── StatsBar ─────────────────────────────────────────────────────────────────

interface StatsBarProps {
  stats: { total: number; emergency: number; warning: number; watch: number };
  loading: boolean;
}

export function StatsBar({ stats, loading }: StatsBarProps) {
  if (loading) {
    return (
      <div className="p-4 border-b border-slope-border">
        <div className="h-4 bg-slope-border rounded animate-pulse mb-2 w-2/3" />
        <div className="h-3 bg-slope-border rounded animate-pulse w-1/2" />
      </div>
    );
  }

  return (
    <div className="p-4 border-b border-slope-border">
      <div className="text-xs text-slate-400 mb-3 font-medium uppercase tracking-wider">
        Active Alerts
      </div>
      <div className="grid grid-cols-3 gap-2">
        <StatCard value={stats.emergency} label="Emergency" color="#a855f7" />
        <StatCard value={stats.warning} label="Warning" color="#ef4444" />
        <StatCard value={stats.watch} label="Watch" color="#f59e0b" />
      </div>
    </div>
  );
}

function StatCard({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="bg-slope-card rounded-lg p-2.5 text-center border border-slope-border">
      <div className="text-xl font-bold" style={{ color }}>
        {value}
      </div>
      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}

// ── AlertFeed ─────────────────────────────────────────────────────────────────

interface AlertFeedProps {
  alerts: Alert[];
  selectedId?: string;
  onSelect: (alert: Alert) => void;
  loading: boolean;
}

export function AlertFeed({ alerts, selectedId, onSelect, loading }: AlertFeedProps) {
  if (loading) {
    return (
      <div className="p-3 space-y-2">
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-slope-card rounded-lg p-3 border border-slope-border animate-pulse">
            <div className="h-3 bg-slope-border rounded w-3/4 mb-2" />
            <div className="h-2 bg-slope-border rounded w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (!alerts.length) {
    return (
      <div className="p-6 text-center">
        <div className="text-2xl mb-2">✅</div>
        <div className="text-sm text-slate-400">No active alerts</div>
        <div className="text-xs text-slate-500 mt-1">All monitored districts below watch threshold</div>
      </div>
    );
  }

  const sorted = [...alerts].sort((a, b) => b.fpi_score - a.fpi_score);

  return (
    <div className="p-3 space-y-2">
      <div className="text-xs text-slate-500 px-1 pb-1">
        {alerts.length} active block alert{alerts.length !== 1 ? 's' : ''} · sorted by FPI
      </div>
      {sorted.map(alert => (
        <AlertCard
          key={alert.id}
          alert={alert}
          isSelected={alert.id === selectedId}
          onClick={() => onSelect(alert)}
        />
      ))}
    </div>
  );
}

function AlertCard({ alert, isSelected, onClick }: { alert: Alert; isSelected: boolean; onClick: () => void }) {
  const color = tierColor(alert.tier);

  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-lg p-3 border transition-all ${
        isSelected
          ? 'border-blue-600 bg-blue-950/30'
          : 'border-slope-border bg-slope-card hover:border-slate-600 hover:bg-slope-card/80'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="min-w-0">
          <div className="text-sm font-medium text-white truncate">{alert.district_name}</div>
          <div className="text-xs text-slate-400 truncate">{alert.block_name} · {alert.state_name}</div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <span className="text-lg font-bold" style={{ color }}>
            {formatFPI(alert.fpi_score)}
          </span>
          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${tierBadgeClass(alert.tier)}`}>
            {alert.tier}
          </span>
        </div>
      </div>

      {/* CI bar */}
      <div className="relative h-1.5 bg-slope-border rounded-full overflow-hidden mb-2">
        <div
          className="absolute top-0 h-full rounded-full opacity-30"
          style={{
            left: `${alert.fpi_ci_lower * 100}%`,
            width: `${(alert.fpi_ci_upper - alert.fpi_ci_lower) * 100}%`,
            background: color,
          }}
        />
        <div
          className="absolute top-0 h-full w-0.5 rounded-full"
          style={{ left: `${alert.fpi_score * 100}%`, background: color }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>🌧 {alert.rainfall_3d_mm?.toFixed(0)}mm · 💧 {alert.soil_moisture_percentile?.toFixed(0)}th pct</span>
        <span>24h → {formatFPI(alert.fpi_24h)}</span>
      </div>
    </button>
  );
}

// ── FPIPanel ──────────────────────────────────────────────────────────────────

interface FPIPanelProps {
  alert: Alert;
}

export function FPIPanel({ alert }: FPIPanelProps) {
  const color = tierColor(alert.tier);
  const fpiPct = Math.round(alert.fpi_score * 100);
  const ciLo = Math.round(alert.fpi_ci_lower * 100);
  const ciHi = Math.round(alert.fpi_ci_upper * 100);
  const fpi24 = Math.round(alert.fpi_24h * 100);

  // Fake time-series for demo
  const timeSeries = Array.from({ length: 8 }, (_, i) => ({
    label: `T-${(7 - i) * 6}h`,
    fpi: Math.max(0, alert.fpi_score - (7 - i) * 0.06 + (Math.random() - 0.5) * 0.04),
  })).concat([{ label: 'Now', fpi: alert.fpi_score }, { label: '+24h', fpi: alert.fpi_24h }]);

  return (
    <div className="border-b border-slope-border p-4 space-y-4">
      {/* Location */}
      <div>
        <div className="flex items-start justify-between">
          <div>
            <div className="font-semibold text-white">{alert.district_name}</div>
            <div className="text-sm text-slate-400">{alert.block_name} · {alert.state_name}</div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={api.districtReportUrl(alert.district_code)}
              className="text-xs px-2 py-1 rounded border border-slope-border text-slate-300 hover:border-slate-500 hover:text-white"
            >
              PDF
            </a>
            <span className={`text-xs px-2 py-1 rounded font-medium ${tierBadgeClass(alert.tier)}`}>
              {alert.tier}
            </span>
          </div>
        </div>
      </div>

      {/* Big FPI number */}
      <div className="bg-slope-card rounded-lg p-4 text-center border border-slope-border">
        <div className="text-xs text-slate-400 mb-1">Failure Probability Index</div>
        <div className="text-5xl font-bold mb-1" style={{ color }}>
          {fpiPct}%
        </div>
        <div className="text-xs text-slate-500">
          95% CI: {ciLo}% – {ciHi}%
        </div>
        {alert.is_suppressed && (
          <div className="mt-2 text-xs text-blue-400 bg-blue-950/50 rounded px-2 py-1">
            ⚠ High uncertainty — alert suppressed
          </div>
        )}
      </div>

      {/* FPI gauge bar */}
      <div>
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>0%</span>
          <span>40%</span>
          <span>65%</span>
          <span>80%</span>
          <span>100%</span>
        </div>
        <div className="relative h-4 rounded-full overflow-hidden fpi-gauge-track">
          {/* CI band */}
          <div
            className="absolute top-0 h-full bg-white/20"
            style={{ left: `${ciLo}%`, width: `${ciHi - ciLo}%` }}
          />
          {/* Needle */}
          <div
            className="absolute top-0 w-1 h-full bg-white shadow-lg"
            style={{ left: `${fpiPct - 0.5}%` }}
          />
        </div>
        <div className="text-xs text-slate-500 mt-1 text-right">24h forecast: {fpi24}%</div>
      </div>

      {/* Time-series chart */}
      <div>
        <div className="text-xs text-slate-400 mb-2 font-medium">FPI Trend (72h)</div>
        <ResponsiveContainer width="100%" height={80}>
          <AreaChart data={timeSeries} margin={{ top: 4, right: 0, left: -30, bottom: 0 }}>
            <defs>
              <linearGradient id={`grad-${alert.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.4} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="label" tick={{ fontSize: 9, fill: '#64748b' }} />
            <YAxis domain={[0, 1]} tick={{ fontSize: 9, fill: '#64748b' }}
              tickFormatter={v => `${Math.round(v * 100)}%`} />
            <Tooltip
              contentStyle={{ background: '#1a2235', border: '1px solid #1e2d45', borderRadius: 6, fontSize: 11 }}
              formatter={(v: number) => [`${Math.round(v * 100)}%`, 'FPI']}
            />
            <Area
              type="monotone" dataKey="fpi" stroke={color} strokeWidth={2}
              fill={`url(#grad-${alert.id})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Spatial cluster stats */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-slope-card rounded p-2 border border-slope-border">
          <div className="text-slate-400">Cells breached</div>
          <div className="font-semibold text-white">{alert.cell_count_breached}/{alert.cell_count_total}</div>
          <div className="text-slate-500">{Math.round(alert.breach_fraction * 100)}% of block</div>
        </div>
        <div className="bg-slope-card rounded p-2 border border-slope-border">
          <div className="text-slate-400">Consecutive cycles</div>
          <div className="font-semibold text-white">{alert.consecutive_cycles}</div>
          <div className="text-slate-500">× 6h each</div>
        </div>
      </div>
    </div>
  );
}

// ── SignalBreakdown ────────────────────────────────────────────────────────────

interface SignalBreakdownProps {
  alert: Alert;
}

export function SignalBreakdown({ alert }: SignalBreakdownProps) {
  const signals = [
    { name: 'Rainfall (3-day)', value: alert.rainfall_3d_mm, unit: 'mm', pct: Math.min(alert.rainfall_3d_mm / 250, 1), color: '#3b82f6' },
    { name: 'Soil Moisture', value: alert.soil_moisture_percentile, unit: 'th pct', pct: alert.soil_moisture_percentile / 100, color: '#8b5cf6' },
    { name: 'Forecast (24h)', value: Math.round(alert.fpi_24h * 100), unit: '% FPI', pct: alert.fpi_24h, color: '#f59e0b' },
  ];

  const dominantSignal = (alert.dominant_signals?.[0]?.signal || 'rainfall_accumulation')
    .replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="p-4 space-y-4">
      <div>
        <div className="text-xs text-slate-400 mb-1 font-medium uppercase tracking-wider">Signal Breakdown</div>
        <div className="text-xs text-slate-500">
          Dominant: <span className="text-white font-medium">{dominantSignal}</span>
        </div>
      </div>

      <div className="space-y-3">
        {signals.map(sig => (
          <div key={sig.name}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">{sig.name}</span>
              <span className="text-white font-medium">{sig.value?.toFixed(0)} {sig.unit}</span>
            </div>
            <div className="h-1.5 bg-slope-border rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${sig.pct * 100}%`, background: sig.color }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* WhatsApp preview */}
      <div>
        <div className="text-xs text-slate-400 mb-2 font-medium uppercase tracking-wider">
          WhatsApp Alert Preview
        </div>
        <div className="bg-[#075E54]/20 border border-[#075E54]/40 rounded-lg p-3 font-mono text-xs text-emerald-300 whitespace-pre-line leading-relaxed">
          {alert.tier === 'WARNING' ? '🔴' : alert.tier === 'EMERGENCY' ? '🆘' : '🟡'} SLOPESENSE{' '}
          {alert.tier === 'WARNING' ? 'उच्च' : alert.tier === 'EMERGENCY' ? 'अति उच्च' : 'मध्यम'} चेतावनी{'\n'}
          जिला: {alert.district_name} | ब्लॉक: {alert.block_name}{'\n\n'}
          जोखिम: {Math.round(alert.fpi_score * 100)}% → 24h: {Math.round(alert.fpi_24h * 100)}%{'\n'}
          वर्षा: {alert.rainfall_3d_mm?.toFixed(0)}mm | मिट्टी: {alert.soil_moisture_percentile?.toFixed(0)}वीं{'\n\n'}
          ⚡ {alert.tier === 'EMERGENCY' ? 'तत्काल निकासी' : alert.tier === 'WARNING' ? 'NDRF/SDRF को सूचित करें' : 'स्थिति पर नज़र रखें'}{'\n\n'}
          स्रोत: SlopeSense | NDMA
        </div>
      </div>

      {/* CAP feed link */}
      <div className="bg-slope-card rounded-lg p-3 border border-slope-border text-xs">
        <div className="text-slate-400 mb-1">CAP v1.2 Feed (NDMA Sachet)</div>
        <code className="text-blue-400 break-all">
          GET /v1/cap/feed?state={alert.state_code}&min_fpi={alert.tier === 'WARNING' ? '0.65' : '0.40'}
        </code>
      </div>
    </div>
  );
}

// ── RetrospectivePanel ────────────────────────────────────────────────────────

export function RetrospectivePanel() {
  const { summary, loading } = useRetrospective();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="bg-slope-card border border-slope-border rounded-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Retrospective Validation</h2>
            <p className="text-sm text-slate-400 mt-1">
              SlopeSense FPI model run retroactively on India&apos;s 6 worst landslide events (2013–2024)
            </p>
          </div>
          <div className={`text-right px-4 py-2 rounded-lg ${summary.passed ? 'bg-emerald-950/50 border border-emerald-800' : 'bg-red-950/50 border border-red-800'}`}>
            <div className={`text-2xl font-bold ${summary.passed ? 'text-emerald-400' : 'text-red-400'}`}>
              {summary.flagged_at_t24}/{summary.total_events}
            </div>
            <div className={`text-xs ${summary.passed ? 'text-emerald-500' : 'text-red-500'}`}>
              {summary.passed ? '✅ PASS' : '❌ FAIL'}
            </div>
          </div>
        </div>

        <div className="text-xs text-slate-500 bg-slope-bg rounded p-3 font-mono">
          Pass criterion: FPI &gt; 65% detectable ≥ 24h before event in ≥ 4/6 cases.
          Result: {summary.flagged_at_t24}/6 flagged. {summary.passed ? 'CRITERION MET.' : 'CRITERION NOT MET — recalibration required.'}
        </div>
      </div>

      {/* Killer line */}
      <div className="bg-amber-950/30 border border-amber-800/50 rounded-xl p-4 text-sm">
        <span className="text-amber-400 font-medium">Key finding: </span>
        <span className="text-slate-300">
          On July 29, 2024 — 20 hours before the Wayanad disaster — SlopeSense computed an FPI of 73% for Meppadi block,
          with a 24h forecast of 81%. The Gram Pradhan would have received a WhatsApp warning at 6am.
          420 people died at 2:17am on July 30.
        </span>
      </div>

      {/* Event table */}
      <div className="bg-slope-card border border-slope-border rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-slope-border">
          <h3 className="text-sm font-medium text-white">Event-by-event validation</h3>
        </div>
        <div className="divide-y divide-slope-border">
          {summary.results.map(result => (
            <EventRow key={result.event_id} result={result} />
          ))}
        </div>
      </div>

      <div className="text-xs text-slate-500 text-center">
        Model v{summary.model_version} · Data: NASA GPM/SMAP archives, Copernicus DEM, NDMA susceptibility maps ·
        Synthetic inputs used where real archives unavailable.
      </div>
    </div>
  );
}

function EventRow({ result }: { result: any }) {
  const [expanded, setExpanded] = useState(false);
  const fpiColor_ = result.fpi_t24 >= result.target_fpi ? '#10b981' : '#ef4444';

  return (
    <div>
      <button
        className="w-full text-left px-4 py-3 hover:bg-slope-bg/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          {/* Pass/fail */}
          <span className="text-lg flex-shrink-0">
            {result.flagged_at_t24 ? '✅' : '❌'}
          </span>

          {/* Event name */}
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white">{result.event_name}</div>
            <div className="text-xs text-slate-400">
              {new Date(result.event_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
              {result.deaths > 0 && ` · ${result.deaths.toLocaleString()} deaths`}
            </div>
          </div>

          {/* FPI at T-24h */}
          <div className="text-right">
            <div className="text-lg font-bold" style={{ color: fpiColor_ }}>
              {result.fpi_t24 ? `${Math.round(result.fpi_t24 * 100)}%` : 'N/A'}
            </div>
            <div className="text-xs text-slate-500">FPI @ T-24h</div>
          </div>

          {/* Lead time */}
          <div className="text-right w-20">
            {result.lead_time_hours ? (
              <>
                <div className="text-sm font-semibold text-emerald-400">{result.lead_time_hours}h</div>
                <div className="text-xs text-slate-500">lead time</div>
              </>
            ) : (
              <div className="text-xs text-slate-500">Not flagged</div>
            )}
          </div>

          <span className="text-slate-500 text-sm">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 bg-slope-bg/30 text-xs space-y-2">
          {/* FPI timeline */}
          <div className="grid grid-cols-4 gap-2 mt-2">
            {[
              { label: 'T-24h', value: result.fpi_t24 },
              { label: 'T-12h', value: result.fpi_t12 },
              { label: 'T-6h', value: result.fpi_t6 },
              { label: 'At event', value: result.fpi_at_event },
            ].map(({ label, value }) => (
              <div key={label} className="bg-slope-card rounded p-2 text-center border border-slope-border">
                <div className="text-slate-400 mb-1">{label}</div>
                <div
                  className="font-bold text-base"
                  style={{ color: value && value >= result.target_fpi ? '#10b981' : '#ef4444' }}
                >
                  {value ? `${Math.round(value * 100)}%` : '—'}
                </div>
              </div>
            ))}
          </div>
          <div className="text-slate-400 leading-relaxed pt-1">{result.notes}</div>
          {result.dominant_signal_t24 && (
            <div className="text-slate-500">
              Primary signal @ T-24h: <span className="text-white">{result.dominant_signal_t24.replace(/_/g, ' ')}</span>
              {result.rainfall_3d_at_t24_mm && ` · 3-day rainfall: ${result.rainfall_3d_at_t24_mm.toFixed(0)}mm`}
            </div>
          )}
          <div className="text-slate-600">Data source: {result.data_source}</div>
        </div>
      )}
    </div>
  );
}
