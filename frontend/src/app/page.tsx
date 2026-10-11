'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { Radio, Cpu, Target, BellRing, MessageCircle, ArrowRight, ArrowUpRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Alert, formatFPI, tierBadgeClass, tierColor, getRiskLevel } from '@/lib/api';
import { useAlerts, useRetrospective } from '@/lib/hooks';
import SearchMeter from '@/components/SearchMeter';

const RiskMap = dynamic(() => import('@/components/map/RiskMap'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[460px] items-center justify-center bg-paper-2">
      <div className="text-center">
        <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-forest border-t-transparent" />
        <p className="eyebrow">Loading map</p>
      </div>
    </div>
  ),
});

type ViewMode = 'live' | 'audit';

const PIPELINE_STEPS = [
  {
    icon: Radio, label: 'Data ingestion', sublabel: 'Raw signals', art: '/art2/p1.webp',
    detail: 'NASA GPM rainfall, SMAP soil moisture, Copernicus DEM, Sentinel-2 NDVI and the NOAA GFS forecast, pulled on a 6-hour cycle.',
  },
  {
    icon: Cpu, label: 'FPI model', sublabel: 'Physics-based', art: '/art2/p2.webp',
    detail: 'Weighted multi-signal fusion into a Failure Probability Index (0-100%), with Monte Carlo confidence bounds per cell.',
  },
  {
    icon: Target, label: 'Tier classification', sublabel: 'Block-level', art: '/art2/p3.webp',
    detail: 'Watch at 40%, Warning at 65%, Emergency at 80%, with spatial clustering across 1 km² grid cells rolled up to blocks.',
  },
  {
    icon: BellRing, label: 'Alert dispatch', sublabel: 'CAP v1.2', art: '/art2/p4.webp',
    detail: 'Structured alerts published through the REST API and a CAP v1.2 XML feed, built to be consumable by NDMA Sachet-style systems.',
  },
  {
    icon: MessageCircle, label: 'WhatsApp', sublabel: 'Planned channel', art: '/art2/p4.webp',
    detail: 'Village-level dispatch in local languages is part of the design. Reply handling closes the feedback loop.',
  },
];

export default function DashboardPage() {
  const { alerts, stats, lastRun, loading, isSample } = useAlerts();
  const { summary } = useRetrospective();
  const [mode, setMode] = useState<ViewMode>('live');
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('view') === 'audit') setMode('audit');
  }, []);

  const sorted = useMemo(() => [...alerts].sort((a, b) => b.fpi_score - a.fpi_score), [alerts]);
  const selectedAlert = useMemo(
    () => alerts.find((a) => a.id === selectedAlertId) ?? sorted[0] ?? null,
    [alerts, sorted, selectedAlertId],
  );

  return (
    <main className="min-h-screen overflow-x-clip">
      {/* ── Hero ── */}
      <section className="relative">
        <Branch side="left" />
        <Branch side="right" />
        <div className="relative z-10 mx-auto max-w-[1280px] px-5 pb-10 pt-14 text-center sm:px-8 sm:pt-20">
          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <span className="inline-flex items-center gap-2 rounded-full border border-ink/10 bg-paper-card/80 px-3.5 py-1.5 text-[12px] font-medium text-ink/70">
              <span className="h-1.5 w-1.5 rounded-full bg-saffron" />
              India-wide landslide intelligence
            </span>
            <h1 className="display mx-auto mt-6 max-w-[880px] text-[44px] sm:text-[64px] lg:text-[76px]">
              SlopeSense reads <em className="whitespace-nowrap">the slope</em> before it breaks.
            </h1>
            <p className="mx-auto mt-5 max-w-[560px] text-[17px] leading-relaxed text-ink/60">
              A prototype for model-generated landslide risk scores and CAP-format feeds. Sample data is labeled. Scores are not calibrated probabilities or official government warnings.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <a href="#console" onClick={() => setMode('live')} className="btn btn-primary">Open risk console</a>
              <a href="#console" onClick={() => setMode('audit')} className="btn btn-ghost">Read the audit</a>
            </div>
          </motion.div>
        </div>

        {/* ── Console window ── */}
        <div id="console" className="relative z-10 mx-auto max-w-[1280px] scroll-mt-24 px-4 pb-6 sm:px-8">
          <motion.div
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.15 }}
            className="overflow-hidden rounded-[22px] border border-ink/10 bg-paper-card shadow-glass-lg"
          >
            <div className="flex items-center justify-between gap-3 border-b border-ink/10 bg-paper-2/60 px-4 py-3 sm:px-5">
              <div className="flex items-center gap-3">
                <div className="hidden gap-1.5 sm:flex" aria-hidden="true">
                  <span className="h-2.5 w-2.5 rounded-full bg-ink/15" />
                  <span className="h-2.5 w-2.5 rounded-full bg-ink/15" />
                  <span className="h-2.5 w-2.5 rounded-full bg-ink/15" />
                </div>
                <div>
                  <div className="text-[13px] font-medium text-ink">Risk console</div>
                  <div className="text-[11px] text-ink/50">
                    {isSample ? 'Sample data · no live model run yet' : lastRun ? `Last model run ${new Date(lastRun).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}` : 'Waiting for first run'}
                  </div>
                </div>
              </div>
              <div role="tablist" aria-label="Console view" className="flex rounded-full border border-ink/10 bg-paper p-1 text-[13px]">
                {(['live', 'audit'] as ViewMode[]).map((m) => (
                  <button
                    key={m}
                    role="tab"
                    aria-selected={mode === m}
                    onClick={() => setMode(m)}
                    className={`focus-ring rounded-full px-4 py-1.5 font-medium capitalize transition-colors ${mode === m ? 'bg-forest text-paper' : 'text-ink/60 hover:text-ink'}`}
                  >
                    {m === 'live' && isSample ? 'Sample' : m}
                  </button>
                ))}
              </div>
            </div>

            <AnimatePresence mode="wait">
              {mode === 'live' ? (
                <motion.div
                  key="live"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="grid lg:h-[680px] lg:grid-cols-[300px_minmax(0,1fr)_340px]"
                >
                  {/* feed */}
                  <div className="order-2 flex min-h-0 flex-col border-ink/10 lg:order-1 lg:border-r">
                    <div className="px-5 pb-2 pt-5">
                      <div className="eyebrow">{isSample ? 'Sample feed' : 'Model feed'}</div>
                      <div className="mt-1 font-serif text-[24px] leading-tight">Active blocks</div>
                    </div>
                    <div className="custom-scrollbar min-h-0 flex-1 space-y-2 overflow-y-auto px-3 pb-3">
                      {loading ? (
                        <div className="space-y-2 px-2">{[0, 1, 2, 3].map((i) => <div key={i} className="h-[68px] animate-pulse rounded-2xl bg-ink/5" />)}</div>
                      ) : sorted.length ? (
                        sorted.map((alert) => (
                          <AlertLine key={alert.id} alert={alert} active={selectedAlert?.id === alert.id} onClick={() => setSelectedAlertId(alert.id)} />
                        ))
                      ) : (
                        <p className="px-3 py-8 text-center text-[14px] text-ink/50">No active alerts above the watch threshold.</p>
                      )}
                    </div>
                    <div className="border-t border-ink/10 px-5 py-3">
                      <Link href="/districts" className="inline-flex items-center gap-1.5 text-[13px] font-medium text-forest hover:text-ink">
                        View all districts <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  </div>

                  {/* map */}
                  <div className="order-1 h-[440px] border-b border-ink/10 lg:order-2 lg:h-auto lg:border-b-0">
                    <RiskMap userSelected={selectedAlertId !== null} alerts={alerts} selectedAlert={selectedAlert} onAlertClick={(a: Alert) => setSelectedAlertId(a.id)} isSample={isSample} />
                  </div>

                  {/* detail */}
                  <div className="custom-scrollbar order-3 overflow-y-auto border-t border-ink/10 p-5 lg:border-l lg:border-t-0">
                    <AnimatePresence mode="wait">
                      {selectedAlert ? <Detail key={selectedAlert.id} alert={selectedAlert} /> : <p className="py-10 text-center text-[14px] text-ink/50">Select a block from the map or the feed.</p>}
                    </AnimatePresence>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="audit"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="grid gap-8 p-5 sm:p-8 lg:grid-cols-[0.8fr_1.2fr]"
                >
                  <Audit summary={summary} />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* metric strip */}
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Active blocks" value={`${stats.total}`} detail="High-risk zones monitored" />
            <Metric label="High risk" value={`${stats.warning}`} detail="Model score in the warning band" tone="#ea580c" />
            <Metric label="Critical" value={`${stats.emergency}`} detail="Model score in the highest band" tone="#dc2626" />
            <Metric label="Retrospective" value={summary ? `${summary.flagged_at_t24}/${summary.total_events}` : '-'} detail="Illustrative replay, not validated lead time" tone="#2f7a4d" />
          </div>
        </div>
      </section>

      {/* ── Pipeline ── */}
      <section className="relative mt-24 sm:mt-32">
        <div className="mx-auto max-w-[1280px] px-5 sm:px-8">
          <Reveal className="mx-auto max-w-[720px] text-center">
            <p className="eyebrow">How it works</p>
            <h2 className="display mt-4 text-[38px] sm:text-[56px]">
              From a satellite pass to <em>a phone in a village</em>
            </h2>
            <p className="mx-auto mt-4 max-w-[540px] text-[16px] text-ink/60">The intended six-hour pipeline has five steps. Pick a step to see what happens inside it.</p>
          </Reveal>

          <Reveal className="mt-12 grid items-center gap-8 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-14">
            <ol className="space-y-2">
              {PIPELINE_STEPS.map((s, i) => {
                const Icon = s.icon;
                const active = step === i;
                return (
                  <li key={s.label}>
                    <button
                      onClick={() => setStep(i)}
                      aria-pressed={active}
                      className={`focus-ring flex w-full items-start gap-4 rounded-2xl border p-4 text-left transition-all ${active ? 'border-ink/10 bg-paper-card shadow-glass' : 'border-transparent hover:bg-paper-card/60'}`}
                    >
                      <span className={`mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl transition-colors ${active ? 'bg-forest text-paper' : 'bg-forest/10 text-forest'}`}>
                        <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
                      </span>
                      <span className="min-w-0">
                        <span className="flex items-baseline gap-2">
                          <span className="font-serif text-[22px] leading-tight text-ink">{s.label}</span>
                          <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-ink/40">{s.sublabel}</span>
                        </span>
                        {active && <span className="mt-1.5 block text-[14px] leading-relaxed text-ink/60">{s.detail}</span>}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>

            <div className="relative">
              <div className="relative aspect-[4/3] overflow-hidden rounded-[26px] border border-ink/10 bg-paper-2 shadow-glass-lg">
                <AnimatePresence mode="wait">
                  <motion.img
                    key={PIPELINE_STEPS[step].art + step}
                    src={PIPELINE_STEPS[step].art}
                    alt=""
                    initial={{ opacity: 0, scale: 1.03 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.45 }}
                    className="absolute inset-0 h-full w-full object-cover"
                  />
                </AnimatePresence>
              </div>
              <div className="absolute -bottom-5 left-5 right-5 rounded-2xl border border-ink/10 bg-paper-card/95 p-4 shadow-glass-lg backdrop-blur sm:left-auto sm:max-w-[320px]">
                <div className="eyebrow">Step {step + 1} of {PIPELINE_STEPS.length}</div>
                <div className="mt-1 font-serif text-[20px] leading-snug">{PIPELINE_STEPS[step].label}</div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Ground truth (sky band) ── */}
      <section className="sky-band mt-28 py-24 sm:mt-36 sm:py-28">
        <div className="mx-auto max-w-[1280px] px-5 sm:px-8">
          <Reveal className="mx-auto max-w-[720px] text-center">
            <p className="eyebrow">Proposed public data inputs</p>
            <h2 className="display mt-4 text-[38px] sm:text-[56px]">
              No new hardware <em>on the hill</em>
            </h2>
            <p className="mx-auto mt-4 max-w-[560px] text-[16px] text-ink/60">
              Rainfall, soil moisture, slope and forecast signals already exist in public data. The design fuses them into a model score. The prototype may show synthetic inputs when labeled sample.
            </p>
          </Reveal>

          <Reveal className="mt-14 grid gap-5 md:grid-cols-3">
            <GroundCard big="6" unit="feeds" title="Free satellite and model feeds" body="Fused per cell: GPM, SMAP, Copernicus DEM, Sentinel-2, GFS and static terrain layers." art="/art2/p1.webp" />
            <GroundCard big="1" unit="km²" title="Grid resolution" body="Scored cell by cell, then rolled up to blocks so the answer matches an administrative unit." art="/art2/p2.webp" />
            <GroundCard big="6" unit="h" title="Refresh cycle" body="The design targets six-hour runs. Check system status for the last confirmed run." art="/art2/p3.webp" />
          </Reveal>
        </div>
      </section>

      {/* ── Evidence ── */}
      <section className="mx-auto mt-28 max-w-[1280px] px-5 sm:mt-36 sm:px-8">
        <Reveal className="text-center">
          <img src="/art2/dragonfly.webp" alt="" className="mx-auto mb-6 h-16 w-16 object-contain" />
          <p className="eyebrow">Evidence, not claims</p>
          <h2 className="display mx-auto mt-4 max-w-[760px] text-[38px] sm:text-[56px]">
            Illustrative <em className="whitespace-nowrap">event replays</em>, in the open
          </h2>
        </Reveal>
        <Reveal className="mt-14 grid items-stretch gap-5 lg:grid-cols-[1fr_1.1fr_1fr]">
          <EvidenceCard
            eyebrow="Retrospective · Wayanad 2024"
            title="Synthetic replay, not a real warning"
            body="The bundled Wayanad example uses synthetic inputs and illustrative scores. It does not establish predictive accuracy or a warning delivered before the event."
            action={{ label: 'Open the audit', onClick: () => { setMode('audit'); document.getElementById('console')?.scrollIntoView({ behavior: 'smooth' }); } }}
          />
          <div className="relative min-h-[300px] overflow-hidden rounded-[26px] border border-ink/10 bg-paper-2 shadow-glass">
            <img src="/art2/p4.webp" alt="A villager reading an alert on a phone" className="absolute inset-0 h-full w-full object-cover" />
          </div>
          <EvidenceCard
            eyebrow="Architecture"
            title="CAP v1.2 native"
            body="Alerts are published as CAP XML and JSON through a REST API, so any system that speaks the Common Alerting Protocol can consume them."
            action={{ label: 'API reference', href: '/api-docs' }}
          />
        </Reveal>

        <Reveal className="mx-auto mt-16 max-w-[760px]">
          <SearchMeter />
        </Reveal>
      </section>
    </main>
  );
}

/* ───────────────────────── pieces ───────────────────────── */

function Branch({ side }: { side: 'left' | 'right' }) {
  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none absolute top-0 z-0 hidden w-[320px] select-none lg:block xl:w-[400px] ${side === 'left' ? '-left-10' : '-right-10'}`}
      style={{ transform: side === 'left' ? 'scaleX(-1)' : undefined }}
    >
      <img src="/art2/branch.webp" alt="" className="h-auto w-full opacity-95" />
    </div>
  );
}

function Reveal({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 22 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function Metric({ label, value, detail, tone }: { label: string; value: string; detail: string; tone?: string }) {
  return (
    <div className="rounded-2xl border border-ink/10 bg-paper-card p-5 shadow-glass">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full" style={{ background: tone ?? '#1d2a21' }} />
        <span className="eyebrow">{label}</span>
      </div>
      <div className="mt-2 font-serif text-[44px] leading-none tracking-tight text-ink">{value}</div>
      <p className="mt-2 text-[13px] text-ink/55">{detail}</p>
    </div>
  );
}

function AlertLine({ alert, active, onClick }: { alert: Alert; active: boolean; onClick: () => void }) {
  const color = tierColor(alert.tier);
  const rl = getRiskLevel(alert.fpi_score);
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`focus-ring flex w-full items-center gap-3 rounded-2xl border p-3.5 text-left transition-all ${active ? 'border-ink/15 bg-paper shadow-glass' : 'border-transparent hover:bg-paper'}`}
    >
      <span className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full text-[13px] font-semibold text-white" style={{ background: color }}>
        {Math.round(alert.fpi_score * 100)}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-serif text-[19px] leading-tight text-ink">{alert.block_name}</span>
        <span className="block truncate text-[12px] text-ink/55">{alert.district_name}, {alert.state_name}</span>
      </span>
      <span className="flex-shrink-0 text-[11px] font-medium" style={{ color: rl.color }}>{rl.label.charAt(0) + rl.label.slice(1).toLowerCase()}</span>
    </button>
  );
}

function Detail({ alert }: { alert: Alert }) {
  const rl = getRiskLevel(alert.fpi_score);
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }} className="space-y-5">
      <div>
        <div className="eyebrow">Selected block</div>
        <div className="mt-1 flex items-start justify-between gap-3">
          <div>
            <div className="font-serif text-[30px] leading-tight text-ink">{alert.block_name}</div>
            <div className="text-[13px] text-ink/55">{alert.district_name}, {alert.state_name}</div>
          </div>
          <span className={`mt-1 shrink-0 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] ${tierBadgeClass(alert.tier)}`}>{alert.tier}</span>
        </div>
      </div>

      <div className="rounded-2xl p-4" style={{ background: `${rl.color}10`, border: `1px solid ${rl.color}30` }}>
        <div className="flex items-center gap-2 text-[14px] font-semibold" style={{ color: rl.color }}>
          <span className="h-2 w-2 rounded-full" style={{ background: rl.color }} />
          {rl.short}
        </div>
        <p className="mt-1.5 text-[13px] leading-relaxed text-ink/70">{rl.description}</p>
        <p className="mt-2 text-[12px] font-medium leading-relaxed" style={{ color: rl.color }}>Action: {rl.action}</p>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <Stat label="FPI score" value={formatFPI(alert.fpi_score)} strong />
        <Stat label="24 h forecast" value={formatFPI(alert.fpi_24h)} />
        <Stat label="95% CI" value={`${Math.round(alert.fpi_ci_lower * 100)}-${Math.round(alert.fpi_ci_upper * 100)}%`} />
        <Stat label="Breach fraction" value={`${Math.round(alert.breach_fraction * 100)}%`} />
      </div>

      <div>
        <div className="eyebrow mb-3">Signal breakdown</div>
        <div className="space-y-3">
          <Bar label="Rainfall 3 d" value={`${Math.round(alert.rainfall_3d_mm || 0)} mm`} pct={Math.min(100, (alert.rainfall_3d_mm || 0) / 3)} color="#3b7aa3" />
          <Bar label="Soil moisture" value={`${Math.round(alert.soil_moisture_percentile || 0)}%`} pct={alert.soil_moisture_percentile || 0} color="#b8730f" />
        </div>
        {alert.dominant_signals?.length > 0 && (
          <p className="mt-3 text-[12px] text-ink/55">
            Dominant signal: <span className="font-medium capitalize text-ink">{alert.dominant_signals[0].signal.replace(/_/g, ' ')}</span>
          </p>
        )}
      </div>

      <Link href={`/alert?id=${encodeURIComponent(alert.id)}`} className="inline-flex items-center gap-1.5 text-[13px] font-medium text-forest hover:text-ink">
        Full alert detail <ArrowUpRight className="h-3.5 w-3.5" />
      </Link>
    </motion.div>
  );
}

function Stat({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`rounded-xl border p-3 ${strong ? 'border-forest/25 bg-forest/[0.06]' : 'border-ink/10 bg-paper'}`}>
      <div className="eyebrow !text-[10px]">{label}</div>
      <div className="mt-1 font-serif text-[26px] leading-none text-ink">{value}</div>
    </div>
  );
}

function Bar({ label, value, pct, color }: { label: string; value: string; pct: number; color: string }) {
  return (
    <div className="grid grid-cols-[92px_1fr_56px] items-center gap-3 text-[12px]">
      <span className="text-ink/65">{label}</span>
      <span className="h-1.5 overflow-hidden rounded-full bg-ink/10"><span className="block h-full rounded-full" style={{ width: `${pct}%`, background: color }} /></span>
      <span className="text-right tabular-nums text-ink/80">{value}</span>
    </div>
  );
}

function Audit({ summary }: { summary: ReturnType<typeof useRetrospective>['summary'] }) {
  if (!summary) return <p className="col-span-full py-10 text-center text-[14px] text-ink/50">Retrospective results unavailable. No substitute validation is shown.</p>;
  return (
    <>
      <div className="space-y-4">
        <div>
          <div className="eyebrow">Retrospective examples, not validation</div>
          <h3 className="mt-1 font-serif text-[30px] leading-tight">Illustrative event replay</h3>
        </div>
        <div className="grid grid-cols-2 gap-2.5">
          <Stat label="Total events" value={`${summary.total_events}`} />
          <Stat label="Flagged at T-24 h" value={`${summary.flagged_at_t24}`} strong />
        </div>
        <div className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-[13px] font-medium ${summary.passed ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-red-500/30 bg-red-500/10 text-red-400'}`}>
          <span className={`h-2 w-2 rounded-full ${summary.passed ? 'bg-emerald-400' : 'bg-red-400'}`} />
          {summary.flagged_at_t24}/{summary.total_events} events flagged at T-24 h
        </div>
        <div className="rounded-2xl border border-saffron-deep/20 bg-saffron-soft/60 p-5">
          <div className="eyebrow !text-saffron-deep">Key finding</div>
          <p className="mt-2 text-[14px] leading-relaxed text-ink/80">
            Bundled replay scores are synthetic examples. They do not show a real pre-event model run, a delivered warning, or validated forecast skill.
          </p>
        </div>
      </div>
      <div>
        <div className="eyebrow mb-3">Event examples</div>
        <ul className="grid gap-2.5 sm:grid-cols-2">
          {summary.results.map((r, i) => (
            <motion.li
              key={r.event_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-2xl border border-ink/10 bg-paper p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-serif text-[20px] leading-tight">{r.event_name}</div>
                  <div className="mt-0.5 text-[11px] uppercase tracking-[0.1em] text-ink/45">{r.state} · {r.district} · Source: {r.data_source || 'unverified'}</div>
                </div>
                <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] ${r.flagged_at_t24 ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-red-500/30 bg-red-500/10 text-red-400'}`}>
                  {r.flagged_at_t24 ? 'Flagged' : 'Missed'}
                </span>
              </div>
              {r.notes && <p className="mt-2.5 text-[12px] leading-relaxed text-ink/60">{r.notes}</p>}
            </motion.li>
          ))}
        </ul>
      </div>
    </>
  );
}

function GroundCard({ big, unit, title, body, art }: { big: string; unit: string; title: string; body: string; art: string }) {
  return (
    <div className="flex flex-col overflow-hidden rounded-[24px] border border-ink/10 bg-paper-card shadow-glass">
      <div className="relative h-44 overflow-hidden bg-paper-2">
        <img src={art} alt="" className="h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-paper-card/60 to-transparent" />
      </div>
      <div className="flex flex-1 flex-col p-6">
        <div className="flex items-baseline gap-1.5">
          <span className="font-serif text-[52px] leading-none text-ink">{big}</span>
          <span className="text-[16px] text-ink/55">{unit}</span>
        </div>
        <h3 className="mt-3 font-serif text-[21px] leading-snug">{title}</h3>
        <p className="mt-2 text-[14px] leading-relaxed text-ink/60">{body}</p>
      </div>
    </div>
  );
}

function EvidenceCard({ eyebrow, title, body, action }: { eyebrow: string; title: string; body: string; action: { label: string; href?: string; onClick?: () => void } }) {
  return (
    <div className="flex flex-col justify-between rounded-[26px] border border-ink/10 bg-paper-card p-7 shadow-glass">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h3 className="mt-3 font-serif text-[30px] leading-tight">{title}</h3>
        <p className="mt-3 text-[15px] leading-relaxed text-ink/60">{body}</p>
      </div>
      <div className="mt-6">
        {action.href ? (
          <Link href={action.href} className="inline-flex items-center gap-1.5 text-[14px] font-medium text-forest hover:text-ink">{action.label} <ArrowRight className="h-4 w-4" /></Link>
        ) : (
          <button onClick={action.onClick} className="focus-ring inline-flex items-center gap-1.5 text-[14px] font-medium text-forest hover:text-ink">{action.label} <ArrowRight className="h-4 w-4" /></button>
        )}
      </div>
    </div>
  );
}
