import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Video,
  Activity,
  ArrowUpRight,
  ShieldAlert,
  ChevronRight,
  Maximize2
} from 'lucide-react';
import { Camera, Incident, SystemHealth } from '../types';
import { apiClient, API_BASE_URL } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

interface CommandCenterProps {
  cameras: Camera[];
  incidents: Incident[];
  onSelectCamera: (camId: number) => void;
  onSelectIncident: (inc: Incident) => void;
  onTriageIncident: (incId: number, status: string) => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({
  cameras,
  incidents,
  onSelectCamera,
  onSelectIncident,
  onTriageIncident
}) => {
  const [primaryCamId, setPrimaryCamId] = useState<number>(cameras[0]?.id || 1);
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    if (cameras.length > 0 && !cameras.some(c => c.id === primaryCamId)) {
      setPrimaryCamId(cameras[0].id);
    }
  }, [cameras]);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await apiClient.get('/system/health');
        setHealth(res.data);
      } catch (e) {
        // fallback
      }
    };
    fetchHealth();
    const timer = setInterval(fetchHealth, 5000);
    return () => clearInterval(timer);
  }, []);

  const criticalIncidents = incidents.filter(
    i => i.severity === 'CRITICAL' && i.status !== 'RESOLVED'
  );
  const recentIncidents = incidents.slice(0, 10);
  const primaryCam = cameras.find(c => c.id === primaryCamId) || cameras[0];
  const onlineCameras = cameras.filter(c => c.status === 'ONLINE').length;

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* 1. Header Operational Status Bar */}
      <div className="bg-[#09090b] border border-[#27272a] rounded-md px-4 py-3 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block">Fleet Status</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-base font-semibold text-white">{onlineCameras} / {cameras.length}</span>
              <span className="text-xs text-zinc-400">Cameras Online</span>
            </div>
          </div>

          <div className="h-8 w-px bg-[#27272a] hidden sm:block" />

          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block">Active Incidents</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-base font-semibold ${criticalIncidents.length > 0 ? 'text-white font-bold underline' : 'text-zinc-200'}`}>
                {criticalIncidents.length} Critical
              </span>
              <span className="text-xs text-zinc-400">({incidents.filter(i => i.status === 'NEW').length} unacknowledged)</span>
            </div>
          </div>

          <div className="h-8 w-px bg-[#27272a] hidden sm:block" />

          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block">System Load</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-base font-semibold text-white font-mono">
                {health?.cpu_usage_pct !== undefined ? `${health.cpu_usage_pct}%` : 'Normal'}
              </span>
              <span className="text-xs text-zinc-400">CPU Usage</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant={criticalIncidents.length > 0 ? 'critical' : 'success'} dot>
            {criticalIncidents.length > 0 ? 'Active Intrusion Threat' : 'Perimeter Secured'}
          </Badge>
        </div>
      </div>

      {/* 2. Primary Operator Row: Active Incidents | Live Camera Focus */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Active Incidents Queue (5 Cols) */}
        <div className="lg:col-span-5 bg-[#09090b] border border-[#27272a] rounded-md flex flex-col h-[480px]">
          <div className="px-3.5 py-2.5 border-b border-[#27272a] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-white" />
              <h2 className="text-xs font-semibold text-white uppercase tracking-wide">
                Incident Triage Queue
              </h2>
            </div>
            <span className="text-xs font-mono text-zinc-400">
              {incidents.length} total
            </span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-[#1c1c20]">
            {incidents.length === 0 ? (
              <div className="p-8 text-center text-zinc-500 text-xs">
                No security incidents reported.
              </div>
            ) : (
              incidents.slice(0, 8).map((inc) => {
                const isCrit = inc.severity === 'CRITICAL';
                return (
                  <div
                    key={inc.id}
                    onClick={() => onSelectIncident(inc)}
                    className="p-3 hover:bg-[#18181b] cursor-pointer transition-colors space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <Badge variant={isCrit ? 'critical' : 'warning'}>
                          {inc.severity}
                        </Badge>
                        <span className="text-xs font-semibold text-white truncate max-w-[200px]">
                          {inc.title}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-zinc-400">
                        {new Date(inc.detected_at).toLocaleTimeString()}
                      </span>
                    </div>

                    <p className="text-xs text-zinc-400 line-clamp-1 leading-normal">
                      {inc.summary}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-zinc-400 pt-0.5">
                      <span className="font-mono text-zinc-400">{inc.location_name}</span>
                      <div className="flex items-center gap-1.5">
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-[#18181b] border border-[#27272a] text-zinc-300">
                          {inc.status}
                        </span>
                        <ChevronRight className="w-3.5 h-3.5 text-zinc-400" />
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Live Camera Focus (7 Cols) */}
        <div className="lg:col-span-7 bg-[#09090b] border border-[#27272a] rounded-md flex flex-col h-[480px]">
          <div className="px-3.5 py-2.5 border-b border-[#27272a] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Video className="w-4 h-4 text-white" />
              <span className="text-xs font-semibold text-white uppercase tracking-wide">
                Live Focus &bull; {primaryCam?.name || 'Primary Feed'}
              </span>
            </div>

            {/* Quick Camera Switcher */}
            <div className="flex items-center gap-2">
              <select
                value={primaryCamId}
                onChange={(e) => setPrimaryCamId(Number(e.target.value))}
                className="bg-[#18181b] border border-[#27272a] text-white text-xs rounded px-2 py-1 focus:outline-none"
              >
                {cameras.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>

              <button
                onClick={() => onSelectCamera(primaryCamId)}
                title="Full Camera Diagnostics"
                className="p-1 rounded text-zinc-400 hover:text-white hover:bg-[#18181b]"
              >
                <ArrowUpRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Video Player */}
          <div className="flex-1 bg-black relative flex items-center justify-center overflow-hidden">
            {primaryCam ? (
              <img
                src={`${API_BASE_URL}/api/v1/streams/${primaryCam.id}/live.mjpg?annotated=true&fps=18`}
                alt={primaryCam.name}
                className="w-full h-full object-contain"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  setTimeout(() => {
                    target.src = `${API_BASE_URL}/api/v1/streams/${primaryCam.id}/live.mjpg?annotated=true&fps=18&t=${Date.now()}`;
                  }, 2000);
                }}
              />
            ) : (
              <div className="text-xs text-zinc-400">Camera offline or unreachable</div>
            )}

            {/* Minimal HUD overlay banner */}
            <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between px-2.5 py-1 rounded bg-black/80 backdrop-blur-sm border border-white/20 text-[11px] text-zinc-300 font-mono">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                <span>LIVE OVERLAY ENABLED</span>
              </div>
              <div>{primaryCam?.location} &bull; {primaryCam?.current_fps || 25} FPS</div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Secondary Row: Recent Operational Events | Camera Fleet Status Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Recent Operational Events (6 Cols) */}
        <div className="lg:col-span-6 bg-[#09090b] border border-[#27272a] rounded-md flex flex-col">
          <div className="px-3.5 py-2.5 border-b border-[#27272a] flex items-center justify-between">
            <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
              Recent Detection Events
            </h3>
            <span className="text-[11px] text-zinc-400 font-mono">Real-time Stream</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#121215] text-zinc-400 border-b border-[#27272a] font-semibold text-[11px]">
                <tr>
                  <th className="p-2.5">TIME</th>
                  <th className="p-2.5">EVENT</th>
                  <th className="p-2.5">SEVERITY</th>
                  <th className="p-2.5">LOCATION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1c1c20] text-zinc-300 font-mono text-[12px]">
                {recentIncidents.slice(0, 5).map((ev) => (
                  <tr key={ev.id} className="hover:bg-[#18181b]/60">
                    <td className="p-2.5 text-zinc-400">
                      {new Date(ev.detected_at).toLocaleTimeString()}
                    </td>
                    <td className="p-2.5 font-sans font-medium text-zinc-100 truncate max-w-[180px]">
                      {ev.title}
                    </td>
                    <td className="p-2.5">
                      <Badge variant={ev.severity === 'CRITICAL' ? 'critical' : 'warning'}>
                        {ev.severity}
                      </Badge>
                    </td>
                    <td className="p-2.5 text-zinc-400 truncate max-w-[140px]">
                      {ev.location_name}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Camera Fleet Health Table (6 Cols) */}
        <div className="lg:col-span-6 bg-[#09090b] border border-[#27272a] rounded-md flex flex-col">
          <div className="px-3.5 py-2.5 border-b border-[#27272a] flex items-center justify-between">
            <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
              Camera Fleet Health
            </h3>
            <span className="text-[11px] text-zinc-400 font-mono">
              {onlineCameras} active feeds
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#121215] text-zinc-400 border-b border-[#27272a] font-semibold text-[11px]">
                <tr>
                  <th className="p-2.5">CAMERA</th>
                  <th className="p-2.5">STATUS</th>
                  <th className="p-2.5">FPS</th>
                  <th className="p-2.5">LATENCY</th>
                  <th className="p-2.5">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1c1c20] text-zinc-300 font-mono text-[12px]">
                {cameras.map((cam) => (
                  <tr key={cam.id} className="hover:bg-[#18181b]/60">
                    <td className="p-2.5 font-sans font-medium text-zinc-100 truncate max-w-[180px]">
                      {cam.name}
                    </td>
                    <td className="p-2.5">
                      <Badge variant={cam.status === 'ONLINE' ? 'success' : 'critical'} dot>
                        {cam.status}
                      </Badge>
                    </td>
                    <td className="p-2.5 text-zinc-300">
                      {cam.current_fps || 25}
                    </td>
                    <td className="p-2.5 text-zinc-400">
                      {cam.latency_ms || 24} ms
                    </td>
                    <td className="p-2.5">
                      <button
                        onClick={() => onSelectCamera(cam.id)}
                        className="text-white hover:underline text-xs font-sans font-medium"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
