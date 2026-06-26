'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Alert, tierColor } from '@/lib/api';

interface RiskMapProps {
  alerts: Alert[];
  selectedAlert: Alert | null;
  onAlertClick: (alert: Alert) => void;
}

const BLOCK_COORDS: Record<string, [number, number]> = {
  KL_WYD_MEP: [76.083, 11.583],
  KL_WYD_VYT: [76.01, 11.52],
  UK_CHA_TAP: [79.72, 30.47],
  UK_RUD_KED: [79.067, 30.735],
  SK_MAN_LAC: [88.53, 27.59],
  MH_PUN_AMB: [73.65, 19.05],
};

const INDIA_CENTER: [number, number] = [80.0, 22.0];
const INDIA_ZOOM = 4.5;

export default function RiskMap({ alerts, selectedAlert, onAlertClick }: RiskMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const instance = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: INDIA_CENTER,
      zoom: INDIA_ZOOM,
      minZoom: 3,
      maxZoom: 14,
      attributionControl: false,
    });

    instance.addControl(new maplibregl.NavigationControl(), 'top-right');
    instance.on('load', () => setMapReady(true));

    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!map.current || !mapReady) return;

    markers.current.forEach((marker) => marker.remove());
    markers.current = [];

    alerts.forEach((alert) => {
      const coords =
        BLOCK_COORDS[alert.block_code] || [80 + (Math.random() - 0.5) * 20, 22 + (Math.random() - 0.5) * 15];
      const color = tierColor(alert.tier);
      const size = alert.tier === 'EMERGENCY' ? 28 : alert.tier === 'WARNING' ? 22 : 18;
      const isSelected = selectedAlert?.id === alert.id;

      const el = document.createElement('div');
      el.style.cssText = `
        width: ${isSelected ? size + 6 : size}px;
        height: ${isSelected ? size + 6 : size}px;
        background: ${color};
        border: 2px solid ${isSelected ? '#c5ff4a' : '#ffffff'};
        border-radius: 9999px;
        cursor: pointer;
        box-shadow: 0 0 ${isSelected ? 18 : 8}px ${color}66;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 700;
        color: #ffffff;
      `;
      el.textContent = `${Math.round(alert.fpi_score * 100)}`;
      if (alert.tier === 'EMERGENCY') {
        el.style.animation = 'pulse-red 1.5s ease-in-out infinite';
      }
      el.addEventListener('click', () => onAlertClick(alert));

      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        className: 'slope-popup',
        offset: 15,
      }).setHTML(`
        <div style="background:#ffffff;border:1px solid #d1d5db;border-radius:0;padding:10px;min-width:160px;color:#000000;">
          <div style="font-size:11px;color:#6b7280;margin-bottom:2px;letter-spacing:0.18em;text-transform:uppercase;">${alert.state_name}</div>
          <div style="font-weight:700;font-size:13px;font-family:Georgia,serif;">${alert.district_name}</div>
          <div style="font-size:12px;color:#111827;">${alert.block_name}</div>
          <div style="display:flex;align-items:center;gap:6px;margin-top:8px;">
            <span style="background:${color};color:#fff;padding:1px 6px;border-radius:0;font-size:10px;font-weight:700;text-transform:uppercase;">${alert.tier}</span>
            <span style="font-size:13px;font-weight:700;">${Math.round(alert.fpi_score * 100)}%</span>
          </div>
          <div style="font-size:11px;color:#6b7280;margin-top:4px;">24h forecast: ${Math.round(alert.fpi_24h * 100)}%</div>
        </div>
      `);

      el.addEventListener('mouseenter', () => popup.addTo(map.current!));
      el.addEventListener('mouseleave', () => popup.remove());

      markers.current.push(new maplibregl.Marker({ element: el }).setLngLat(coords).addTo(map.current!));
    });
  }, [alerts, selectedAlert, mapReady, onAlertClick]);

  useEffect(() => {
    if (!map.current || !mapReady || !selectedAlert) return;
    const coords = BLOCK_COORDS[selectedAlert.block_code];
    if (coords) {
      map.current.flyTo({
        center: coords,
        zoom: Math.max(map.current.getZoom(), 9),
        duration: 800,
        essential: true,
      });
    }
  }, [selectedAlert, mapReady]);

  return (
    <div className="relative h-[600px] w-full lg:h-full lg:min-h-[500px]">
      <div ref={mapContainer} className="absolute inset-0" />

      <div className="absolute bottom-6 left-4 z-10 rounded-none border border-black/10 bg-white/95 p-3 text-xs text-black">
        <div className="mb-2 font-semibold uppercase tracking-[0.2em] text-black/45">Failure Probability Index</div>
        <div className="space-y-1.5">
          {[
            { color: '#111111', label: 'EMERGENCY >80%' },
            { color: '#ef4444', label: 'WARNING 65-80%' },
            { color: '#f59e0b', label: 'WATCH 40-65%' },
            { color: '#10b981', label: 'NORMAL <40%' },
          ].map(({ color, label }) => (
            <div key={label} className="flex items-center gap-2">
              <div className="h-3 w-3 flex-shrink-0 rounded-full" style={{ background: color }} />
              <span className="text-black/75">{label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="absolute left-3 top-3 z-10 rounded-none border border-black/10 bg-white/90 px-2 py-1 text-xs font-medium text-black/60 backdrop-blur">
        NASA GPM · SMAP · NOAA GFS · Copernicus DEM
      </div>

      <button
        onClick={() => map.current?.flyTo({ center: INDIA_CENTER, zoom: INDIA_ZOOM })}
        className="absolute right-3 top-12 z-10 mt-20 rounded-none border border-black/10 bg-white px-2 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-black/70 transition-colors hover:border-lime-400 hover:bg-lime-300 hover:text-black"
      >
        India ↺
      </button>
    </div>
  );
}
