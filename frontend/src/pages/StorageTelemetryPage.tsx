import React, { useState, useEffect } from 'react';
import {
  HardDrive,
  Trash2,
  RefreshCw,
  Film,
  Eye,
  Shield,
  CheckCircle2,
  Database
} from 'lucide-react';
import { StorageTelemetry } from '../types';
import { nvrApi } from '../api/nvr';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const StorageTelemetryPage: React.FC = () => {
  const [telemetry, setTelemetry] = useState<StorageTelemetry | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isCleaning, setIsCleaning] = useState<boolean>(false);
  const [cleanResult, setCleanResult] = useState<string | null>(null);

  const fetchTelemetry = () => {
    setIsLoading(true);
    nvrApi
      .getStorageTelemetry()
      .then((data) => {
        setTelemetry(data);
      })
      .catch((err) => {
        console.error('Failed to load storage telemetry:', err);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchTelemetry();
  }, []);

  const handleEnforceRetention = async () => {
    setIsCleaning(true);
    setCleanResult(null);
    try {
      const res = await nvrApi.enforceRetention();
      setCleanResult(`Retention enforced: pruned ${res.pruned_segments} expired segments, freed ${(res.freed_bytes / (1024 * 1024)).toFixed(2)} MB.`);
      fetchTelemetry();
    } catch (err: any) {
      setCleanResult('Failed to enforce retention policies.');
    } finally {
      setIsCleaning(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Page Header */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-white" />
            NVR Storage Management & Retention Engine
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Disk allocation, automated per-camera retention policies, segment lifecycle, and forensic storage quotas.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={fetchTelemetry} disabled={isLoading}>
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            variant="danger"
            size="sm"
            onClick={handleEnforceRetention}
            disabled={isCleaning}
            className="flex items-center gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5" />
            {isCleaning ? 'Pruning...' : 'Enforce Retention Cleanup'}
          </Button>
        </div>
      </div>

      {cleanResult && (
        <div className="p-3 bg-zinc-900 border border-zinc-700 rounded text-white text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-white shrink-0" />
          <span>{cleanResult}</span>
        </div>
      )}

      {/* Storage Health & Threshold Warning Banner */}
      {telemetry && telemetry.warning_level && telemetry.warning_level !== 'NORMAL' && (
        <div className="p-3.5 bg-zinc-900 border border-zinc-700 rounded text-white text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 font-mono">
            <span className="w-2.5 h-2.5 rounded-full bg-white animate-pulse" />
            <span className="font-bold uppercase tracking-wider">{telemetry.warning_level}:</span>
            <span>{telemetry.warning_message}</span>
          </div>
          <Button variant="primary" size="sm" onClick={handleEnforceRetention} disabled={isCleaning}>
            {isCleaning ? 'Pruning...' : 'Run Auto-Prune Now'}
          </Button>
        </div>
      )}

      {/* Disk Capacity & Category Allocation Cards */}
      {telemetry && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Total Disk Card */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span className="font-semibold uppercase tracking-wider text-[11px]">System Disk Capacity</span>
              <Database className="w-4 h-4 text-white" />
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {formatBytes(telemetry.disk_used_bytes)} / {formatBytes(telemetry.disk_total_bytes)}
            </div>
            {/* Progress Bar */}
            <div className="w-full h-1.5 bg-black rounded-full overflow-hidden border border-zinc-800">
              <div
                className={`h-full ${telemetry.disk_used_percent > 85 ? 'bg-zinc-300' : 'bg-white'}`}
                style={{ width: `${Math.min(100, telemetry.disk_used_percent)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] font-mono text-zinc-400">
              <span>Used: {telemetry.disk_used_percent}%</span>
              <span>Free: {formatBytes(telemetry.disk_free_bytes)}</span>
            </div>
          </div>

          {/* Recordings Card */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Archival Video Segments</span>
              <Film className="w-4 h-4 text-white" />
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {formatBytes(telemetry.categories.recordings.bytes)}
            </div>
            <div className="text-[11px] text-zinc-400 font-mono">
              {telemetry.categories.recordings.count} MP4 segments stored
            </div>
          </div>

          {/* Snapshots Card */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Tracked Object Snapshots</span>
              <Eye className="w-4 h-4 text-white" />
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {formatBytes(telemetry.categories.snapshots.bytes)}
            </div>
            <div className="text-[11px] text-zinc-400 font-mono">
              {telemetry.categories.snapshots.count} frames & crops
            </div>
          </div>

          {/* Evidence Card */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Protected Evidence</span>
              <Shield className="w-4 h-4 text-white" />
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {formatBytes(telemetry.categories.evidence.bytes + (telemetry.protected_evidence?.bytes || 0))}
            </div>
            <div className="text-[11px] text-zinc-400 font-mono">
              {telemetry.protected_evidence?.count || 0} locked segments
            </div>
          </div>

          {/* Database Card */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Database (SQLite)</span>
              <HardDrive className="w-4 h-4 text-white" />
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {formatBytes(telemetry.categories.database?.bytes || 0)}
            </div>
            <div className="text-[10px] text-zinc-400 font-mono truncate" title={telemetry.oldest_recording_time || 'N/A'}>
              Oldest: {telemetry.oldest_recording_time ? new Date(telemetry.oldest_recording_time).toLocaleDateString() : 'Active'}
            </div>
          </div>
        </div>
      )}

      {/* Per-Camera Retention & Footprint Table */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/60">
          <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
            Per-Camera Storage Allocation & Retention Policies
          </h2>
          <span className="text-[11px] font-mono text-zinc-400">
            {telemetry?.per_camera.length || 0} Ingestion Channels Configured
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black text-zinc-400 border-b border-zinc-800 font-mono uppercase text-[10px]">
              <tr>
                <th className="px-4 py-2.5">Camera Name</th>
                <th className="px-4 py-2.5">Tactical Sector</th>
                <th className="px-4 py-2.5">Recording Mode</th>
                <th className="px-4 py-2.5">Continuous Retention</th>
                <th className="px-4 py-2.5">Event Retention</th>
                <th className="px-4 py-2.5">Recordings Size</th>
                <th className="px-4 py-2.5">Snapshots Size</th>
                <th className="px-4 py-2.5">Total Disk Footprint</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800 text-zinc-200">
              {telemetry?.per_camera.map((cam) => (
                <tr key={cam.camera_id} className="hover:bg-zinc-900 transition-colors">
                  <td className="px-4 py-2.5 font-semibold text-white flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-white" />
                    {cam.camera_name}
                  </td>
                  <td className="px-4 py-2.5 text-zinc-400">{cam.group_name}</td>
                  <td className="px-4 py-2.5">
                    <Badge variant="neutral">{cam.recording_mode}</Badge>
                  </td>
                  <td className="px-4 py-2.5 font-mono">{cam.retention_days} Days</td>
                  <td className="px-4 py-2.5 font-mono text-zinc-300 font-medium">
                    {cam.retention_events_days} Days
                  </td>
                  <td className="px-4 py-2.5 font-mono text-zinc-300">
                    {formatBytes(cam.recording_bytes)} ({cam.recording_count} seg)
                  </td>
                  <td className="px-4 py-2.5 font-mono text-zinc-300">
                    {formatBytes(cam.snapshot_bytes)} ({cam.snapshot_count} snaps)
                  </td>
                  <td className="px-4 py-2.5 font-mono font-bold text-white">
                    {formatBytes(cam.total_bytes)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
