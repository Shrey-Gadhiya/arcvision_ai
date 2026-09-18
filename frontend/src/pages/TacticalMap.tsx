import React, { useState, useEffect } from 'react';
import { Video, AlertTriangle, Compass, Radio, Crosshair, MapPin, Share2, RefreshCw, Wifi } from 'lucide-react';
import { Camera, Incident, TacticalMapLayer } from '../types';
import { apiClient } from '../api/client';

interface TacticalMapProps {
  cameras: Camera[];
  incidents: Incident[];
  onSelectCamera: (camId: number) => void;
  onSelectIncident: (inc: Incident) => void;
}

export const TacticalMap: React.FC<TacticalMapProps> = ({
  cameras,
  incidents,
  onSelectCamera,
  onSelectIncident
}) => {
  const [selectedCam, setSelectedCam] = useState<Camera | null>(cameras[0] || null);
  const [tacticalData, setTacticalData] = useState<TacticalMapLayer | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchTacticalLayer = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/map/tactical-layer');
      setTacticalData(res.data);
    } catch (e) {
      // use local data as fallback
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchTacticalLayer();
    const interval = setInterval(fetchTacticalLayer, 15000);
    return () => clearInterval(interval);
  }, []);

  const displayCameras = tacticalData?.cameras || cameras.map((c, i) => ({
    id: c.id,
    name: c.name,
    latitude: c.latitude,
    longitude: c.longitude,
    altitude_m: c.altitude_m || 120,
    heading_deg: c.heading_deg,
    fov_angle: c.fov_angle,
    range_meters: c.range_meters || 150,
    status: c.status,
    location: c.location,
    group_name: c.group_name,
    ptz_enabled: c.ptz_enabled || false,
    is_night_mode: false
  }));

  const displayIncidents = tacticalData?.active_incidents || incidents.filter(i => i.status !== 'RESOLVED').map(i => ({
    id: i.id,
    code: i.incident_code,
    title: i.title,
    severity: i.severity,
    status: i.status,
    threat_score: i.threat_score,
    camera_id: i.camera_id,
    location_name: i.location_name,
    latitude: 26.85 + Math.random() * 0.005,
    longitude: 85.20 + Math.random() * 0.005,
    detected_at: i.detected_at
  }));

  const topologyLinks = tacticalData?.topology_links || [];
  const globalTracks = tacticalData?.global_tracks || [];

  const severityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return 'border-white shadow-[0_0_12px_rgba(255,255,255,0.6)]';
      case 'HIGH': return 'border-zinc-300 shadow-[0_0_8px_rgba(255,255,255,0.3)]';
      case 'MEDIUM': return 'border-zinc-500';
      default: return 'border-zinc-600';
    }
  };

  const selectedCamDetail = selectedCam ?
    displayCameras.find((c: any) => c.id === selectedCam.id) || displayCameras[0]
    : null;

  return (
    <div className="p-4 space-y-4 font-mono">
      <div className="p-3 rounded bg-zinc-950 border border-zinc-800 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <MapPin className="w-4 h-4" />
            TACTICAL GEOSPATIAL MAP & SENSOR CONES (GIS)
          </h2>
          <p className="text-xs text-zinc-400">
            {tacticalData?.sector_name || 'Border fence layout, sensor coverage cones, and real-time incident geo-markers'}
          </p>
        </div>
        <div className="flex items-center space-x-3 text-xs">
          <button
            onClick={fetchTacticalLayer}
            className="flex items-center gap-1 text-zinc-400 hover:text-white transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>SYNC</span>
          </button>
          <div className="flex items-center space-x-1 text-white">
            <Radio className="w-4 h-4 animate-pulse" />
            <span>GPS RTK LOCK</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left 8 Cols: Tactical GIS Map Canvas */}
        <div className="lg:col-span-8 p-3 rounded bg-zinc-950 border border-zinc-800 space-y-2">
          <div className="relative aspect-[16/10] bg-black rounded overflow-hidden border border-zinc-800 tactical-grid flex items-center justify-center select-none">
            {/* Compass rose */}
            <div className="absolute top-4 right-4 text-zinc-600 flex flex-col items-center z-10">
              <Compass className="w-8 h-8 text-zinc-400" />
              <span className="text-[10px] font-bold text-zinc-400">N</span>
            </div>

            {/* Stats overlay */}
            <div className="absolute top-4 left-4 z-10 space-y-1.5">
              <div className="px-2 py-1 rounded bg-black/80 border border-zinc-800 text-[10px] text-zinc-300 font-mono">
                SENSORS: {displayCameras.length} • ACTIVE THREATS: {displayIncidents.length}
              </div>
              {globalTracks.length > 0 && (
                <div className="px-2 py-1 rounded bg-black/80 border border-zinc-800 text-[10px] text-zinc-300 font-mono">
                  GLOBAL TRACKS: {globalTracks.length}
                </div>
              )}
            </div>

            {/* Simulated Boundary Lines */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              <path
                d="M 50 350 Q 300 320 600 380 T 1100 330"
                fill="none"
                stroke="#ffffff"
                strokeWidth="1.5"
                strokeDasharray="6 4"
              />
              <text x="70" y="340" fill="#ffffff" fontSize="10" fontFamily="monospace">
                INTERNATIONAL BORDER ZERO LINE
              </text>

              <path
                d="M 50 420 Q 300 390 600 450 T 1100 400"
                fill="none"
                stroke="rgba(255, 255, 255, 0.4)"
                strokeWidth="1"
                strokeDasharray="3 3"
              />
              <text x="70" y="440" fill="rgba(255, 255, 255, 0.5)" fontSize="9" fontFamily="monospace">
                SECURITY BUFFER ZONE (150M)
              </text>

              {/* Topology links between cameras */}
              {topologyLinks.map((link: any, lIdx: number) => {
                const srcCam = displayCameras.find((c: any) => c.id === link.camera_a_id);
                const dstCam = displayCameras.find((c: any) => c.id === link.camera_b_id);
                if (!srcCam || !dstCam) return null;
                const srcIdx = displayCameras.indexOf(srcCam);
                const dstIdx = displayCameras.indexOf(dstCam);
                const sx = 20 + (srcIdx * 22);
                const sy = 40 + (srcIdx % 2 === 0 ? 15 : -10);
                const dx = 20 + (dstIdx * 22);
                const dy = 40 + (dstIdx % 2 === 0 ? 15 : -10);
                return (
                  <line
                    key={`topo-${lIdx}`}
                    x1={`${sx}%`} y1={`${sy}%`}
                    x2={`${dx}%`} y2={`${dy}%`}
                    stroke="rgba(255, 255, 255, 0.15)"
                    strokeWidth="1"
                    strokeDasharray="2 3"
                  />
                );
              })}
            </svg>

            {/* Render Camera Sensor Nodes with FOV Cones */}
            {displayCameras.map((cam: any, idx: number) => {
              const leftPct = 20 + (idx * 22);
              const topPct = 40 + (idx % 2 === 0 ? 15 : -10);
              const isSelected = selectedCam?.id === cam.id;
              const isPtz = cam.ptz_enabled;
              const isOnline = cam.status === 'ONLINE';

              return (
                <div
                  key={cam.id}
                  style={{ left: `${leftPct}%`, top: `${topPct}%` }}
                  onClick={() => {
                    const matchCam = cameras.find(c => c.id === cam.id);
                    if (matchCam) setSelectedCam(matchCam);
                  }}
                  className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                >
                  {/* FOV Cone SVG */}
                  <svg
                    className="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                    style={{
                      width: '180px',
                      height: '180px',
                      transform: `rotate(${cam.heading_deg || 0}deg)`
                    }}
                  >
                    <path
                      d="M 90 90 L 40 10 A 100 100 0 0 1 140 10 Z"
                      fill={isSelected ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.08)'}
                      stroke={isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.3)'}
                      strokeWidth="1"
                    />
                  </svg>

                  {/* Camera Pin */}
                  <div className={`relative w-7 h-7 rounded-full border-2 flex items-center justify-center transition-all ${
                    isSelected
                      ? 'bg-white text-black border-white shadow-[0_0_10px_#fff]'
                      : isOnline
                        ? 'bg-zinc-900 text-white border-zinc-600 hover:scale-110'
                        : 'bg-zinc-900 text-zinc-600 border-zinc-800'
                  }`}>
                    {isPtz ? <Crosshair className="w-3.5 h-3.5" /> : <Video className="w-3.5 h-3.5" />}
                    {/* PTZ badge */}
                    {isPtz && (
                      <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-white flex items-center justify-center">
                        <Wifi className="w-2 h-2 text-black" />
                      </div>
                    )}
                  </div>

                  {/* Pin label */}
                  <div className="absolute top-8 left-1/2 -translate-x-1/2 px-1.5 py-0.5 rounded bg-black/90 border border-zinc-800 text-[9px] whitespace-nowrap text-zinc-200">
                    {cam.name}
                    {isPtz && <span className="ml-1 text-zinc-500">PTZ</span>}
                  </div>
                </div>
              );
            })}

            {/* Active Incident Pins */}
            {displayIncidents.map((inc: any, iIdx: number) => {
              const matchInc = incidents.find(i => i.id === inc.id);
              return (
                <div
                  key={inc.id}
                  style={{ left: `${35 + iIdx * 25}%`, top: `${52 + iIdx * 5}%` }}
                  onClick={() => matchInc && onSelectIncident(matchInc)}
                  className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                >
                  {/* Threat pulse ring */}
                  {(inc.severity === 'CRITICAL' || inc.severity === 'HIGH') && (
                    <div className="absolute inset-0 -m-3 rounded-full border border-white/20 animate-ping" />
                  )}
                  <div className={`w-6 h-6 rounded-full bg-white border-2 ${severityColor(inc.severity)} flex items-center justify-center text-black font-bold`}>
                    <AlertTriangle className="w-3.5 h-3.5" />
                  </div>
                  <div className="absolute bottom-7 left-1/2 -translate-x-1/2 px-1.5 py-0.5 rounded bg-black border border-white text-[9px] whitespace-nowrap text-white font-bold">
                    {inc.code}
                  </div>
                </div>
              );
            })}

            {/* Global Track Journey Trails (cross-camera movement dots) */}
            {globalTracks.slice(0, 5).map((track: any, tIdx: number) => {
              const observations = track.observations || [];
              if (observations.length < 2) return null;
              return observations.map((obs: any, oIdx: number) => {
                const cam = displayCameras.find((c: any) => c.id === obs.camera_id);
                if (!cam) return null;
                const camIdx = displayCameras.indexOf(cam);
                const cx = 20 + (camIdx * 22) + (oIdx * 2);
                const cy = 40 + (camIdx % 2 === 0 ? 15 : -10) + 5;
                return (
                  <div
                    key={`track-${tIdx}-${oIdx}`}
                    style={{ left: `${cx}%`, top: `${cy}%` }}
                    className="absolute w-2 h-2 rounded-full bg-white/40 border border-white/60"
                    title={`Track ${track.global_track_id} @ ${cam.name}`}
                  />
                );
              });
            })}
          </div>

          {/* Legend Bar */}
          <div className="flex items-center gap-4 text-[10px] text-zinc-400 px-1">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-zinc-900 border border-zinc-600 flex items-center justify-center">
                <Video className="w-2 h-2 text-white" />
              </div>
              <span>Fixed Camera</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-zinc-900 border border-zinc-600 flex items-center justify-center relative">
                <Crosshair className="w-2 h-2 text-white" />
                <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-white" />
              </div>
              <span>PTZ Camera</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-white flex items-center justify-center">
                <AlertTriangle className="w-2 h-2 text-black" />
              </div>
              <span>Active Incident</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-0.5 bg-white/30 border-t border-dashed border-white/40" style={{ width: '12px' }} />
              <span>Topology Link</span>
            </div>
          </div>
        </div>

        {/* Right 4 Cols: Selected Camera Sensor Inspector */}
        <div className="lg:col-span-4 space-y-3">
          <div className="p-4 rounded bg-zinc-950 border border-zinc-800 space-y-3 text-xs">
            <h3 className="text-xs font-bold text-white uppercase pb-2 border-b border-zinc-800 tracking-wider">
              SENSOR GEOSPATIAL TELEMETRY
            </h3>

            {selectedCamDetail ? (
              <div className="space-y-3">
                <div>
                  <span className="text-[10px] text-zinc-400 block">SENSOR DESIGNATION</span>
                  <span className="font-bold text-white text-sm">{selectedCamDetail.name}</span>
                  <span className="text-[11px] text-zinc-300 block">{selectedCamDetail.location}</span>
                  {selectedCamDetail.ptz_enabled && (
                    <span className="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-zinc-800 text-white border border-zinc-700">
                      PTZ ENABLED
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-black border border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block">LATITUDE</span>
                    <span className="font-bold text-white">{selectedCamDetail.latitude?.toFixed(4)}° N</span>
                  </div>
                  <div className="p-2 rounded bg-black border border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block">LONGITUDE</span>
                    <span className="font-bold text-white">{selectedCamDetail.longitude?.toFixed(4)}° E</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-black border border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block">AZIMUTH / HEADING</span>
                    <span className="font-bold text-white">{selectedCamDetail.heading_deg}° TRUE</span>
                  </div>
                  <div className="p-2 rounded bg-black border border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block">FOV ANGLE</span>
                    <span className="font-bold text-white">{selectedCamDetail.fov_angle}° HORIZ</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-black border border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block">ALTITUDE</span>
                    <span className="font-bold text-white">{selectedCamDetail.altitude_m}m MSL</span>
                  </div>
                  <div className="p-2 rounded bg-black border border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block">RANGE</span>
                    <span className="font-bold text-white">{selectedCamDetail.range_meters}m</span>
                  </div>
                </div>

                <div className="p-2 rounded bg-black border border-zinc-800">
                  <span className="text-[10px] text-zinc-400 block">STATUS</span>
                  <span className="text-white font-bold">{selectedCamDetail.status}</span>
                </div>

                <button
                  onClick={() => onSelectCamera(selectedCamDetail.id)}
                  className="w-full py-2 rounded bg-white hover:bg-zinc-200 text-black font-semibold text-xs transition-colors"
                >
                  OPEN LIVE SENSOR CANVAS →
                </button>
              </div>
            ) : (
              <div className="text-zinc-500 py-6 text-center">SELECT A SENSOR NODE ON THE MAP</div>
            )}
          </div>

          {/* Active Incidents Panel */}
          <div className="p-4 rounded bg-zinc-950 border border-zinc-800 space-y-2 text-xs">
            <h3 className="text-xs font-bold text-white uppercase pb-2 border-b border-zinc-800 tracking-wider">
              ACTIVE THREAT MARKERS ({displayIncidents.length})
            </h3>
            <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
              {displayIncidents.length === 0 ? (
                <div className="text-zinc-500 py-3 text-center">NO ACTIVE THREATS</div>
              ) : (
                displayIncidents.map((inc: any) => {
                  const matchInc = incidents.find(i => i.id === inc.id);
                  return (
                    <button
                      key={inc.id}
                      onClick={() => matchInc && onSelectIncident(matchInc)}
                      className="w-full p-2 rounded bg-black border border-zinc-800 hover:border-zinc-600 text-left transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-[11px]">{inc.code}</span>
                        <span className={`text-[10px] font-mono ${
                          inc.severity === 'CRITICAL' ? 'text-white font-bold' : 'text-zinc-400'
                        }`}>
                          {inc.severity}
                        </span>
                      </div>
                      <div className="text-[10px] text-zinc-400 mt-0.5 truncate">{inc.title}</div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* Topology Summary */}
          {topologyLinks.length > 0 && (
            <div className="p-4 rounded bg-zinc-950 border border-zinc-800 space-y-2 text-xs">
              <h3 className="text-xs font-bold text-white uppercase pb-2 border-b border-zinc-800 tracking-wider flex items-center gap-1.5">
                <Share2 className="w-3.5 h-3.5" />
                CAMERA TOPOLOGY ({topologyLinks.length} LINKS)
              </h3>
              <div className="space-y-1 max-h-[120px] overflow-y-auto">
                {topologyLinks.map((link: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between p-1.5 rounded bg-black border border-zinc-800 text-[10px]">
                    <span className="text-zinc-300">
                      Cam {link.camera_a_id} ↔ Cam {link.camera_b_id}
                    </span>
                    <span className="text-zinc-500 font-mono">{link.travel_time_sec || '?'}s</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
