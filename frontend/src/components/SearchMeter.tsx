'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiUrl, formatFPI, fpiColor, tierColor } from '@/lib/api';

interface RiskResult {
  lat: number;
  lon: number;
  fpi_score: number;
  fpi_ci_lower: number;
  fpi_ci_upper: number;
  alert_tier: string;
  dominant_signal: string;
}

export default function SearchMeter() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<RiskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;

    // Parse lat, lon from string like "11.58, 76.08"
    const parts = query.split(',').map(s => s.trim());
    if (parts.length !== 2 || parts.some(p => !p || !Number.isFinite(Number(p))) || Math.abs(Number(parts[0])) > 90 || Math.abs(Number(parts[1])) > 180) {
      setError('Please enter valid coordinates, e.g. "11.58, 76.08"');
      return;
    }

    const lat = Number(parts[0]);
    const lon = Number(parts[1]);

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(apiUrl(`/v1/risk?lat=${lat}&lon=${lon}`));
      if (!res.ok) throw new Error(res.status === 503 ? 'Risk score unavailable: real inputs or a model run are not available.' : 'Risk request failed. No score is confirmed.');
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel relative overflow-hidden p-6 sm:p-8">
      <div className="eyebrow mb-1">Model FPI search</div>
      <h3 className="font-serif text-[28px] leading-tight text-ink">Check any coordinate</h3>
      <p className="mb-5 mt-1 text-[14px] text-ink/55">Request the model index for a coordinate. Unavailable real inputs may return no score. FPI is not a calibrated probability.</p>
      
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. 11.58, 76.08"
          aria-label="Latitude, longitude" className="h-11 min-w-0 flex-1 rounded-full border border-ink/15 bg-paper px-5 text-[14px] text-ink placeholder-ink/35 outline-none transition-colors focus:border-forest"
        />
        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary h-11 disabled:opacity-50"
        >
          {loading ? 'Scanning…' : 'Check risk'}
        </button>
      </form>

      <AnimatePresence mode="wait">
        {error && (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="text-red-400 text-base-sm p-3 bg-red-400/10 border border-red-400/20 rounded-lg"
          >
            {error}
          </motion.div>
        )}

        {result && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-center gap-6 p-4 rounded-2xl bg-paper border border-ink/10"
          >
            <ArcGauge pct={result.fpi_score * 100} color={fpiColor(result.fpi_score)} />
            <div>
              <div className="font-serif text-4xl font-bold leading-none" style={{ color: fpiColor(result.fpi_score) }}>
                {Math.round(result.fpi_score * 100)}%
              </div>
              <div className="mt-1 text-small font-medium text-ink/60">Current Risk Index</div>
              <div className="mt-2 text-tiny uppercase tracking-widest font-bold" style={{ color: tierColor(result.alert_tier) }}>
                {result.alert_tier}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ArcGauge({ pct, color }: { pct: number; color: string }) {
  const r = 32;
  const cx = 40;
  const cy = 40;
  const startAngle = -220;
  const endAngle = 40;
  const totalAngle = endAngle - startAngle;
  const fillAngle = (pct / 100) * totalAngle;

  function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function describeArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
    const start = polarToCartesian(cx, cy, r, endDeg);
    const end = polarToCartesian(cx, cy, r, startDeg);
    const largeArc = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
  }

  const trackPath = describeArc(cx, cy, r, startAngle, endAngle);
  const fillPath = fillAngle > 0 ? describeArc(cx, cy, r, startAngle, startAngle + fillAngle) : '';

  return (
    <svg width="80" height="80" viewBox="0 0 80 80" className="shrink-0">
      <path d={trackPath} fill="none" stroke="rgba(29,42,33,0.10)" strokeWidth="6" strokeLinecap="round" />
      {fillPath && (
        <motion.path
          d={fillPath}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      )}
    </svg>
  );
}
