'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Map, { Marker, Popup, NavigationControl, MapRef } from 'react-map-gl/maplibre';
import type { StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Alert, tierColor, SourceObservation, ageLabel } from '@/lib/api';

interface RiskMapProps {
  alerts: Alert[];
  selectedAlert: Alert | null;
  onAlertClick: (alert: Alert) => void;
  /** True when the live API is unreachable and the alerts shown are sample data. */
  isSample?: boolean;
  /** Fly to the selected alert only after the visitor has chosen one. */
  userSelected?: boolean;
  /** Real provider snapshots shown as separate markers (not risk scores). */
  observations?: SourceObservation[];
  selectedObsCode?: string | null;
  onObsClick?: (o: SourceObservation) => void;
}

const BLOCK_COORDS: Record<string, [number, number]> = {
  KL_WYD_MEP: [76.083, 11.583],
  KL_WYD_VYT: [76.01, 11.52],
  UK_CHA_TAP: [79.72, 30.47],
  UK_RUD_KED: [79.067, 30.735],
  SK_MAN_LAC: [88.53, 27.59],
  MH_PUN_AMB: [73.65, 19.05],
};

const INDIA_CENTER: [number, number] = [80.5, 22.5];
const POSITRON = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

function coordsFor(a: Alert): [number, number] | null {
  if (a.lat && a.lon) return [a.lon, a.lat];
  return BLOCK_COORDS[a.block_code] ?? null;
}

/**
 * CARTO Positron restyled to the site palette (paper land, sage vegetation,
 * pale-blue water) with real SRTM-derived hillshade from the open Terrarium
 * elevation tiles, so the relief that drives landslide risk is visible.
 */
function paperStyle(base: any): StyleSpecification {
  const s = JSON.parse(JSON.stringify(base));
  s.sources['terrain-dem'] = {
    type: 'raster-dem',
    encoding: 'terrarium',
    tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
    tileSize: 256,
    maxzoom: 13,
    attribution: 'Terrain: Mapzen / SRTM',
  };
  const layers: any[] = [];
  for (const l of s.layers) {
    const id: string = l.id;
    l.paint = l.paint || {};
    if (l.type === 'background') l.paint['background-color'] = '#f0ebdc';
    if (['landcover', 'park_national_park', 'park_nature_reserve', 'landuse'].includes(id)) {
      l.paint['fill-color'] = 'rgba(150, 182, 146, 0.42)';
    }
    if (id === 'landuse_residential') l.paint['fill-color'] = 'rgba(214, 205, 180, 0.4)';
    if (id === 'water') l.paint['fill-color'] = '#cddfe2';
    if (id === 'waterway') l.paint['line-color'] = '#b9d0d5';
    if (id === 'boundary_state' || id === 'boundary_county') {
      l.paint['line-color'] = 'rgba(47, 74, 55, 0.35)';
    }
    if (id.startsWith('boundary_country')) {
      if (id === 'boundary_country_outline') l.paint['line-color'] = 'rgba(244,241,232,0.6)';
      else l.paint['line-color'] = 'rgba(47, 74, 55, 0.6)';
    }
    if (l.type === 'symbol') {
      l.paint['text-color'] = id.startsWith('watername') || id === 'waterway_label' ? '#6f95a0' : '#3d4a40';
      l.paint['text-halo-color'] = 'rgba(244,241,232,0.9)';
      l.paint['text-halo-width'] = 1.4;
      if (id === 'place_state') {
        l.paint['text-color'] = '#6f7a71';
        l.paint['text-halo-width'] = 1.2;
      }
    }
    layers.push(l);
    if (id === 'landuse') {
      layers.push({
        id: 'hillshade',
        type: 'hillshade',
        source: 'terrain-dem',
        paint: {
          'hillshade-exaggeration': 0.55,
          'hillshade-shadow-color': 'rgba(38, 62, 46, 0.55)',
          'hillshade-highlight-color': 'rgba(255, 250, 232, 0.9)',
          'hillshade-accent-color': 'rgba(47, 74, 55, 0.25)',
        },
      });
    }
  }
  s.layers = layers;
  return s as StyleSpecification;
}

const LEGEND = [
  { tier: 'EMERGENCY', label: 'Emergency', range: '>80%' },
  { tier: 'WARNING', label: 'Warning', range: '65-80%' },
  { tier: 'WATCH', label: 'Watch', range: '40-65%' },
  { tier: 'NORMAL', label: 'Normal', range: '<40%' },
];

export default function RiskMap({ alerts, selectedAlert, onAlertClick, isSample, userSelected, observations = [], selectedObsCode = null, onObsClick }: RiskMapProps) {
  const mapRef = useRef<MapRef>(null);
  const [style, setStyle] = useState<StyleSpecification | string>(POSITRON);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(POSITRON)
      .then((r) => r.json())
      .then((j) => !cancelled && setStyle(paperStyle(j)))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const [zoom, setZoom] = useState(4);
  const [keyOpen, setKeyOpen] = useState(false);

  const bounds = useMemo(() => {
    const pts = [
      ...(alerts.map(coordsFor).filter(Boolean) as [number, number][]),
      ...observations.map((o) => [o.longitude, o.latitude] as [number, number]),
    ];
    if (!pts.length) return null;
    const lons = pts.map((p) => p[0]);
    const lats = pts.map((p) => p[1]);
    return [
      [Math.min(...lons), Math.min(...lats)],
      [Math.max(...lons), Math.max(...lats)],
    ] as [[number, number], [number, number]];
  }, [alerts, observations]);

  const fitAll = () => {
    const map = mapRef.current?.getMap();
    if (!map) return;
    map.resize();
    const narrow = map.getContainer().clientWidth < 600;
    const padding = narrow ? { top: 90, bottom: 150, left: 40, right: 40 } : { top: 80, bottom: 120, left: 70, right: 70 };
    if (bounds) map.fitBounds(bounds, { padding, maxZoom: 6, minZoom: 2, duration: 0, pitch: 0, bearing: 0 });
    else map.easeTo({ center: INDIA_CENTER, zoom: 4, duration: 900 });
  };

  useEffect(() => {
    if (ready) fitAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, bounds?.[0]?.[0], bounds?.[0]?.[1], bounds?.[1]?.[0], bounds?.[1]?.[1]]);

  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(() => { if (!userSelected) fitAll(); }, 400);
    const onResize = () => { if (!userSelected) fitAll(); };
    window.addEventListener('resize', onResize);
    return () => { clearTimeout(t); window.removeEventListener('resize', onResize); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, bounds?.[0]?.[0], bounds?.[1]?.[1]]);

  useEffect(() => {
    if (!ready || !selectedAlert || !userSelected) return;
    const c = coordsFor(selectedAlert);
    if (c) mapRef.current?.getMap().flyTo({ center: c, zoom: 8.2, duration: 1100, essential: true });
  }, [selectedAlert?.id, ready]); // eslint-disable-line react-hooks/exhaustive-deps

  const sel = selectedAlert ? coordsFor(selectedAlert) : null;

  return (
    <div className="relative h-full min-h-[460px] w-full">
      <Map
        ref={mapRef}
        initialViewState={{ longitude: INDIA_CENTER[0], latitude: INDIA_CENTER[1], zoom: 3.8 }}
        mapStyle={style as any}
        attributionControl={true}
        onLoad={() => setReady(true)}
        onZoom={(e) => setZoom(e.viewState.zoom)}
        minZoom={2}
        maxPitch={0}
        dragRotate={false}
        touchPitch={false}
        cooperativeGestures={false}
      >
        <NavigationControl position="top-right" showCompass={false} />

        {observations.map((o) => {
          const sel = selectedObsCode === o.point_code;
          const rain = o.modeled_large_scale_rain_previous_72h_mm;
          return (
            <Marker
              key={o.point_code}
              longitude={o.longitude}
              latitude={o.latitude}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                onObsClick?.(o);
                const m = mapRef.current?.getMap();
                if (m) m.flyTo({ center: [o.longitude, o.latitude], zoom: Math.max(m.getZoom(), 6.5), duration: 700, essential: true });
              }}
              style={{ cursor: 'pointer', zIndex: sel ? 10 : 1 }}
            >
              <div role="button" aria-label={`${o.point_name}, provider weather values fetched ${ageLabel(o.fetched_at)}`} className="flex flex-col items-center">
                <span
                  className={`flex items-center justify-center rounded-full font-semibold tabular-nums ${zoom < 5.5 && !sel ? 'h-6 min-w-[24px] px-1 text-[10px]' : 'h-8 min-w-[32px] px-2 text-[11px]'}`}
                  style={{
                    background: o.stale ? '#e8e2cf' : '#fbf9f3',
                    color: '#1d2a21',
                    border: `${sel ? 3 : 2}px solid ${o.stale ? '#b8730f' : '#3b7aa3'}`,
                    boxShadow: sel ? '0 0 0 2px #3b7aa3, 0 6px 16px rgba(29,42,33,0.3)' : '0 3px 10px rgba(29,42,33,0.28)',
                  }}
                >
                  {rain == null ? 'n/a' : `${rain.toFixed(1)}`}
                </span>
                {(zoom >= 5.5 || sel) && <span className="mt-0.5 rounded bg-paper-card/90 px-1 text-[10px] font-medium text-ink/70">{o.point_code}</span>}
              </div>
            </Marker>
          );
        })}

        {alerts.map((alert) => {
          const coords = coordsFor(alert);
          if (!coords) return null;
          const color = tierColor(alert.tier);
          const hot = alert.tier === 'EMERGENCY' || alert.tier === 'WARNING';
          const isSelected = selectedAlert?.id === alert.id;
          const size = isSelected ? 38 : hot ? 32 : 28;
          return (
            <Marker
              key={alert.id}
              longitude={coords[0]}
              latitude={coords[1]}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                onAlertClick(alert);
              }}
              style={{ cursor: 'pointer', zIndex: isSelected ? 10 : 1 }}
            >
              <div className="relative" style={{ width: size, height: size }} role="button" aria-label={`${alert.block_name}, ${alert.tier}, FPI ${Math.round(alert.fpi_score * 100)}%`}>
                {hot && (
                  <span
                    className="absolute inset-0 rounded-full"
                    style={{ background: color, animation: 'pulse-ring 2.4s ease-out infinite' }}
                  />
                )}
                <span
                  className="relative flex h-full w-full items-center justify-center rounded-full text-[11px] font-semibold text-white"
                  style={{
                    background: color,
                    color: '#fff',
                    border: `${isSelected ? 3 : 2}px solid #fbf9f3`,
                    boxShadow: isSelected ? `0 0 0 2px ${color}, 0 6px 16px rgba(29,42,33,0.3)` : '0 3px 10px rgba(29,42,33,0.28)',
                    transition: 'all .2s ease',
                  }}
                >
                  {Math.round(alert.fpi_score * 100)}
                </span>
              </div>
            </Marker>
          );
        })}

        {selectedAlert && sel && (
          <Popup longitude={sel[0]} latitude={sel[1]} closeButton={false} closeOnClick={false} offset={26} maxWidth="240px">
            <div style={{ minWidth: 170 }}>
              <div className="eyebrow">{selectedAlert.state_name}</div>
              <div className="mt-0.5 font-serif text-[20px] leading-tight text-ink">{selectedAlert.block_name}</div>
              <div className="text-[12px] text-ink/60">{selectedAlert.district_name} district</div>
              <div className="mt-2 flex items-center gap-2 text-[12px] font-medium" style={{ color: tierColor(selectedAlert.tier) }}>
                <span className="h-2 w-2 rounded-full" style={{ background: tierColor(selectedAlert.tier) }} />
                {selectedAlert.tier.charAt(0) + selectedAlert.tier.slice(1).toLowerCase()} · FPI {Math.round(selectedAlert.fpi_score * 100)}%
              </div>
            </div>
          </Popup>
        )}
      </Map>

      {/* legend */}
      {observations.length > 0 && alerts.length === 0 ? (
        <div className={`${keyOpen ? 'block' : 'hidden'} absolute bottom-[72px] left-3 z-20 max-w-[260px] rounded-2xl border border-ink/10 bg-paper-card/95 px-4 py-3 shadow-glass backdrop-blur`}>
          <button onClick={() => setKeyOpen(false)} aria-label="Close key" className="absolute right-2 top-1 text-ink/50">&times;</button>
          <div className="eyebrow mb-1.5">Provider weather values</div>
          <p className="text-[12px] leading-snug text-ink/70">Marker number: modeled large-scale rain over the previous 72 h (mm). Amber outline means the snapshot is more than 3 h old. These are not risk scores or warnings.</p>
        </div>
      ) : null}
      <div className={`hidden ${alerts.length ? 'sm:block' : ''} absolute bottom-[72px] left-3 z-10 rounded-2xl border border-ink/10 bg-paper-card/95 px-4 py-3 shadow-glass backdrop-blur`}>
        <div className="eyebrow mb-2">Model FPI score</div>
        <ul className="space-y-1.5">
          {LEGEND.map(({ tier, label, range }) => (
            <li key={tier} className="flex items-center gap-2.5 text-[12px] text-ink/80">
              <span className="h-2.5 w-2.5 flex-shrink-0 rounded-full" style={{ background: tierColor(tier) }} />
              <span className="w-[68px]">{label}</span>
              <span className="tabular-nums text-ink/50">{range}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* source chip */}
      <div className="absolute left-3 top-3 z-10 flex max-w-[calc(100%-70px)] flex-wrap gap-2">
        <span className="hidden sm:inline-block rounded-full border border-ink/10 bg-paper-card/95 px-3 py-1.5 text-[11px] font-medium text-ink/70 shadow-glass backdrop-blur">
          {observations.length ? 'Open-Meteo weather model values · not warnings' : 'No validated risk scores'}
        </span>
        {isSample && alerts.length > 0 && (
          <span className="rounded-full border border-saffron-deep/30 bg-saffron-soft px-3 py-1.5 text-[11px] font-medium text-saffron-deep shadow-glass">
            Sample data · no live model run yet
          </span>
        )}
      </div>

      <div className="absolute bottom-8 left-3 z-10 flex gap-2">
        <button
          onClick={fitAll}
          className="focus-ring rounded-xl border border-ink/10 bg-paper-card px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink/70 shadow-glass transition-colors hover:text-ink"
        >
          Reset view
        </button>
        {observations.length > 0 && alerts.length === 0 ? (
          <button
            onClick={() => setKeyOpen((v) => !v)}
            className="focus-ring rounded-xl border border-ink/10 bg-paper-card px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink/70 shadow-glass transition-colors hover:text-ink"
          >
            Key
          </button>
        ) : null}
      </div>
    </div>
  );
}
