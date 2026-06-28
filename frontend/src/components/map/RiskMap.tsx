'use client';

import { useState } from 'react';
import Map, { Marker, Popup, NavigationControl } from 'react-map-gl/maplibre';
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
  const [viewState, setViewState] = useState({
    longitude: INDIA_CENTER[0],
    latitude: INDIA_CENTER[1],
    zoom: INDIA_ZOOM,
    pitch: 55,
    bearing: -15
  });

  const handleAlertClick = (e: any, alert: Alert, coords: [number, number]) => {
    e.originalEvent.stopPropagation();
    onAlertClick(alert);
    setViewState((prev) => ({
      ...prev,
      longitude: coords[0],
      latitude: coords[1],
      zoom: 10,
      pitch: 65,
      bearing: (Math.random() - 0.5) * 60
    }));
  };

  return (
    <div className="relative h-[600px] w-full lg:h-full lg:min-h-[500px]">
      <Map
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        attributionControl={false}
      >
        <NavigationControl position="top-right" />
        
        {alerts.map((alert) => {
          const coords = (alert.lat && alert.lon) 
            ? [alert.lon, alert.lat] as [number, number]
            : (BLOCK_COORDS[alert.block_code] || [80 + (Math.random() - 0.5) * 20, 22 + (Math.random() - 0.5) * 15]);
          const color = tierColor(alert.tier);
          const size = alert.tier === 'EMERGENCY' ? 28 : alert.tier === 'WARNING' ? 22 : 18;
          const isSelected = selectedAlert?.id === alert.id;

          return (
            <Marker 
              key={alert.id}
              longitude={coords[0]} 
              latitude={coords[1]}
              anchor="center"
              onClick={(e) => handleAlertClick(e, alert, coords)}
              style={{ cursor: 'pointer', zIndex: isSelected ? 10 : 1 }}
            >
              <div 
                style={{
                  width: isSelected ? size + 6 : size,
                  height: isSelected ? size + 6 : size,
                  background: color,
                  border: `2px solid ${isSelected ? '#c5ff4a' : '#ffffff'}`,
                  borderRadius: '9999px',
                  boxShadow: `0 0 ${isSelected ? 18 : 8}px ${color}66`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '10px',
                  fontWeight: 700,
                  color: '#ffffff',
                  animation: alert.tier === 'EMERGENCY' ? 'pulse-red 1.5s ease-in-out infinite' : 'none'
                }}
              >
                {Math.round(alert.fpi_score * 100)}
              </div>
            </Marker>
          );
        })}

        {selectedAlert && (selectedAlert.lat || BLOCK_COORDS[selectedAlert.block_code]) && (
          <Popup
            longitude={selectedAlert.lon || BLOCK_COORDS[selectedAlert.block_code][0]}
            latitude={selectedAlert.lat || BLOCK_COORDS[selectedAlert.block_code][1]}
            closeButton={false}
            closeOnClick={false}
            offset={15}
            className="slope-popup"
          >
            <div style={{ background: '#ffffff', border: '1px solid #d1d5db', borderRadius: 0, padding: '10px', minWidth: '160px', color: '#000000' }}>
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '2px', letterSpacing: '0.18em', textTransform: 'uppercase' }}>{selectedAlert.state_name}</div>
              <div style={{ fontWeight: 700, fontSize: '13px', fontFamily: 'Georgia,serif' }}>{selectedAlert.district_name}</div>
              <div style={{ fontSize: '12px', color: '#111827' }}>{selectedAlert.block_name}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '8px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '4px', background: tierColor(selectedAlert.tier) }}></div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: tierColor(selectedAlert.tier) }}>{selectedAlert.tier}</div>
              </div>
            </div>
          </Popup>
        )}
      </Map>

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
        onClick={() => setViewState({ longitude: INDIA_CENTER[0], latitude: INDIA_CENTER[1], zoom: INDIA_ZOOM, pitch: 55, bearing: -15 })}
        className="absolute right-3 top-12 z-10 mt-20 rounded-none border border-black/10 bg-white px-2 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-black/70 transition-colors hover:border-lime-400 hover:bg-lime-300 hover:text-black"
      >
        India ↺
      </button>
    </div>
  );
}
