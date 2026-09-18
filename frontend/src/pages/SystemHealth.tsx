import React, { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { SystemHealth as HealthType } from '../types';
import { apiClient } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const SystemHealth: React.FC = () => {
  const [health, setHealth] = useState<HealthType | null>(null);

  const fetchHealth = async () => {
    try {
      const res = await apiClient.get('/health/');
      setHealth(res.data);
    } catch (e) {
      // fallback
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 3000);
    return () => clearInterval(interval);
  }, []);

  const diskUsedPct = health ? Math.round(((health.disk_total_gb - health.disk_free_gb) / health.disk_total_gb) * 100) : 0;

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <div>
          <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
            Platform System Telemetry
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Operational compute metrics, memory allocation, edge worker threads, and camera decoding pipelines.
          </p>
        </div>

        <Button variant="secondary" size="sm" icon={<RefreshCw className="w-3 h-3" />} onClick={fetchHealth}>
          Refresh Telemetry
        </Button>
      </div>

      {health ? (
        <>
          {/* Main Resource Gauges */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* CPU */}
            <div className="p-3.5 rounded-md bg-zinc-950 border border-zinc-800 space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-semibold uppercase tracking-wider text-[11px]">CPU Usage</span>
                <span className="font-mono font-bold text-white">{health.cpu_usage_pct}%</span>
              </div>
              <div className="w-full bg-black h-1.5 rounded-full overflow-hidden border border-zinc-800">
                <div
                  className="h-full bg-white"
                  style={{ width: `${health.cpu_usage_pct}%` }}
                />
              </div>
              <div className="text-[11px] text-zinc-400 font-sans">
                Host CPU Core Load
              </div>
            </div>

            {/* RAM */}
            <div className="p-3.5 rounded-md bg-zinc-950 border border-zinc-800 space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-semibold uppercase tracking-wider text-[11px]">System Memory</span>
                <span className="font-mono font-bold text-white">{health.memory_usage_pct}%</span>
              </div>
              <div className="w-full bg-black h-1.5 rounded-full overflow-hidden border border-zinc-800">
                <div
                  className="h-full bg-zinc-300"
                  style={{ width: `${health.memory_usage_pct}%` }}
                />
              </div>
              <div className="text-[11px] text-zinc-400 font-mono">
                {health.memory_used_gb} GB / {health.memory_total_gb} GB
              </div>
            </div>

            {/* Disk */}
            <div className="p-3.5 rounded-md bg-zinc-950 border border-zinc-800 space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-semibold uppercase tracking-wider text-[11px]">Storage Vault</span>
                <span className="font-mono font-bold text-white">{diskUsedPct}%</span>
              </div>
              <div className="w-full bg-black h-1.5 rounded-full overflow-hidden border border-zinc-800">
                <div
                  className="h-full bg-zinc-400"
                  style={{ width: `${diskUsedPct}%` }}
                />
              </div>
              <div className="text-[11px] text-zinc-400 font-mono">
                {health.disk_free_gb} GB free of {health.disk_total_gb} GB
              </div>
            </div>

            {/* Service Status */}
            <div className="p-3.5 rounded-md bg-zinc-950 border border-zinc-800 space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-semibold uppercase tracking-wider text-[11px]">Core Services</span>
                <Badge variant="success" dot>Healthy</Badge>
              </div>
              <div className="pt-1 text-[11px] text-zinc-400 font-sans space-y-0.5">
                <div>AI Pipeline: <span className="text-white font-mono">YOLOv8 Active</span></div>
                <div>Database: <span className="text-white font-mono">SQLite (aiosqlite)</span></div>
              </div>
            </div>
          </div>

          {/* Active Camera Threads Worker Table */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
              <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
                Camera Stream Worker Telemetry
              </h2>
              <span className="text-xs font-mono text-zinc-400">
                {health.cameras.length} background decoder threads
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase tracking-wider">
                  <tr>
                    <th className="p-3">CAMERA</th>
                    <th className="p-3">STATUS</th>
                    <th className="p-3">CURRENT FPS</th>
                    <th className="p-3">TARGET FPS</th>
                    <th className="p-3">TOTAL FRAMES</th>
                    <th className="p-3">PROCESS STATE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800 text-zinc-300 font-mono">
                  {health.cameras.map((c) => (
                    <tr key={c.camera_id} className="hover:bg-zinc-900/50">
                      <td className="p-3 font-sans font-medium text-white">
                        {c.name} (Cam #{c.camera_id})
                      </td>
                      <td className="p-3">
                        <Badge variant={c.status === 'ONLINE' ? 'success' : 'critical'} dot>
                          {c.status}
                        </Badge>
                      </td>
                      <td className="p-3 text-white">
                        {c.fps}
                      </td>
                      <td className="p-3 text-zinc-400">
                        {c.target_fps}
                      </td>
                      <td className="p-3 text-zinc-300">
                        {c.frames_processed.toLocaleString()}
                      </td>
                      <td className="p-3">
                        <span className="text-[11px] text-white font-sans">
                          {c.is_running ? 'Streaming' : 'Idle'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="p-12 text-center text-xs text-zinc-500 bg-zinc-950 border border-zinc-800 rounded-md">
          Connecting to system telemetry service...
        </div>
      )}
    </div>
  );
};
