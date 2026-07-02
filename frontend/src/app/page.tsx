'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import { Alert, formatFPI, tierBadgeClass, tierColor, getRiskLevel, fpiBarColor } from '@/lib/api';
import { useAlerts, useRetrospective } from '@/lib/hooks';
import SearchMeter from '@/components/SearchMeter';

const RiskMap = dynamic(() => import('@/components/map/RiskMap'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center bg-black/50 text-white">
      <div className="text-center">
        <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-slope-accent border-t-transparent" />
        <p className="text-tiny uppercase tracking-[0.2em] text-white/40">Initialising map</p>
      </div>
    </div>
  ),
});

type ViewMode = 'live' | 'audit';

// ── Pipeline steps ────────────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  {
    icon: '📡',
    label: 'Data Ingestion',
    sublabel: 'Raw signals',
    detail: 'NASA GPM rainfall · SMAP soil moisture · Copernicus DEM · Sentinel-2 NDVI · NOAA GFS forecast',
    color: 'rgba(99,179,237,0.9)',
    glow: 'rgba(99,179,237,0.15)',
  },
  {
    icon: '⚙️',
    label: 'FPI Model',
    sublabel: 'Physics-based',
    detail: 'Weighted multi-signal fusion → Failure Probability Index (0–100%) with Monte Carlo CI bounds per cell',
    color: 'rgba(167,139,250,0.9)',
    glow: 'rgba(167,139,250,0.15)',
  },
  {
    icon: '🎯',
    label: 'Tier Classification',
    sublabel: 'Block-level',
    detail: 'WATCH ≥40% · WARNING ≥65% · EMERGENCY ≥80% — spatial clustering across 1km² grid cells',
    color: 'rgba(251,191,36,0.9)',
    glow: 'rgba(251,191,36,0.15)',
  },
  {
    icon: '🔔',
    label: 'Alert Dispatch',
    sublabel: 'CAP v1.2',
    detail: 'Structured alerts pushed via REST API, CAP XML feed (NDMA Sachet-compatible), and email hooks',
    color: 'rgba(239,68,68,0.9)',
    glow: 'rgba(239,68,68,0.15)',
  },
  {
    icon: '📱',
    label: 'WhatsApp',
    sublabel: 'Multilingual',
    detail: 'Gram Pradhan-level dispatch in 7 languages. Reply "NO EVENT" to confirm, closing the feedback loop.',
    color: 'rgba(197,255,74,0.9)',
    glow: 'rgba(197,255,74,0.15)',
  },
];

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { alerts, stats, lastRun, loading } = useAlerts();
  const { summary } = useRetrospective();
  const [mode, setMode] = useState<ViewMode>('live');
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [expandedPipelineStep, setExpandedPipelineStep] = useState<number | null>(null);

  const selectedAlert = useMemo(
    () => alerts.find((a) => a.id === selectedAlertId) ?? alerts[0] ?? null,
    [alerts, selectedAlertId],
  );

  const topSignals = useMemo(
    () => [...alerts].sort((a, b) => b.fpi_score - a.fpi_score).slice(0, 3),
    [alerts],
  );

  return (
    <main className="editorial-shell min-h-screen bg-slope-bg text-white overflow-hidden">
      <div className="mx-auto flex min-h-screen max-w-[1600px] flex-col px-6 sm:px-8 lg:px-12">

        {/* ── Top bar ── */}
        <TopBar mode={mode} setMode={setMode} lastRun={lastRun} stats={stats} summary={summary} />

        {/* ── Hero ── */}
        <section className="grid gap-8 py-14 lg:grid-cols-[1.2fr_0.8fr] lg:py-20 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="space-y-10"
          >
            {/* Headline */}
            <div className="max-w-3xl">
              <motion.div
                initial={{ opacity: 0, scaleX: 0 }}
                animate={{ opacity: 1, scaleX: 1 }}
                transition={{ duration: 0.7, delay: 0.4, ease: 'easeOut' }}
                style={{ transformOrigin: 'left' }}
                className="mb-5 h-px w-10 bg-slope-accent opacity-80"
              />
              <p className="mb-4 text-tiny font-semibold uppercase tracking-[0.28em] text-white/40">
                India-wide landslide intelligence
              </p>
              <h1 className="text-[44px] leading-[1.06] sm:text-[58px] lg:text-[72px] font-serif">
                <span className="block text-white">SlopeSense reads</span>
                <span className="block text-slope-accent">the slope before</span>
                <span className="block text-white">it breaks.</span>
              </h1>
              <p className="mt-6 max-w-xl text-[15px] leading-relaxed text-white/50">
                Operational landslide risk intelligence — live FPI scoring, block-level alerting,
                and a transparent retrospective evidence trail across India.
              </p>
            </div>

            {/* CTA buttons */}
            <div className="flex flex-wrap gap-3">
              <ActionButton label="Open live console" variant="primary" onClick={() => setMode('live')} />
              <ActionButton label="Read the audit" variant="secondary" onClick={() => setMode('audit')} />
            </div>

            {/* Metric cards */}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Active blocks"  value={`${stats.total}`}     detail="Live high-risk zones monitored"  delay={0.1} />
              <MetricCard label="HIGH risk"      value={`${stats.warning}`}   detail="Landslide very likely 24–48h"    delay={0.15} accent="warning" />
              <MetricCard label="CRITICAL risk"  value={`${stats.emergency}`} detail="Landslide imminent — act now"     delay={0.2}  accent="emergency" />
              <MetricCard
                label="Retrospective"
                value={summary ? `${summary.flagged_at_t24}/${summary.total_events}` : '—'}
                detail="Events flagged at T-24h"
                delay={0.25}
                accent={summary?.passed ? 'ok' : 'default'}
              />
            </div>
            
            {/* Search Meter */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <SearchMeter />
            </motion.div>
          </motion.div>

          {/* ── Signal console ── */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="space-y-4"
          >
            <div className="glass-panel overflow-hidden">
              {/* Console header */}
              <div className="flex items-center justify-between border-b border-white/6 px-6 py-4 bg-white/[0.02]">
                <div>
                  <div className="text-tiny font-semibold uppercase tracking-[0.24em] text-white/40">Signal console</div>
                  <div className="mt-1 font-serif text-2xl leading-tight">Operational summary</div>
                </div>
                <LiveBadge />
              </div>

              <div className="p-6">
                <div className="mb-4 flex items-center justify-between">
                  <div className="text-small font-semibold tracking-wide text-white/50">
                    Showing top {topSignals.length} high-risk blocks
                  </div>
                  <div className="text-small font-semibold text-white/30">
                    Last run: {lastRun ? new Date(lastRun).toLocaleTimeString('en-IN') : 'Pending'}
                  </div>
                </div>

                {/* Top signals grid */}
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {topSignals.map((alert) => (
                    <SignalCard
                      key={alert.id}
                      alert={alert}
                      active={selectedAlert?.id === alert.id}
                      onClick={() => setSelectedAlertId(alert.id)}
                    />
                  ))}
                  {!topSignals.length && (
                    <div className="col-span-full py-10 text-center text-base-sm text-white/30 italic glass-panel border-dashed">
                      No high-risk alerts detected currently
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Feature cards */}
            <div className="grid gap-3 sm:grid-cols-2">
              <FeatureCard
                eyebrow="Wayanad 2024"
                title="20h early warning"
                copy="FPI reached 73% for Meppadi before the disaster. WhatsApp alert sent to Gram Pradhan at 6am."
              />
              <FeatureCard
                eyebrow="Architecture"
                title="CAP v1.2 native"
                copy="All alerts are CAP XML compliant, NDMA Sachet-compatible, and consumable via REST or feed."
              />
            </div>
          </motion.div>
        </section>

        {/* ── Pipeline diagram ── */}
        <PipelineSection
          expandedStep={expandedPipelineStep}
          setExpandedStep={setExpandedPipelineStep}
        />

        {/* ── Live / Audit ── */}
        <AnimatePresence mode="wait">
          {mode === 'live' ? (
            <motion.section
              key="live"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.45 }}
              className="grid gap-6 pb-24 lg:grid-cols-[1.15fr_0.85fr]"
            >
              {/* Map */}
              <div className="glass-panel lime-outline overflow-hidden flex flex-col h-[700px]">
                <div className="flex items-center justify-between border-b border-white/6 px-6 py-4 bg-white/[0.02]">
                  <div>
                    <div className="text-tiny font-bold uppercase tracking-[0.24em] text-white/40">Live map</div>
                    <div className="mt-1 font-serif text-2xl">Risk field</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-slope-accent opacity-60" />
                      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-slope-accent" />
                    </span>
                    <span className="text-tiny font-bold uppercase tracking-[0.18em] text-white/50" title={`Data refreshed every 6 hours. Last model run: ${lastRun ? new Date(lastRun).toLocaleString() : 'Pending'}`}>Live telemetry</span>
                  </div>
                </div>
                <div className="flex-1 w-full scan-effect bg-black/60">
                  <RiskMap
                    alerts={alerts}
                    selectedAlert={selectedAlert}
                    onAlertClick={(alert: Alert) => setSelectedAlertId(alert.id)}
                  />
                </div>
              </div>

              {/* Feed + detail */}
              <div className="space-y-5">
                <Panel title="Active blocks" eyebrow="Live feed">
                  <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1 custom-scrollbar">
                    {loading ? (
                      <LoadingSkeleton rows={4} />
                    ) : alerts.length ? (
                      [...alerts]
                        .sort((a, b) => b.fpi_score - a.fpi_score)
                        .map((alert) => (
                          <AlertLine
                            key={alert.id}
                            alert={alert}
                            active={selectedAlert?.id === alert.id}
                            onClick={() => setSelectedAlertId(alert.id)}
                          />
                        ))
                    ) : (
                      <EmptyState text="No active alerts above the watch threshold." />
                    )}
                  </div>
                  <div className="mt-3 pt-3 border-t border-white/6 text-right">
                    <Link href="/districts" className="text-small font-bold uppercase tracking-wider text-slope-accent hover:text-white transition-colors">
                      View all active blocks →
                    </Link>
                  </div>
                </Panel>

                <Panel title="Selected block" eyebrow="Detail">
                  <AnimatePresence mode="wait">
                    {selectedAlert ? (
                      <motion.div
                        key={selectedAlert.id}
                        initial={{ opacity: 0, x: 12 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -12 }}
                        transition={{ duration: 0.3 }}
                        className="space-y-5"
                      >
                        <div className="flex items-start justify-between gap-4 border-b border-white/8 pb-4">
                          <div>
                            <div className="font-serif text-3xl font-bold leading-tight">{selectedAlert.block_name}</div>
                            <div className="mt-1.5 text-base-sm font-medium tracking-wide text-white/50">
                              {selectedAlert.district_name}, {selectedAlert.state_name}
                            </div>
                          </div>
                          <div className={`shrink-0 rounded-full border px-3 py-1 text-tiny font-bold uppercase tracking-[0.18em] ${tierBadgeClass(selectedAlert.tier)}`}>
                            {selectedAlert.tier}
                          </div>
                        </div>

                        {/* Human-readable risk banner */}
                        {(() => {
                          const rl = getRiskLevel(selectedAlert.fpi_score);
                          return (
                            <div
                              className="rounded-xl border p-4 space-y-1"
                              style={{ borderColor: `${rl.color}40`, backgroundColor: `${rl.color}0D` }}
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-lg">{rl.emoji}</span>
                                <span className="text-base font-bold" style={{ color: rl.color }}>{rl.short}</span>
                              </div>
                              <p className="text-base-sm leading-relaxed text-white/70">{selectedAlert.risk_description || rl.description}</p>
                              <p className="text-small font-semibold mt-2" style={{ color: rl.color }}>Action: {selectedAlert.risk_action || rl.action}</p>
                            </div>
                          );
                        })()}

                        <div className="grid gap-3 sm:grid-cols-2">
                          <MetricCardLight label="FPI Score"     value={formatFPI(selectedAlert.fpi_score)} highlight />
                          <MetricCardLight label="24h Forecast"  value={formatFPI(selectedAlert.fpi_24h)} />
                          <MetricCardLight label="95% CI range"  value={`${Math.round(selectedAlert.fpi_ci_lower * 100)}–${Math.round(selectedAlert.fpi_ci_upper * 100)}%`} />
                          <MetricCardLight label="Breach fraction" value={`${Math.round(selectedAlert.breach_fraction * 100)}%`} />
                        </div>
                        
                        <div className="mt-5 pt-5 border-t border-white/8">
                          <div className="text-tiny font-bold uppercase tracking-[0.2em] text-white/50 mb-4">Signal Breakdown</div>
                          <div className="space-y-3">
                            <div className="flex items-center gap-3">
                              <div className="w-24 text-small font-medium text-white/70">Rainfall 3D</div>
                              <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-blue-400" style={{ width: `${Math.min(100, (selectedAlert.rainfall_3d_mm || 0) / 3)}%` }} /></div>
                              <div className="w-12 text-right text-small font-mono">{Math.round(selectedAlert.rainfall_3d_mm || 0)}mm</div>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className="w-24 text-small font-medium text-white/70">Soil Moisture</div>
                              <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-amber-600" style={{ width: `${selectedAlert.soil_moisture_percentile || 0}%` }} /></div>
                              <div className="w-12 text-right text-small font-mono">{Math.round(selectedAlert.soil_moisture_percentile || 0)}%</div>
                            </div>
                            {selectedAlert.dominant_signals && selectedAlert.dominant_signals.length > 0 && (
                              <div className="mt-4 text-small font-medium text-white/60">
                                Dominant signal: <span className="text-slope-accent capitalize">{selectedAlert.dominant_signals[0].signal.replace(/_/g, ' ')}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    ) : (
                      <EmptyState text="Select a block from the map or the feed above." />
                    )}
                  </AnimatePresence>
                </Panel>
              </div>
            </motion.section>
          ) : (
            <motion.section
              key="audit"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.45 }}
              className="grid gap-6 pb-24 lg:grid-cols-[0.9fr_1.1fr]"
            >
              <Panel title="Retrospective audit" eyebrow="Evidence">
                {summary ? (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-5">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <MetricCardLight label="Total Events"  value={`${summary.total_events}`} />
                      <MetricCardLight label="Flagged T-24h" value={`${summary.flagged_at_t24}`} highlight />
                    </div>

                    <div className={`rounded-lg border px-4 py-3 text-base-sm font-bold flex items-center gap-2 ${summary.passed ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
                      <span className={`h-2 w-2 rounded-full ${summary.passed ? 'bg-emerald-400' : 'bg-red-400'}`} />
                      {summary.flagged_at_t24}/{summary.total_events} events flagged at T-24h
                    </div>

                    <div className="rounded-xl border border-slope-accent/15 bg-slope-accent/4 p-5 relative overflow-hidden">
                      <div className="text-tiny font-bold uppercase tracking-[0.22em] text-slope-accent mb-2 flex items-center gap-2">
                        <span className="w-1 h-3.5 rounded-full bg-slope-accent" />
                        Key finding
                      </div>
                      <p className="text-base-sm leading-relaxed text-white/80">
                        On July 29, 2024, SlopeSense reached{' '}
                        <strong className="text-slope-accent">73% FPI</strong> for Meppadi block and an{' '}
                        <strong className="text-slope-accent">81% 24h forecast</strong>.
                        The Wayanad disaster occurred at 2:17am on July 30. The warning arrived first.
                      </p>
                    </div>
                  </motion.div>
                ) : (
                  <EmptyState text="Loading retrospective results…" />
                )}
              </Panel>

              <Panel title="Event validation" eyebrow="Validation">
                {summary ? (
                  <div className="space-y-2">
                    {summary.results.map((result, i) => (
                      <motion.div
                        key={result.event_id}
                        initial={{ opacity: 0, x: 16 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.08 }}
                        className="rounded-xl border border-white/6 bg-white/3 p-4 hover:bg-white/6 transition-colors"
                      >
                        <div className="flex flex-col gap-3">
                          <div className="flex items-center justify-between gap-4">
                            <div>
                              <div className="font-serif text-xl font-medium">{result.event_name}</div>
                              <div className="text-tiny font-semibold uppercase tracking-[0.18em] text-white/40 mt-1">
                                {result.state} · {result.district}
                              </div>
                            </div>
                            <div className={`shrink-0 rounded-full border px-3 py-1 text-tiny font-bold uppercase tracking-[0.18em] ${
                              result.flagged_at_t24
                                ? 'border-emerald-500/30 bg-emerald-500/8 text-emerald-400'
                                : 'border-red-500/30 bg-red-500/10 text-red-400'
                            }`}>
                              {result.flagged_at_t24 ? 'Flagged' : 'Missed'}
                            </div>
                          </div>
                          {result.notes && (
                            <div className="text-small leading-relaxed text-white/60 bg-black/20 p-2 rounded border border-white/5">
                              {result.notes}
                            </div>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <EmptyState text="Waiting for summary data…" />
                )}
              </Panel>
            </motion.section>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}

// ── Pipeline section ──────────────────────────────────────────────────────────

function PipelineSection({
  expandedStep,
  setExpandedStep,
}: {
  expandedStep: number | null;
  setExpandedStep: (i: number | null) => void;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay: 0.3 }}
      className="mb-16 relative z-10"
    >
      {/* Section header */}
      <div className="mb-8 flex items-end justify-between">
        <div>
          <p className="text-tiny font-semibold uppercase tracking-[0.28em] text-slope-accent mb-2">
            How it works
          </p>
          <h2 className="font-serif text-3xl sm:text-4xl text-white">The signal pipeline</h2>
        </div>
        <p className="hidden text-base-sm text-white/35 max-w-xs text-right sm:block">
          Click any stage to see its role in the risk computation chain.
        </p>
      </div>

      {/* Pipeline nodes */}
      <div className="glass-panel p-6 sm:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:gap-0">
          {PIPELINE_STEPS.map((step, i) => (
            <div key={step.label} className="flex sm:flex-col sm:flex-1 items-center sm:items-stretch gap-0">
              {/* Node */}
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => setExpandedStep(expandedStep === i ? null : i)}
                className={`pipeline-node flex-1 sm:flex-none rounded-xl border p-4 text-left transition-all duration-300 cursor-pointer ${
                  expandedStep === i
                    ? 'border-white/20 bg-white/6'
                    : 'border-white/6 bg-white/2 hover:border-white/14 hover:bg-white/4'
                }`}
              >
                {/* Icon row */}
                <div className="flex sm:flex-col sm:items-center sm:text-center gap-3 sm:gap-2">
                  <div
                    className="pipeline-node-icon shrink-0"
                    style={{
                      borderColor: expandedStep === i ? step.color.replace('0.9', '0.4') : undefined,
                      boxShadow: expandedStep === i ? `0 0 16px ${step.glow}` : undefined,
                    }}
                  >
                    <span className="text-xl">{step.icon}</span>
                  </div>
                  <div className="sm:text-center">
                    <div className="text-base-sm font-bold text-white/90 tracking-tight">{step.label}</div>
                    <div className="text-tiny text-white/40 mt-0.5">{step.sublabel}</div>
                  </div>
                </div>

                {/* Step number */}
                <div
                  className="hidden sm:block text-center mt-3 text-micro font-bold uppercase tracking-[0.24em] text-white/40"
                >
                  Step {i + 1}
                </div>
              </motion.button>

              {/* Connector (between steps) */}
              {i < PIPELINE_STEPS.length - 1 && (
                <div className="pipeline-connector sm:justify-center sm:py-2 sm:px-0 px-2 py-0">
                  <div
                    className="hidden sm:block pipeline-connector-line bg-white/20"
                  />
                  <div className="sm:hidden w-px h-6 bg-gradient-to-b from-white/20 to-white/5 mx-auto" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Expanded detail */}
        <AnimatePresence>
          {expandedStep !== null && (
            <motion.div
              key={expandedStep}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.35, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <div
                className="mt-6 rounded-xl border p-5"
                style={{
                  borderColor: PIPELINE_STEPS[expandedStep].color.replace('0.9', '0.2'),
                  background: PIPELINE_STEPS[expandedStep].glow,
                }}
              >
                <div className="flex items-start gap-4">
                  <span className="text-3xl shrink-0">{PIPELINE_STEPS[expandedStep].icon}</span>
                  <div>
                    <div className="font-serif text-xl font-bold mb-1"
                      style={{ color: PIPELINE_STEPS[expandedStep].color }}>
                      {PIPELINE_STEPS[expandedStep].label}
                    </div>
                    <p className="text-base-sm leading-relaxed text-white/70">
                      {PIPELINE_STEPS[expandedStep].detail}
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}

// ── Top bar ───────────────────────────────────────────────────────────────────

function TopBar({
  mode,
  setMode,
  lastRun,
  stats,
  summary,
}: {
  mode: ViewMode;
  setMode: (m: ViewMode) => void;
  lastRun: string | null;
  stats: { total: number; emergency: number; warning: number; watch: number };
  summary: ReturnType<typeof useRetrospective>['summary'];
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/6 py-5">
      <div className="flex items-center gap-4">
        <div>
          <div className="font-serif text-2xl leading-none">SlopeSense</div>
          <div className="mt-1 text-micro uppercase tracking-[0.26em] text-white/35">
            Landslide risk intelligence · India
          </div>
        </div>
        <div className="hidden h-6 w-px bg-white/10 sm:block" />
        <div className="hidden items-center gap-3 text-tiny text-white/40 sm:flex">
          <span className="stat-chip">{stats.total} active</span>
          {summary && (
            <span className="stat-chip text-slope-accent border-slope-accent/20">
              {summary.flagged_at_t24}/{summary.total_events} audit
            </span>
          )}
          {lastRun && (
            <span className="stat-chip">{new Date(lastRun).toLocaleDateString('en-IN')}</span>
          )}
        </div>
      </div>

      {/* Mode toggle */}
      <div className="flex items-center rounded-xl border border-white/8 bg-white/3 p-1 gap-1">
        <ModeButton active={mode === 'live'}  onClick={() => setMode('live')}  label="Live"  />
        <ModeButton active={mode === 'audit'} onClick={() => setMode('audit')} label="Audit" />
      </div>
    </header>
  );
}

function ModeButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`relative rounded-lg px-5 py-2 text-tiny font-bold uppercase tracking-[0.2em] transition-all duration-200 ${
        active ? 'text-slope-bg' : 'text-white/50 hover:text-white'
      }`}
    >
      {active && (
        <motion.div
          layoutId="mode-active"
          className="absolute inset-0 rounded-lg bg-slope-accent shadow-glow-lime"
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        />
      )}
      <span className="relative z-10">{label}</span>
    </button>
  );
}

// ── Action button ─────────────────────────────────────────────────────────────

function ActionButton({
  label,
  variant,
  onClick,
}: {
  label: string;
  variant: 'primary' | 'secondary';
  onClick?: () => void;
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.02, y: -1 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`h-11 rounded-full px-6 text-tiny font-bold uppercase tracking-[0.2em] transition-all duration-200 ${
        variant === 'primary'
          ? 'bg-slope-accent text-slope-bg shadow-glow-lime hover:shadow-glow-lime-strong hover:bg-white'
          : 'border border-white/12 bg-white/4 text-white/70 hover:border-white/25 hover:bg-white/8 hover:text-white'
      }`}
    >
      {label}
    </motion.button>
  );
}

// ── Metric card ───────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  detail,
  delay = 0,
  accent = 'default',
}: {
  label: string;
  value: string;
  detail: string;
  delay?: number;
  accent?: 'default' | 'warning' | 'emergency' | 'ok';
}) {
  const accentColors: Record<string, string> = {
    default:   'border-white/7',
    warning:   'border-red-500/20',
    emergency: 'border-slope-accent/25',
    ok:        'border-emerald-500/20',
  };
  const leftBarColors: Record<string, string> = {
    default:   'bg-white/15',
    warning:   'bg-red-500',
    emergency: 'bg-slope-accent',
    ok:        'bg-emerald-400',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -3 }}
      className={`glass-panel p-5 relative overflow-hidden group border ${accentColors[accent]}`}
    >
      {/* Left accent bar */}
      <div className={`absolute left-0 top-4 bottom-4 w-0.5 rounded-full ${leftBarColors[accent]}`} />

      <div className="pl-3">
        <div className="text-tiny font-bold uppercase tracking-[0.2em] text-white/35">{label}</div>
        <div className="mt-2.5 font-serif text-4xl leading-none text-white">{value}</div>
        <div className="mt-2 text-base-sm text-white/40">{detail}</div>
      </div>
    </motion.div>
  );
}

// ── Feature card ──────────────────────────────────────────────────────────────

function FeatureCard({ eyebrow, title, copy }: { eyebrow: string; title: string; copy: string }) {
  return (
    <motion.div
      whileHover={{ scale: 1.01, y: -2 }}
      transition={{ duration: 0.2 }}
      className="glass-panel p-6 relative overflow-hidden group"
    >
      <div className="absolute top-0 right-0 w-28 h-28 rounded-full bg-slope-accent/4 blur-3xl group-hover:bg-slope-accent/8 transition-colors duration-700" />
      <div className="relative z-10">
        <div className="text-tiny font-bold uppercase tracking-[0.24em] text-slope-accent mb-3 flex items-center gap-2">
          <span className="w-1 h-1 rounded-full bg-slope-accent" />
          {eyebrow}
        </div>
        <div className="font-serif text-xl leading-tight mb-2 text-white">{title}</div>
        <p className="text-base-sm leading-relaxed text-white/50">{copy}</p>
      </div>
    </motion.div>
  );
}

// ── Signal card (top 3 in console) ───────────────────────────────────────────

function SignalCard({ alert, active, onClick }: { alert: Alert; active: boolean; onClick: () => void }) {
  const rl = getRiskLevel(alert.fpi_score);
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className={`relative rounded-xl border p-3.5 text-left transition-all duration-200 overflow-hidden ${
        active
          ? 'border-slope-accent/35 bg-slope-accent/5 shadow-glow-lime'
          : 'border-white/6 bg-white/3 hover:border-white/14'
      }`}
    >
      {active && <div className="absolute top-0 left-0 w-0.5 h-full rounded-r-sm" style={{ backgroundColor: rl.color }} />}
      <div className="pl-1">
        <div className="flex items-center gap-1.5 mb-1">
          <span className="text-sm">{rl.emoji}</span>
          <span className="text-micro font-bold uppercase tracking-[0.2em]" style={{ color: rl.color }}>{rl.label}</span>
        </div>
        <div className="font-serif text-lg leading-tight text-white/90 truncate">{alert.block_name}</div>
        <div className="text-tiny text-white/40 truncate mt-0.5">{alert.district_name}</div>
        <div className="mt-2.5 flex items-baseline gap-2">
          <span className="text-base font-bold" style={{ color: rl.color }}>{formatFPI(alert.fpi_score)}</span>
          <span className="text-tiny text-white/35">FPI</span>
        </div>
      </div>
    </motion.button>
  );
}

// ── Console stat ──────────────────────────────────────────────────────────────

function ConsoleStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/6 bg-white/3 px-4 py-3">
      <div className="text-micro font-bold uppercase tracking-[0.22em] text-white/35">{label}</div>
      <div className="mt-1.5 text-base-sm font-semibold text-white/80 truncate">{value}</div>
    </div>
  );
}

// ── Terminal line ─────────────────────────────────────────────────────────────

function TerminalLine({ cmd, active = false }: { cmd: string; active?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-white/25 select-none">$</span>
      <span className={`text-slope-accent/80 text-small tracking-wide ${active ? 'text-slope-accent' : ''}`}>
        {cmd}
      </span>
      {active && <span className="terminal-cursor" />}
    </div>
  );
}

// ── Panel ─────────────────────────────────────────────────────────────────────

function Panel({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) {
  return (
    <section className="glass-panel p-5 flex flex-col">
      <div className="mb-4 border-b border-white/6 pb-4">
        <div className="text-tiny font-bold uppercase tracking-[0.22em] text-white/40">{eyebrow}</div>
        <div className="mt-1.5 font-serif text-2xl text-white">{title}</div>
      </div>
      <div className="flex-1">{children}</div>
    </section>
  );
}

// ── Alert line ────────────────────────────────────────────────────────────────

function AlertLine({ alert, active, onClick }: { alert: Alert; active: boolean; onClick: () => void }) {
  const rl = getRiskLevel(alert.fpi_score);
  return (
    <motion.button
      whileHover={{ x: 3 }}
      onClick={onClick}
      className={`w-full rounded-xl border p-3.5 text-left transition-all duration-200 relative overflow-hidden ${
        active
          ? 'border-slope-accent/30 bg-slope-accent/6 shadow-glow-lime'
          : 'border-white/5 bg-white/3 hover:border-white/12 hover:bg-white/5'
      }`}
    >
      {active && <motion.div layoutId="alert-active" className="absolute left-0 top-0 bottom-0 w-0.5" style={{ backgroundColor: rl.color }} />}
      <div className="flex items-center justify-between gap-3 pl-1">
        <div className="min-w-0 flex-1">
          <div className="font-serif text-lg font-medium text-white/90 truncate">{alert.block_name}</div>
          <div className="mt-0.5 text-tiny font-semibold uppercase tracking-[0.14em] text-white/40 truncate">
            {alert.district_name} · {alert.state_name}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-lg font-bold" style={{ color: rl.color }}>
            {formatFPI(alert.fpi_score)}
          </div>
          <div className="mt-1 text-micro font-bold uppercase tracking-[0.1em]" style={{ color: rl.color }}>
            {rl.emoji} {rl.label}
          </div>
        </div>
      </div>
    </motion.button>
  );
}

// ── Metric card light ─────────────────────────────────────────────────────────

function MetricCardLight({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 transition-colors ${
      highlight
        ? 'border-slope-accent/25 bg-slope-accent/5'
        : 'border-white/6 bg-white/3 hover:bg-white/5'
    }`}>
      <div className={`text-micro font-bold uppercase tracking-[0.2em] ${highlight ? 'text-slope-accent' : 'text-white/40'}`}>
        {label}
      </div>
      <div className="mt-2 font-serif text-2xl font-medium text-white">{value}</div>
    </div>
  );
}

// ── Live badge ────────────────────────────────────────────────────────────────

function LiveBadge() {
  return (
    <div className="flex items-center gap-2 rounded-full border border-slope-accent/25 bg-slope-accent/6 px-3.5 py-1.5">
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full rounded-full bg-slope-accent opacity-75 animate-ping" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-slope-accent" />
      </span>
      <span className="text-micro font-bold uppercase tracking-[0.22em] text-slope-accent">Live</span>
    </div>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="rounded-xl border border-white/5 bg-white/3 p-3.5 animate-pulse">
          <div className="h-3 w-3/4 rounded bg-white/8 mb-2" />
          <div className="h-2.5 w-1/2 rounded bg-white/5" />
        </div>
      ))}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/10 bg-white/2 px-6 py-8 text-center text-base-sm font-medium text-white/35">
      {text}
    </div>
  );
}
