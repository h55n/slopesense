'use client';

import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
interface EndpointParam {
  name: string;
  type: string;
  desc: string;
}

interface Endpoint {
  id: string;
  method: string;
  path: string;
  auth: string;
  description: string;
  tryPath?: string;
  params?: EndpointParam[];
  example?: string;
}

interface EndpointGroup {
  group: string;
  endpoints: Endpoint[];
}

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen bg-slope-bg text-white">
      <header className="border-b border-white/10 px-6 py-5">
        <div className="mx-auto max-w-6xl">
          <nav className="mb-3 flex items-center gap-2 text-xs text-white/40">
            <Link href="/" className="hover:text-white transition-colors">SlopeSense</Link>
            <span>/</span>
            <span className="text-white">API Docs</span>
          </nav>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-12">
            <div>
              <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400 mb-4">
                SlopeSense API Documentation
              </h1>
              <p className="text-slate-400 text-lg max-w-3xl">
                Integrate real-time landslide risk intelligence, historical data, and CAP-compliant alerts into your own systems.
              </p>
            </div>
            <Link
              href="/developers"
              className="shrink-0 bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 px-6 rounded-lg shadow-lg hover:shadow-xl transition-all flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>
              Get API Key
            </Link>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex gap-3">
              <a
                href={`${API_BASE}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg border border-white/20 px-4 py-2 text-sm text-white/70 hover:text-white transition-colors"
              >
                Swagger UI ↗
              </a>
              <a
                href={`${API_BASE}/redoc`}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg border border-white/20 px-4 py-2 text-sm text-white/70 hover:text-white transition-colors"
              >
                ReDoc ↗
              </a>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
          {/* Sidebar */}
          <aside className="space-y-6">
            <div>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-white/30">Overview</h3>
              <div className="space-y-1 text-sm text-white/60">
                <div className="rounded-lg bg-white/5 px-3 py-2 text-white">Authentication</div>
                <div className="px-3 py-1.5 hover:text-white cursor-default">Rate Limits</div>
                <div className="px-3 py-1.5 hover:text-white cursor-default">Error Codes</div>
              </div>
            </div>
            <div>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-white/30">Endpoints</h3>
              <div className="space-y-1 text-sm text-white/60">
                {ENDPOINT_GROUPS.map(g => (
                  <div key={g.group}>
                    <div className="mb-1 mt-3 text-xs font-semibold uppercase tracking-wider text-white/30">{g.group}</div>
                    {g.endpoints.map(e => (
                      <a key={e.path} href={`#${e.id}`} className="flex items-center gap-2 px-3 py-1.5 hover:text-white transition-colors">
                        <MethodBadge method={e.method} />
                        <span className="font-mono text-xs truncate">{e.path}</span>
                      </a>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </aside>

          {/* Content */}
          <div className="space-y-12">
            {/* Auth section */}
            <section id="authentication">
              <h2 className="mb-4 text-xl font-bold">Authentication</h2>
              <div className="rounded-xl border border-white/10 bg-white/3 p-6 space-y-4">
                <p className="text-sm text-white/70">
                  Public endpoints are rate-limited to <strong className="text-white">100 requests/hour</strong> per IP.
                  Research and paid tiers require an <code className="text-lime-300">X-API-Key</code> header.
                </p>
                <div className="rounded-lg bg-black/50 p-4">
                  <code className="text-sm text-green-400">
                    curl -H &quot;X-API-Key: your_key&quot; https://api.slopesense.in/v1/alerts/active
                  </code>
                </div>
                <div className="grid gap-3 sm:grid-cols-3 text-sm">
                  {[
                    { tier: 'Public', limit: '100/hour', key: 'No key required' },
                    { tier: 'Research', limit: '1,000/hour', key: 'X-API-Key required' },
                    { tier: 'Paid', limit: '10,000/hour', key: 'X-API-Key required' },
                  ].map(t => (
                    <div key={t.tier} className="rounded-lg border border-white/10 p-3">
                      <div className="font-semibold">{t.tier}</div>
                      <div className="text-white/60 text-xs mt-1">{t.limit}</div>
                      <div className="text-white/40 text-xs">{t.key}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* Endpoints */}
            {ENDPOINT_GROUPS.map(group => (
              <section key={group.group}>
                <h2 className="mb-6 text-xl font-bold">{group.group}</h2>
                <div className="space-y-6">
                  {group.endpoints.map(ep => (
                    <div key={ep.id} id={ep.id} className="rounded-xl border border-white/10 bg-white/3 overflow-hidden">
                      <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
                        <MethodBadge method={ep.method} />
                        <code className="flex-1 font-mono text-sm text-white">{ep.path}</code>
                        <span className="text-xs text-white/30">{ep.auth}</span>
                      </div>
                      <div className="px-5 py-4">
                        <p className="mb-4 text-sm text-white/70">{ep.description}</p>
                        {ep.params && (
                          <div className="mb-4">
                            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/30">Parameters</div>
                            <div className="overflow-hidden rounded-lg border border-white/10">
                              <table className="w-full text-xs">
                                <thead className="bg-white/5">
                                  <tr>
                                    <th className="px-3 py-2 text-left text-white/40">Name</th>
                                    <th className="px-3 py-2 text-left text-white/40">Type</th>
                                    <th className="px-3 py-2 text-left text-white/40">Description</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                  {ep.params.map(p => (
                                    <tr key={p.name}>
                                      <td className="px-3 py-2 font-mono text-lime-300">{p.name}</td>
                                      <td className="px-3 py-2 text-white/50">{p.type}</td>
                                      <td className="px-3 py-2 text-white/60">{p.desc}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                        {ep.example && (
                          <div>
                            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/30">Example</div>
                            <div className="rounded-lg bg-black/50 p-3">
                              <code className="text-xs text-green-400 whitespace-pre">{ep.example}</code>
                            </div>
                          </div>
                        )}
                        <div className="mt-3">
                          <a
                            href={`${API_BASE}${ep.tryPath || ep.path}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-white/40 hover:text-white/70 transition-colors"
                          >
                            Try it live ↗
                          </a>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))}

            {/* Embedded Swagger */}
            <section id="swagger-ui">
              <h2 className="mb-4 text-xl font-bold">Interactive Swagger UI</h2>
              <div className="rounded-xl border border-white/10 overflow-hidden" style={{ height: '600px' }}>
                <iframe
                  src={`${API_BASE}/docs`}
                  className="w-full h-full"
                  title="SlopeSense Swagger UI"
                />
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: 'bg-emerald-500/20 text-emerald-300',
    POST: 'bg-blue-500/20 text-blue-300',
    WS: 'bg-purple-500/20 text-purple-300',
  };
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-bold font-mono ${colors[method] || 'bg-white/10 text-white/60'}`}>
      {method}
    </span>
  );
}

const ENDPOINT_GROUPS: EndpointGroup[] = [
  {
    group: 'FPI & Risk',
    endpoints: [
      {
        id: 'ep-health', method: 'GET', path: '/', auth: 'Public', tryPath: '/',
        description: 'Health check. Returns API status, version, last model run timestamp, and active alert count.',
        example: `curl ${API_BASE}/`,
      },
      {
        id: 'ep-risk', method: 'GET', path: '/v1/risk', auth: 'Public',
        description: 'Get FPI score for a specific lat/lon coordinate. Uses nearest 0.1° grid cell.',
        tryPath: '/v1/risk?lat=11.58&lon=76.08',
        params: [
          { name: 'lat', type: 'float', desc: 'Latitude (−90 to 90)' },
          { name: 'lon', type: 'float', desc: 'Longitude (−180 to 180)' },
          { name: 'hours_ahead', type: 'int', desc: 'Forecast horizon: 0, 24, or 48 hours' },
        ],
        example: `curl "${API_BASE}/v1/risk?lat=11.58&lon=76.08&hours_ahead=24"`,
      },
      {
        id: 'ep-districts', method: 'GET', path: '/v1/districts/{state_code}', auth: 'Public',
        description: 'All districts in a state with current FPI summary. Filter by min_fpi.',
        tryPath: '/v1/districts/KL',
        params: [
          { name: 'state_code', type: 'str', desc: 'Two-letter state code (e.g., KL, UK, SK)' },
          { name: 'min_fpi', type: 'float', desc: 'Minimum FPI score filter (0.0–1.0)' },
        ],
      },
    ],
  },
  {
    group: 'Alerts',
    endpoints: [
      {
        id: 'ep-active-alerts', method: 'GET', path: '/v1/alerts/active', auth: 'Public', tryPath: '/v1/alerts/active',
        description: 'Get all currently active alerts. Filter by tier, state, or minimum FPI score.',
        params: [
          { name: 'min_fpi', type: 'float', desc: 'Minimum FPI threshold' },
          { name: 'tier', type: 'str', desc: 'WATCH | WARNING | EMERGENCY' },
          { name: 'state', type: 'str', desc: 'Two-letter state code' },
        ],
      },
      {
        id: 'ep-alert-detail', method: 'GET', path: '/v1/alerts/{alert_id}', auth: 'Public',
        description: 'Full detail for a specific alert including signal breakdown.',
        tryPath: '/v1/alerts/demo-1',
      },
    ],
  },
  {
    group: 'GeoJSON & CAP',
    endpoints: [
      {
        id: 'ep-geojson', method: 'GET', path: '/v1/geojson/fpi', auth: 'Public', tryPath: '/v1/geojson/fpi',
        description: 'GeoJSON FeatureCollection of FPI scores for MapLibre heatmap rendering. Supports bbox viewport filtering.',
        params: [
          { name: 'state', type: 'str', desc: 'Filter by state code' },
          { name: 'min_fpi', type: 'float', desc: 'Minimum FPI' },
          { name: 'bbox', type: 'str', desc: 'minLon,minLat,maxLon,maxLat viewport filter' },
        ],
      },
      {
        id: 'ep-cap', method: 'GET', path: '/v1/cap/feed', auth: 'Public', tryPath: '/v1/cap/feed',
        description: 'CAP v1.2 XML alert feed. Compatible with NDMA Sachet app and all CAP consumers.',
        params: [
          { name: 'state', type: 'str', desc: 'Filter by state' },
          { name: 'min_fpi', type: 'float', desc: 'Default 0.65 (WARNING threshold)' },
        ],
        example: `curl "${API_BASE}/v1/cap/feed?state=KL&min_fpi=0.65"`,
      },
    ],
  },
  {
    group: 'Reports & Audit',
    endpoints: [
      {
        id: 'ep-pdf', method: 'GET', path: '/v1/districts/{district_code}/report.pdf', auth: 'Public',
        description: 'Official NDMA-style PDF report for a district. Includes FPI table, signal breakdown, and recommended actions.',
        tryPath: '/v1/districts/WYD/report.pdf',
      },
      {
        id: 'ep-historical', method: 'GET', path: '/v1/historical/{date}/{district_code}', auth: 'Public',
        description: 'Historical FPI time-series for a district on a given date. Supports GeoJSON output.',
        tryPath: '/v1/historical/2024-07-29/WYD',
        params: [
          { name: 'date', type: 'str', desc: 'YYYY-MM-DD' },
          { name: 'district_code', type: 'str', desc: 'District code (e.g., WYD)' },
          { name: 'format', type: 'str', desc: 'json | geojson' },
        ],
      },
      {
        id: 'ep-retrospective', method: 'GET', path: '/v1/retrospective', auth: 'Public', tryPath: '/v1/retrospective',
        description: 'Retrospective validation summary for all 6 historical India landslide events.',
      },
    ],
  },
  {
    group: 'Contacts & Webhooks',
    endpoints: [
      {
        id: 'ep-register', method: 'POST', path: '/v1/contacts/register', auth: 'API Key',
        description: 'Register for WhatsApp alert delivery. Supports DDMA officers, Aapda Mitra volunteers, and Gram Pradhans.',
        example: `curl -X POST ${API_BASE}/v1/contacts/register \\
  -H "Content-Type: application/json" \\
  -d '{"name":"Test","role":"district_collector","whatsapp_number":"+919876543210","state_code":"KL","language":"ml","min_tier":"WARNING"}'`,
      },
      {
        id: 'ep-webhook', method: 'POST', path: '/v1/webhooks/whatsapp', auth: 'Signed',
        description: 'WhatsApp webhook receiver. Handles delivery receipts and "NO EVENT" false alarm feedback from field officers.',
      },
      {
        id: 'ep-ws', method: 'WS', path: '/ws/live', auth: 'Public',
        description: 'WebSocket endpoint for live FPI updates on the dashboard. Sends init state on connect, then pushes on each model run.',
        example: `// JavaScript
const ws = new WebSocket("wss://api.slopesense.in/ws/live");
ws.onmessage = (e) => console.log(JSON.parse(e.data));`,
      },
    ],
  },
];
