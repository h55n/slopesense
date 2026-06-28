'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { api, Alert, apiUrl, formatFPI, tierBadgeClass, fpiColor, tierColor } from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const LANGUAGES = [
  { code: 'hi', name: 'हि', label: 'Hindi'      },
  { code: 'ml', name: 'മ',  label: 'Malayalam'  },
  { code: 'kn', name: 'ಕ',  label: 'Kannada'    },
  { code: 'mr', name: 'म',  label: 'Marathi'    },
  { code: 'bn', name: 'ব',  label: 'Bengali'    },
  { code: 'ta', name: 'த',  label: 'Tamil'      },
  { code: 'en', name: 'EN', label: 'English'    },
];

const WA_TEMPLATES: Record<string, (a: Alert) => string> = {
  hi: (a) => `⚠️ भूस्खलन चेतावनी — ${a.district_name}, ${a.state_name}\n\nखंड: ${a.block_name}\nFPI स्कोर: ${formatFPI(a.fpi_score)} (CI: ${formatFPI(a.fpi_ci_lower)}–${formatFPI(a.fpi_ci_upper)})\n24h पूर्वानुमान: ${formatFPI(a.fpi_24h || 0)}\n\nतत्काल कार्रवाई करें।`,
  ml: (a) => `⚠️ മണ്ണിടിച്ചിൽ മുന്നറിയിപ്പ് — ${a.district_name}\n\nബ്ലോക്ക്: ${a.block_name}\nFPI: ${formatFPI(a.fpi_score)}\n\nഉടൻ നടപടി ആവശ്യം.`,
  kn: (a) => `⚠️ ಭೂಕುಸಿತ ಎಚ್ಚರಿಕೆ — ${a.district_name}\n\nFPI: ${formatFPI(a.fpi_score)}\n\nತಕ್ಷಣ ಕ್ರಮ ಕೈಗೊಳ್ಳಿ.`,
  mr: (a) => `⚠️ भूस्खलन इशारा — ${a.district_name}\n\nFPI: ${formatFPI(a.fpi_score)}\n\nत्वरित कारवाई करा.`,
  bn: (a) => `⚠️ ভূমিধস সতর্কতা — ${a.district_name}\n\nFPI: ${formatFPI(a.fpi_score)}\n\nতাৎক্ষণিক পদক্ষেপ নিন।`,
  ta: (a) => `⚠️ நிலச்சரிவு எச்சரிக்கை — ${a.district_name}\n\nFPI: ${formatFPI(a.fpi_score)}\n\nஉடனடியாக நடவடிக்கை எடுங்கள்.`,
  en: (a) => `⚠️ LANDSLIDE ${a.tier} — ${a.district_name}, ${a.state_name}\n\nBlock: ${a.block_name}\nFPI Score: ${formatFPI(a.fpi_score)} (95% CI: ${formatFPI(a.fpi_ci_lower)}–${formatFPI(a.fpi_ci_upper)})\n24h Forecast: ${formatFPI(a.fpi_24h || 0)}\n3-day Rainfall: ${a.rainfall_3d_mm} mm | Soil Moisture: ${a.soil_moisture_percentile}th %ile\n\nReply NO EVENT if no hazard observed.`,
};

// ── Tier header gradients ─────────────────────────────────────────────────────

const TIER_GRADIENT: Record<string, string> = {
  EMERGENCY:  'from-lime-400/10 via-transparent to-transparent',
  WARNING:    'from-red-500/10 via-transparent to-transparent',
  WATCH:      'from-amber-500/10 via-transparent to-transparent',
  NORMAL:     'from-emerald-500/8 via-transparent to-transparent',
  MONITORING: 'from-zinc-600/8 via-transparent to-transparent',
};

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AlertDetailPage() {
  const params  = useParams();
  const alertId = params?.id as string;

  const [alert,        setAlert]        = useState<Alert | null>(null);
  const [loading,      setLoading]      = useState(true);
  const [selectedLang, setSelectedLang] = useState('en');
  const [capXml,       setCapXml]       = useState<string | null>(null);
  const [showXml,      setShowXml]      = useState(false);

  useEffect(() => {
    if (!alertId) return;
    api.alertDetail(alertId)
      .then(a => { setAlert(a); setLoading(false); })
      .catch(() => { setAlert(DEMO_ALERT); setLoading(false); });
  }, [alertId]);

  useEffect(() => {
    if (!alert) return;
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/v1/cap/feed?min_fpi=0.0`)
      .then(r => r.text())
      .then(xml => setCapXml(xml))
      .catch(() => setCapXml(null));
  }, [alert]);

  if (loading) return <AlertDetailSkeleton />;
  if (!alert)  return (
    <div className="flex min-h-screen items-center justify-center bg-slope-bg text-white/40 text-sm">
      Alert not found
    </div>
  );

  const signalData = alert.dominant_signals?.map(s => ({
    name:  s.signal.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    value: Math.round(s.value * 100),
  })) ?? [];

  const waMessage    = WA_TEMPLATES[selectedLang]?.(alert) ?? WA_TEMPLATES.en(alert);
  const fpiPct       = Math.round(alert.fpi_score * 100);
  const ciLo         = Math.round(alert.fpi_ci_lower * 100);
  const ciHi         = Math.round(alert.fpi_ci_upper * 100);
  const fpi24Pct     = Math.round((alert.fpi_24h || 0) * 100);
  const accentColor  = fpiColor(alert.fpi_score);
  const gradientKey  = alert.tier in TIER_GRADIENT ? alert.tier : 'NORMAL';

  return (
    <div className="editorial-shell min-h-screen bg-slope-bg text-white">

      {/* ── Header ── */}
      <header className={`relative border-b border-white/6 px-6 py-8 bg-gradient-to-b ${TIER_GRADIENT[gradientKey]}`}>
        <div className="mx-auto max-w-6xl">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.22em] text-white/30">
            <Link href="/" className="hover:text-slope-accent transition-colors">SlopeSense</Link>
            <span className="text-white/15">/</span>
            <Link href={`/districts/${alert.state_code}`} className="hover:text-white/70 transition-colors">
              {alert.state_name}
            </Link>
            <span className="text-white/15">/</span>
            <span className="text-white/70">{alert.district_name}</span>
          </nav>

          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <motion.h1
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="font-serif text-4xl sm:text-5xl font-bold text-white"
                >
                  {alert.block_name}
                </motion.h1>
                <motion.span
                  initial={{ opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1 }}
                  className={`shrink-0 inline-flex rounded-full px-3.5 py-1.5 text-[10px] font-bold uppercase tracking-[0.18em] ${tierBadgeClass(alert.tier)}`}
                >
                  {alert.tier}
                </motion.span>
              </div>
              <p className="text-[12px] font-medium tracking-wide text-white/40">
                {alert.district_name} · {alert.state_name} ·{' '}
                Issued {new Date(alert.issued_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
              </p>
            </div>
            <motion.a
              whileHover={{ scale: 1.02, y: -1 }}
              whileTap={{ scale: 0.98 }}
              href={apiUrl(`/v1/districts/${alert.district_code}/report.pdf`)}
              target="_blank"
              rel="noopener noreferrer"
              id="download-pdf-btn"
              className="shrink-0 inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/5 px-5 py-2.5 text-[10px] font-bold uppercase tracking-[0.2em] text-white/70 hover:bg-white/10 hover:border-white/25 hover:text-white transition-all shadow-glass"
            >
              <span>↓</span> PDF Report
            </motion.a>
          </div>
        </div>
      </header>

      {/* ── Main content ── */}
      <main className="mx-auto max-w-6xl px-6 py-10">
        <motion.div
          initial="hidden"
          animate="visible"
          variants={{ visible: { transition: { staggerChildren: 0.1 } } }}
          className="grid gap-6 lg:grid-cols-2"
        >

          {/* ── FPI Score Summary ── */}
          <motion.section variants={fadeUp} className="glass-panel p-7">
            <SectionLabel>FPI Score Summary</SectionLabel>

            {/* Arc gauge */}
            <div className="flex items-center gap-6 mb-8">
              <ArcGauge pct={fpiPct} color={accentColor} />
              <div>
                <div className="font-serif text-6xl font-bold leading-none" style={{ color: accentColor }}>
                  {fpiPct}%
                </div>
                <div className="mt-2 text-[11px] font-medium text-white/40">Current FPI</div>
                <div className="mt-1 font-mono text-[10px] text-white/30 tracking-wider">
                  95% CI: {ciLo}% – {ciHi}%
                </div>
                {alert.is_suppressed && (
                  <div className="mt-2 text-[10px] font-bold text-amber-400 bg-amber-500/8 border border-amber-500/20 rounded-full px-3 py-1">
                    ⚠ High uncertainty — suppressed
                  </div>
                )}
              </div>
            </div>

            {/* CI bar */}
            <div className="mb-6">
              <div className="flex justify-between text-[9px] font-bold uppercase tracking-[0.2em] text-white/25 mb-2">
                <span>0%</span><span>50%</span><span>100%</span>
              </div>
              <div className="relative h-2 rounded-full overflow-hidden bg-white/5 border border-white/6">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${ciHi - ciLo}%` }}
                  transition={{ duration: 1.2, delay: 0.2, ease: 'easeOut' }}
                  className="absolute h-full rounded-full opacity-25"
                  style={{ left: `${ciLo}%`, backgroundColor: accentColor }}
                />
                <motion.div
                  initial={{ left: '0%' }}
                  animate={{ left: `${fpiPct - 0.5}%` }}
                  transition={{ duration: 0.9, type: 'spring', stiffness: 80 }}
                  className="absolute h-full w-0.5 rounded shadow-md"
                  style={{ backgroundColor: accentColor }}
                />
              </div>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-3">
              <DetailCard label="24h Forecast"       value={`${fpi24Pct}%`}                        color={fpiColor(alert.fpi_24h || 0)} />
              <DetailCard label="Consecutive Cycles" value={`${alert.consecutive_cycles}`}          unit="× 6h" />
              <DetailCard label="3-day Rainfall"     value={`${alert.rainfall_3d_mm}`}              unit="mm" />
              <DetailCard label="Soil Moisture"      value={`${alert.soil_moisture_percentile}`}    unit="th %ile" />
            </div>
          </motion.section>

          {/* ── Signal Breakdown ── */}
          <motion.section variants={fadeUp} className="glass-panel p-7">
            <SectionLabel>Signal Breakdown</SectionLabel>

            {signalData.length === 0 ? (
              <div className="flex h-40 items-center justify-center text-white/30 text-sm">
                No signal data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={signalData} layout="vertical">
                  <XAxis
                    type="number" domain={[0, 100]}
                    tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 600 }}
                    unit="%" stroke="rgba(255,255,255,0.06)"
                  />
                  <YAxis
                    type="category" dataKey="name"
                    tick={{ fill: 'rgba(255,255,255,0.65)', fontSize: 11, fontWeight: 500 }}
                    width={145} stroke="transparent"
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(17,17,20,0.92)',
                      backdropFilter: 'blur(16px)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: 12,
                      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                    }}
                    itemStyle={{ color: '#fff', fontSize: 13, fontWeight: 700 }}
                    formatter={(v) => [`${v}%`, 'Signal strength']}
                  />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]} animationDuration={1400}>
                    {signalData.map((_, i) => (
                      <Cell
                        key={i}
                        fill={i === 0 ? '#c5ff4a' : `rgba(197,255,74,${Math.max(0.25, 0.7 - i * 0.2)})`}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}

            {/* Breach fraction */}
            <div className="mt-5 rounded-xl border border-white/6 bg-white/3 p-4">
              <div className="text-[9px] font-bold uppercase tracking-[0.22em] text-white/35 mb-3">Breach Fraction</div>
              <div className="flex items-center gap-4">
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/5 border border-white/6">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(alert.breach_fraction || 0) * 100}%` }}
                    transition={{ duration: 1.1, delay: 0.5, ease: 'easeOut' }}
                    className="h-full rounded-full bg-slope-accent shadow-glow-lime"
                  />
                </div>
                <span className="text-[12px] font-bold text-white/80 shrink-0">
                  {alert.cell_count_breached}/{alert.cell_count_total} cells
                  <span className="ml-1 text-white/40 font-normal">
                    ({Math.round((alert.breach_fraction || 0) * 100)}%)
                  </span>
                </span>
              </div>
            </div>

            {/* Spatial note */}
            <div className="mt-3 rounded-xl border border-white/5 bg-white/2 px-4 py-3">
              <div className="text-[10px] text-white/35 leading-relaxed">
                <strong className="text-white/60">Dominant signal:</strong>{' '}
                {(alert.dominant_signals?.[0]?.signal || 'rainfall_accumulation').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
              </div>
            </div>
          </motion.section>

          {/* ── WhatsApp Preview ── */}
          <motion.section variants={fadeUp} className="glass-panel p-7">
            <div className="flex items-center justify-between border-b border-white/6 pb-4 mb-5">
              <SectionLabel className="mb-0">WhatsApp Alert Preview</SectionLabel>
              {/* Language tabs */}
              <div className="flex gap-1">
                {LANGUAGES.map(lang => (
                  <button
                    key={lang.code}
                    id={`lang-btn-${lang.code}`}
                    onClick={() => setSelectedLang(lang.code)}
                    title={lang.label}
                    className={`h-7 w-7 rounded-lg text-[11px] font-bold transition-all duration-150 ${
                      selectedLang === lang.code
                        ? 'bg-white text-slope-bg shadow-sm'
                        : 'text-white/40 hover:text-white hover:bg-white/8'
                    }`}
                  >
                    {lang.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Phone mockup */}
            <div className="rounded-2xl border border-white/8 bg-black/50 overflow-hidden">
              {/* WA header */}
              <div className="bg-[#128C7E]/20 border-b border-[#128C7E]/20 px-4 py-3 flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-[#25D366]/80 flex items-center justify-center text-[10px] font-bold text-white">
                  SS
                </div>
                <div>
                  <div className="text-[12px] font-bold text-white">SlopeSense Alert</div>
                  <div className="text-[9px] text-white/40">via WhatsApp Business API</div>
                </div>
                <div className="ml-auto flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#25D366]" />
                  <span className="text-[9px] text-white/30">online</span>
                </div>
              </div>
              {/* Message bubble */}
              <div className="p-4">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={selectedLang}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.2 }}
                    className="inline-block rounded-2xl rounded-tl-sm bg-[#1a1a1a] border border-white/5 px-4 py-3 text-[12px] leading-relaxed text-white/85 whitespace-pre-wrap font-mono max-w-full"
                  >
                    {waMessage}
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>
          </motion.section>

          {/* ── CAP XML Feed ── */}
          <motion.section variants={fadeUp} className="glass-panel p-7">
            <div className="flex items-center justify-between border-b border-white/6 pb-4 mb-5">
              <SectionLabel className="mb-0">CAP v1.2 XML Feed</SectionLabel>
              <button
                onClick={() => setShowXml(v => !v)}
                className="rounded-full border border-white/12 bg-white/4 px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-white/60 hover:bg-white/8 hover:border-white/22 hover:text-white transition-all"
              >
                {showXml ? 'Hide XML' : 'Show XML'}
              </button>
            </div>

            <AnimatePresence mode="wait">
              {showXml ? (
                <motion.pre
                  key="xml"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-x-auto overflow-hidden rounded-xl bg-black/60 border border-white/5 p-4 text-[10px] leading-relaxed text-emerald-400 max-h-60"
                >
                  {capXml || 'Loading CAP XML…'}
                </motion.pre>
              ) : (
                <motion.div
                  key="placeholder"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="rounded-xl bg-white/2 border border-white/5 p-5 space-y-3"
                >
                  <p className="text-[13px] text-white/50 leading-relaxed">
                    CAP v1.2 compliant XML alert feed, compatible with NDMA Sachet and national emergency broadcast systems.
                  </p>
                  <div className="font-mono text-[11px] text-slope-accent/60 bg-black/40 rounded-lg px-4 py-3 border border-white/5">
                    GET /v1/cap/feed?state={alert.state_code}&amp;min_fpi=0.65
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/v1/cap/feed`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex items-center gap-1.5 text-[11px] font-semibold text-white/35 hover:text-slope-accent transition-colors"
            >
              Open live CAP feed ↗
            </a>
          </motion.section>
        </motion.div>
      </main>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

const fadeUp = {
  hidden:  { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const } },
};

function SectionLabel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <h2 className={`mb-5 text-[10px] font-bold uppercase tracking-[0.26em] text-white/35 ${className}`}>
      {children}
    </h2>
  );
}

function DetailCard({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: string;
  unit?: string;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-white/6 bg-white/3 p-4 hover:bg-white/5 transition-colors">
      <div className="text-[9px] font-bold uppercase tracking-[0.2em] text-white/35">{label}</div>
      <div className="mt-2 font-serif text-2xl font-bold" style={color ? { color } : undefined}>
        <span className={color ? '' : 'text-white'}>{value}</span>
        {unit && <span className="ml-1 text-[12px] font-sans font-medium text-white/35">{unit}</span>}
      </div>
    </div>
  );
}

// ── Arc gauge ─────────────────────────────────────────────────────────────────

function ArcGauge({ pct, color }: { pct: number; color: string }) {
  const r           = 42;
  const cx          = 54;
  const cy          = 54;
  const startAngle  = -220; // degrees
  const endAngle    = 40;
  const totalAngle  = endAngle - startAngle; // 260°
  const fillAngle   = (pct / 100) * totalAngle;

  function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function describeArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
    const start   = polarToCartesian(cx, cy, r, endDeg);
    const end     = polarToCartesian(cx, cy, r, startDeg);
    const largeArc = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
  }

  const trackPath = describeArc(cx, cy, r, startAngle, endAngle);
  const fillPath  = fillAngle > 0 ? describeArc(cx, cy, r, startAngle, startAngle + fillAngle) : '';

  return (
    <svg width="108" height="108" viewBox="0 0 108 108" className="shrink-0">
      {/* Track */}
      <path d={trackPath} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="7" strokeLinecap="round" />
      {/* Fill */}
      {fillPath && (
        <motion.path
          d={fillPath}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.2, delay: 0.2, ease: 'easeOut' }}
        />
      )}
      {/* Tick marks at 40%, 65%, 80% */}
      {[40, 65, 80].map(threshold => {
        const angle = startAngle + (threshold / 100) * totalAngle;
        const inner = polarToCartesian(cx, cy, r - 8, angle);
        const outer = polarToCartesian(cx, cy, r + 2, angle);
        return (
          <line
            key={threshold}
            x1={inner.x} y1={inner.y}
            x2={outer.x} y2={outer.y}
            stroke="rgba(255,255,255,0.2)"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        );
      })}
    </svg>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function AlertDetailSkeleton() {
  return (
    <div className="min-h-screen bg-slope-bg p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="h-5 w-44 animate-pulse rounded-full bg-white/8" />
        <div className="h-12 w-72 animate-pulse rounded-xl bg-white/8" />
        <div className="grid gap-6 lg:grid-cols-2 mt-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-64 animate-pulse rounded-2xl bg-white/4" />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Demo alert ────────────────────────────────────────────────────────────────

const DEMO_ALERT: Alert = {
  id: 'demo-1', alert_code: 'KL_WYD_MEPPADI_DEMO',
  state_code: 'KL', state_name: 'Kerala',
  district_code: 'KL_WYD', district_name: 'Wayanad',
  block_code: 'KL_WYD_MEPPADI', block_name: 'Meppadi',
  lat: 11.55, lon: 76.10,
  fpi_score: 0.73, fpi_ci_lower: 0.61, fpi_ci_upper: 0.84, fpi_24h: 0.81,
  tier: 'WARNING', is_active: true, is_suppressed: false, consecutive_cycles: 2,
  dominant_signals: [
    { signal: 'rainfall_accumulation', value: 0.82 },
    { signal: 'soil_moisture',         value: 0.68 },
    { signal: 'slope_angle',           value: 0.54 },
  ],
  rainfall_3d_mm: 183, soil_moisture_percentile: 91,
  cell_count_total: 48, cell_count_breached: 22, breach_fraction: 0.46,
  issued_at: new Date(Date.now() - 3600000).toISOString(),
};
