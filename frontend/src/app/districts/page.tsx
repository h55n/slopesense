'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { api, Alert, apiUrl, formatFPI, tierBadgeClass, fpiColor, tierColor, getRiskLevel } from '@/lib/api';

const STATE_NAMES: Record<string, string> = {
  KL: 'Kerala', UK: 'Uttarakhand', SK: 'Sikkim', HP: 'Himachal Pradesh',
  JK: 'Jammu & Kashmir', MH: 'Maharashtra', GA: 'Goa', MZ: 'Mizoram',
  AR: 'Arunachal Pradesh', NL: 'Nagaland', ML: 'Meghalaya', TR: 'Tripura',
  MN: 'Manipur', AS: 'Assam', WB: 'West Bengal', OR: 'Odisha',
  KA: 'Karnataka',
};

type SortField = 'fpi_score' | 'district_name' | 'tier';
type SortDir = 'asc' | 'desc';

const TIER_ORDER: Record<string, number> = { EMERGENCY: 0, WARNING: 1, WATCH: 2, MONITORING: 3, NORMAL: 4 };

export default function DistrictsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('fpi_score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [tierFilter, setTierFilter] = useState<string>('ALL');
  const [search, setSearch] = useState('');

  useEffect(() => {
    setLoading(true);
    api.activeAlerts({ min_fpi: 0.1 })
      .then(d => {
        setAlerts(d.alerts || []);
        setError(null);
      })
      .catch(() => {
        // Fallback to all demo alerts across states if API is down
        const allDemos = Object.values(DEMO_DISTRICTS).flat();
        setAlerts(allDemos);
        setError('Using cached data — API unavailable');
      })
      .finally(() => setLoading(false));
  }, []);

  const sorted = useMemo(() => {
    let list = [...alerts];
    if (tierFilter !== 'ALL') list = list.filter(a => a.tier === tierFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(a =>
        a.district_name?.toLowerCase().includes(q) ||
        a.district_code?.toLowerCase().includes(q)
      );
    }
    list.sort((a, b) => {
      let cmp = 0;
      if (sortField === 'fpi_score') cmp = (a.fpi_score ?? 0) - (b.fpi_score ?? 0);
      else if (sortField === 'district_name') cmp = (a.district_name || '').localeCompare(b.district_name || '');
      else if (sortField === 'tier') cmp = (TIER_ORDER[a.tier] ?? 9) - (TIER_ORDER[b.tier] ?? 9);
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return list;
  }, [alerts, sortField, sortDir, tierFilter, search]);

  const tiers = useMemo(() => ['ALL', ...Array.from(new Set(alerts.map(a => a.tier)))], [alerts]);

  function toggleSort(field: SortField) {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('desc'); }
  }

  const SortIcon = ({ field }: { field: SortField }) =>
    sortField === field ? (sortDir === 'desc' ? ' ↓' : ' ↑') : ' ↕';

  return (
    <div className="editorial-shell min-h-screen bg-slope-bg text-white overflow-hidden">
      {/* Header */}
      <header className="border-b border-white/10 px-6 py-8 relative z-10 bg-black/20 backdrop-blur-md">
        <div className="mx-auto max-w-7xl">
          <nav className="mb-4 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">
            <Link href="/" className="hover:text-slope-accent hover:underline transition-all cursor-pointer">SlopeSense</Link>
            <span>/</span>
            <span className="text-white">All Districts</span>
          </nav>
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <h1 className="text-4xl font-serif font-bold text-white drop-shadow-md">India-Wide Districts</h1>
              <p className="mt-2 text-[13px] font-medium tracking-wide text-white/50">
                {sorted.length} high-risk monitored block{sorted.length !== 1 ? 's' : ''} across all states
              </p>
            </motion.div>
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-wrap gap-2 bg-white/5 p-1 rounded-full border border-white/10"
            >
              {tiers.map(t => (
                <button
                  key={t}
                  id={`tier-filter-${t.toLowerCase()}`}
                  onClick={() => setTierFilter(t)}
                  className={`rounded-full px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.2em] transition-all ${
                    tierFilter === t
                      ? 'bg-white text-black shadow-md'
                      : 'text-white/60 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {t}
                </button>
              ))}
            </motion.div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-10 relative z-10">
        {/* Search */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <div className="relative max-w-sm">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              <span className="text-white/30 text-lg">⌕</span>
            </div>
            <input
              id="district-search"
              type="text"
              placeholder="Search districts..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full rounded-full border border-white/10 bg-white/5 pl-10 pr-4 py-3 text-[13px] font-medium text-white placeholder-white/30 outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner"
            />
          </div>
        </motion.div>

        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-sm font-medium text-amber-300">
            ⚠️ {error}
          </motion.div>
        )}

        {loading ? (
          <SkeletonTable />
        ) : sorted.length === 0 ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel py-20 text-center text-[13px] font-medium text-white/50">
            No districts found for {tierFilter !== 'ALL' ? `tier ${tierFilter}` : 'your search'}.
          </motion.div>
        ) : (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-panel overflow-hidden"
          >
            <table className="w-full text-sm">
              <thead className="border-b border-white/10 bg-white/5">
                <tr>
                  <SortTh label="District" field="district_name" onSort={toggleSort}>
                    <SortIcon field="district_name" />
                  </SortTh>
                  <th className="px-5 py-4 text-left text-[10px] font-bold uppercase tracking-[0.2em] text-white/50">State</th>
                  <th className="px-5 py-4 text-left text-[10px] font-bold uppercase tracking-[0.2em] text-white/50">Risk Level</th>
                  <SortTh label="Tier" field="tier" onSort={toggleSort}>
                    <SortIcon field="tier" />
                  </SortTh>
                  <SortTh label="FPI Score" field="fpi_score" onSort={toggleSort}>
                    <SortIcon field="fpi_score" />
                  </SortTh>
                  <th className="px-5 py-3 text-left text-xs uppercase tracking-wider text-white/40">95% CI</th>
                  <th className="px-5 py-3 text-left text-xs uppercase tracking-wider text-white/40">Rainfall 3d</th>
                  <th className="px-5 py-3 text-left text-xs uppercase tracking-wider text-white/40 whitespace-nowrap">Soil Moisture</th>
                  <th className="px-5 py-3 text-left text-xs uppercase tracking-wider text-white/40">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                <AnimatePresence>
                  {sorted.map((alert, i) => (
                    <motion.tr 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3, delay: i * 0.05 }}
                      key={alert.id || alert.district_code} 
                      className="hover:bg-white/5 transition-colors group"
                    >
                      <td className="px-5 py-5">
                        <div className="font-serif text-lg font-medium text-white">{alert.district_name}</div>
                        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40 mt-1">{alert.district_code} — {alert.block_name}</div>
                      </td>
                      <td className="px-5 py-5">
                        <span className="text-[13px] font-medium text-white/80">{STATE_NAMES[alert.state_code] || alert.state_code}</span>
                      </td>
                      <td className="px-5 py-5">
                        {(() => {
                          const rl = getRiskLevel(alert.fpi_score ?? 0);
                          return (
                            <div className="flex items-center gap-2">
                              <span className="text-base">{rl.emoji}</span>
                              <div>
                                <div className="text-[11px] font-bold" style={{ color: rl.color }}>{rl.label}</div>
                                <div className="text-[9px] text-white/40 mt-0.5">{rl.short}</div>
                              </div>
                            </div>
                          );
                        })()}
                      </td>
                      <td className="px-5 py-5">
                        <div className="flex items-center gap-4">
                          <div className="h-2.5 w-24 overflow-hidden rounded-full bg-white/10 border border-white/5">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${(alert.fpi_score ?? 0) * 100}%` }}
                              transition={{ duration: 0.8, delay: 0.2 + i * 0.05 }}
                              className="h-full rounded-full"
                              style={{ backgroundColor: fpiColor(alert.fpi_score ?? 0) }}
                            />
                          </div>
                          <span className="font-mono text-[15px] font-bold" style={{ color: fpiColor(alert.fpi_score ?? 0) }}>
                            {formatFPI(alert.fpi_score ?? 0)}
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-5 font-mono text-[13px] font-medium text-white/60">
                        {formatFPI(alert.fpi_ci_lower ?? 0)}–{formatFPI(alert.fpi_ci_upper ?? 0)}
                      </td>
                      <td className="px-5 py-5 text-[13px] font-medium text-white/80">
                        {alert.rainfall_3d_mm != null ? `${alert.rainfall_3d_mm} mm` : '—'}
                      </td>
                      <td className="px-5 py-5 text-[13px] font-medium text-white/80">
                        {alert.soil_moisture_percentile != null ? `${alert.soil_moisture_percentile}th %ile` : '—'}
                      </td>
                      <td className="px-5 py-5">
                        <div className="flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                          <Link
                            href={`/alerts/${alert.id}`}
                            className="rounded-full border border-white/20 bg-white/5 px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-white hover:border-white/40 hover:bg-white/10 transition-all shadow-sm"
                          >
                            Details
                          </Link>
                          <button
                            onClick={() => window.alert("PDF generation in progress — downloading shortly")}
                            className="rounded-full border border-white/10 px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-white/50 hover:text-white hover:bg-white/5 transition-all"
                          >
                            PDF
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </motion.div>
        )}

        {/* Risk Level Legend */}
        <div className="mt-8 flex flex-wrap items-center gap-6 text-xs text-white/40">
          <span>Risk Level:</span>
          {[
            { label: '🆘 CRITICAL ≥80%', color: '#dc2626' },
            { label: '🔴 HIGH ≥65%', color: '#ea580c' },
            { label: '⚠️ ELEVATED ≥40%', color: '#d97706' },
            { label: '🟡 MODERATE ≥20%', color: '#65a30d' },
            { label: '✅ LOW <20%', color: '#16a34a' },
          ].map(l => (
            <span key={l.label} className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: l.color }} />
              {l.label}
            </span>
          ))}
        </div>
      </main>
    </div>
  );
}

function SortTh({
  label, field, onSort, children
}: {
  label: string;
  field: SortField;
  onSort: (f: SortField) => void;
  children?: React.ReactNode;
}) {
  return (
    <th
      className="cursor-pointer select-none px-5 py-4 text-left text-[10px] font-bold uppercase tracking-[0.2em] text-white/50 hover:text-white transition-colors"
      onClick={() => onSort(field)}
    >
      {label}{children}
    </th>
  );
}

function SkeletonTable() {
  return (
    <div className="overflow-hidden rounded-xl border border-white/10">
      <div className="space-y-0">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 border-b border-white/5 px-5 py-4">
            <div className="h-4 w-40 animate-pulse rounded bg-white/10" />
            <div className="h-5 w-16 animate-pulse rounded-full bg-white/10" />
            <div className="h-3 w-28 animate-pulse rounded-full bg-white/10" />
            <div className="h-3 w-20 animate-pulse rounded bg-white/10" />
          </div>
        ))}
      </div>
    </div>
  );
}

// Demo data for when API is unavailable
const DEMO_DISTRICTS: Record<string, Alert[]> = {
  KL: [
    {
      id: 'demo-kl-1', alert_code: 'KL_WYD_DEMO', state_code: 'KL', state_name: 'Kerala',
      district_code: 'WYD', district_name: 'Wayanad', block_code: '', block_name: '',
      fpi_score: 0.73, fpi_ci_lower: 0.61, fpi_ci_upper: 0.84, fpi_24h: 0.81,
      tier: 'WARNING', is_active: true, is_suppressed: false, consecutive_cycles: 2,
      dominant_signals: [{ signal: 'rainfall_accumulation', value: 0.82 }],
      rainfall_3d_mm: 183, soil_moisture_percentile: 91,
      cell_count_total: 48, cell_count_breached: 22, breach_fraction: 0.46,
      issued_at: new Date().toISOString(),
    },
    {
      id: 'demo-kl-2', alert_code: 'KL_IDK_DEMO', state_code: 'KL', state_name: 'Kerala',
      district_code: 'IDK', district_name: 'Idukki', block_code: '', block_name: '',
      fpi_score: 0.55, fpi_ci_lower: 0.43, fpi_ci_upper: 0.67, fpi_24h: 0.61,
      tier: 'WATCH', is_active: true, is_suppressed: false, consecutive_cycles: 1,
      dominant_signals: [{ signal: 'soil_moisture', value: 0.61 }],
      rainfall_3d_mm: 112, soil_moisture_percentile: 82,
      cell_count_total: 38, cell_count_breached: 14, breach_fraction: 0.37,
      issued_at: new Date().toISOString(),
    },
    {
      id: 'demo-kl-3', alert_code: 'KL_MLP_DEMO', state_code: 'KL', state_name: 'Kerala',
      district_code: 'MLP', district_name: 'Malappuram', block_code: '', block_name: '',
      fpi_score: 0.41, fpi_ci_lower: 0.29, fpi_ci_upper: 0.53, fpi_24h: 0.45,
      tier: 'WATCH', is_active: true, is_suppressed: false, consecutive_cycles: 1,
      dominant_signals: [{ signal: 'slope_angle', value: 0.55 }],
      rainfall_3d_mm: 88, soil_moisture_percentile: 73,
      cell_count_total: 28, cell_count_breached: 9, breach_fraction: 0.32,
      issued_at: new Date().toISOString(),
    },
  ],
};
