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
    if (parts.length !== 2 || isNaN(Number(parts[0])) || isNaN(Number(parts[1]))) {
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
      if (!res.ok) throw new Error('Failed to fetch risk data');
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel p-6 relative overflow-hidden">
      <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-slope-accent mb-3 flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-slope-accent animate-pulse" />
        Live FPI Search
      </div>
      
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. 11.58, 76.08"
          className="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-[13px] text-white placeholder-white/30 focus:outline-none focus:border-slope-accent/50 transition-colors"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-slope-accent text-slope-bg px-5 py-2 rounded-lg text-[11px] font-bold uppercase tracking-widest hover:bg-white transition-colors disabled:opacity-50"
        >
          {loading ? '...' : 'Scan'}
        </button>
      </form>

      <AnimatePresence mode="wait">
        {error && (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="text-red-400 text-[12px] p-3 bg-red-400/10 border border-red-400/20 rounded-lg"
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
            className="flex items-center gap-6 p-4 rounded-xl bg-white/5 border border-white/10"
          >
            <ArcGauge pct={result.fpi_score * 100} color={fpiColor(result.fpi_score)} />
            <div>
              <div className="font-serif text-4xl font-bold leading-none" style={{ color: fpiColor(result.fpi_score) }}>
                {Math.round(result.fpi_score * 100)}%
              </div>
              <div className="mt-1 text-[11px] font-medium text-white/50">Current Risk Index</div>
              <div className="mt-2 text-[10px] uppercase tracking-widest font-bold" style={{ color: tierColor(result.alert_tier) }}>
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
      <path d={trackPath} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" strokeLinecap="round" />
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
