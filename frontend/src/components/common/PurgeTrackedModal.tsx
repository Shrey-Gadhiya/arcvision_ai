import React, { useState } from 'react';
import { AlertTriangle, Trash2, X, Check, ShieldAlert, Loader2, HardDrive, Database, Camera as CameraIcon } from 'lucide-react';
import { nvrApi } from '../../api/nvr';
import { Camera } from '../../types';

interface PurgeTrackedModalProps {
  isOpen: boolean;
  onClose: () => void;
  cameras?: Camera[];
  initialCameraId?: number | null;
  onPurgeComplete?: (result: { streamers_reset: number; deleted_snapshots: number; freed_mb?: number }) => void;
}

export const PurgeTrackedModal: React.FC<PurgeTrackedModalProps> = ({
  isOpen,
  onClose,
  cameras = [],
  initialCameraId = null,
  onPurgeComplete,
}) => {
  const [purgeMode, setPurgeMode] = useState<'ALL_SURVEILLANCE_DATA' | 'TRACKS_ONLY' | 'FACTORY_RESET'>('ALL_SURVEILLANCE_DATA');
  const [selectedCameraId, setSelectedCameraId] = useState<number | 'ALL'>(
    initialCameraId ? initialCameraId : 'ALL'
  );
  const [purgeRecordings, setPurgeRecordings] = useState<boolean>(true);
  const [purgeSnapshots, setPurgeSnapshots] = useState<boolean>(true);
  const [purgeEvents, setPurgeEvents] = useState<boolean>(true);
  const [purgeIncidents, setPurgeIncidents] = useState<boolean>(true);
  const [verificationInput, setVerificationInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [successResult, setSuccessResult] = useState<{
    message: string;
    files_deleted: number;
    freed_mb: number;
    records_purged: number;
  } | null>(null);

  if (!isOpen) return null;

  const isVerified = verificationInput.trim().toUpperCase() === 'PURGE';

  const handleExecutePurge = async () => {
    if (!isVerified || isLoading) return;
    setIsLoading(true);
    setError('');

    try {
      const camId = selectedCameraId === 'ALL' ? undefined : selectedCameraId;
      const res = await nvrApi.purgeAllData({
        scope: purgeMode,
        cameraId: camId,
        purgeRecordings: purgeMode === 'TRACKS_ONLY' ? false : purgeRecordings,
        purgeSnapshots: purgeMode === 'TRACKS_ONLY' ? false : purgeSnapshots,
        purgeEventsAndDetections: purgeMode === 'TRACKS_ONLY' ? false : purgeEvents,
        purgeIncidentsAndEvidence: purgeMode === 'TRACKS_ONLY' ? false : purgeIncidents,
        deleteCameras: purgeMode === 'FACTORY_RESET',
      });

      setSuccessResult({
        message: res.message || 'Surveillance data purged successfully.',
        files_deleted: res.files_deleted ?? 0,
        freed_mb: res.freed_mb ?? 0,
        records_purged: res.records_purged ?? 0,
      });

      if (onPurgeComplete) {
        onPurgeComplete({
          streamers_reset: res.streamers_reset ?? 0,
          deleted_snapshots: res.files_deleted ?? 0,
          freed_mb: res.freed_mb ?? 0,
        });
      }

      // Auto close after brief display
      setTimeout(() => {
        handleClose();
      }, 2000);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to purge data. Check permissions.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setVerificationInput('');
    setError('');
    setSuccessResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-150">
      <div className="relative w-full max-w-xl bg-[#09090b] border border-red-900/60 rounded-2xl shadow-2xl p-6 text-white overflow-hidden">
        {/* Glowing tactical warning accent */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-600 via-amber-500 to-red-600" />
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-red-600/10 blur-[80px] pointer-events-none rounded-full" />

        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-950/80 border border-red-700/80 flex items-center justify-center text-red-400 shrink-0 shadow-lg">
              <ShieldAlert className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
                Tactical Data Purge & Removal Center
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800">
                  SYSTEM CLEAN
                </span>
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Reclaim disk storage, remove historical evidence, or reset tracking telemetry
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-zinc-500 hover:text-white p-1 rounded-lg hover:bg-zinc-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="py-4 space-y-4 max-h-[75vh] overflow-y-auto pr-1">
          {/* Purge Mode Selector */}
          <div>
            <label className="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-2">
              Select Purge Objective
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setPurgeMode('ALL_SURVEILLANCE_DATA')}
                className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                  purgeMode === 'ALL_SURVEILLANCE_DATA'
                    ? 'bg-red-950/40 border-red-600 text-white ring-1 ring-red-500'
                    : 'bg-zinc-900/50 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                }`}
              >
                <HardDrive className={`w-4 h-4 mb-2 ${purgeMode === 'ALL_SURVEILLANCE_DATA' ? 'text-red-400' : 'text-zinc-500'}`} />
                <span className="text-xs font-semibold block text-white">Purge All Media</span>
                <span className="text-[10px] text-zinc-400 mt-0.5">Wipes recordings & snapshots; preserves cameras</span>
              </button>

              <button
                type="button"
                onClick={() => setPurgeMode('TRACKS_ONLY')}
                className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                  purgeMode === 'TRACKS_ONLY'
                    ? 'bg-amber-950/40 border-amber-600 text-white ring-1 ring-amber-500'
                    : 'bg-zinc-900/50 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                }`}
              >
                <Database className={`w-4 h-4 mb-2 ${purgeMode === 'TRACKS_ONLY' ? 'text-amber-400' : 'text-zinc-500'}`} />
                <span className="text-xs font-semibold block text-white">Tracks Only</span>
                <span className="text-[10px] text-zinc-400 mt-0.5">Flushes active in-memory trackers & boxes</span>
              </button>

              <button
                type="button"
                onClick={() => setPurgeMode('FACTORY_RESET')}
                className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                  purgeMode === 'FACTORY_RESET'
                    ? 'bg-red-950/80 border-red-500 text-white ring-1 ring-red-400'
                    : 'bg-zinc-900/50 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                }`}
              >
                <CameraIcon className={`w-4 h-4 mb-2 ${purgeMode === 'FACTORY_RESET' ? 'text-red-400' : 'text-zinc-500'}`} />
                <span className="text-xs font-semibold block text-white">Factory Reset</span>
                <span className="text-[10px] text-zinc-400 mt-0.5">Wipes all cameras, rules, and all data</span>
              </button>
            </div>
          </div>

          {/* Scope Selector */}
          {purgeMode !== 'FACTORY_RESET' && (
            <div>
              <label className="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1.5">
                Target Sensor Scope
              </label>
              <select
                value={selectedCameraId}
                onChange={(e) => setSelectedCameraId(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
                disabled={isLoading}
                className="w-full bg-black/60 border border-zinc-700/80 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-red-500 transition-colors font-mono"
              >
                <option value="ALL">Entire Fleet (All {cameras.length} Active Streamers)</option>
                {cameras.map((c) => (
                  <option key={c.id} value={c.id}>
                    Camera #{c.id}: {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Granular Purge Checkboxes (for media purge) */}
          {purgeMode === 'ALL_SURVEILLANCE_DATA' && (
            <div className="space-y-2 p-3 bg-zinc-900/40 border border-zinc-800/80 rounded-xl">
              <span className="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1">
                Data Categories to Remove
              </span>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <label className="flex items-center gap-2 cursor-pointer select-none text-zinc-300">
                  <input
                    type="checkbox"
                    checked={purgeRecordings}
                    onChange={(e) => setPurgeRecordings(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-700 text-red-600 focus:ring-red-500 bg-black cursor-pointer"
                  />
                  <span>Recorded MP4 Segments (Disk & DB)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer select-none text-zinc-300">
                  <input
                    type="checkbox"
                    checked={purgeSnapshots}
                    onChange={(e) => setPurgeSnapshots(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-700 text-red-600 focus:ring-red-500 bg-black cursor-pointer"
                  />
                  <span>Snapshot Images & Crops (Disk & DB)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer select-none text-zinc-300">
                  <input
                    type="checkbox"
                    checked={purgeEvents}
                    onChange={(e) => setPurgeEvents(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-700 text-red-600 focus:ring-red-500 bg-black cursor-pointer"
                  />
                  <span>Detections & Rule Events (DB)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer select-none text-zinc-300">
                  <input
                    type="checkbox"
                    checked={purgeIncidents}
                    onChange={(e) => setPurgeIncidents(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-700 text-red-600 focus:ring-red-500 bg-black cursor-pointer"
                  />
                  <span>Incidents, Evidence & Logs (DB)</span>
                </label>
              </div>
            </div>
          )}

          {/* Warning Banner */}
          <div className="p-3 rounded-xl bg-red-950/30 border border-red-800/60 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-zinc-300 space-y-0.5">
              <p className="font-semibold text-red-300">
                Permanent Removal Notice
              </p>
              <p className="text-zinc-400 leading-relaxed text-[11px]">
                {purgeMode === 'FACTORY_RESET'
                  ? 'All cameras, zones, virtual fences, recordings, and snapshots will be completely erased. Only admin accounts will be retained.'
                  : 'Selected media files on disk and historical tracking rows will be permanently deleted and SQLite storage will be compacted.'}
              </p>
            </div>
          </div>

          {/* Verification Challenge */}
          <div className="space-y-1.5 pt-1">
            <label className="block text-[11px] font-medium text-zinc-300 uppercase tracking-wider">
              Verification: Type <span className="font-mono text-red-400 font-bold">PURGE</span> to confirm
            </label>
            <div className="relative">
              <input
                type="text"
                value={verificationInput}
                onChange={(e) => setVerificationInput(e.target.value)}
                placeholder="Type PURGE"
                disabled={isLoading}
                className="w-full bg-black/80 border border-zinc-700 focus:border-red-500 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-red-500/50 font-mono uppercase tracking-widest"
              />
              {isVerified && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-xs text-emerald-400 font-mono">
                  <Check className="w-4 h-4" />
                  Verified
                </span>
              )}
            </div>
          </div>

          {/* Success Banner */}
          {successResult && (
            <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2.5">
              <Check className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>
                {successResult.message} ({successResult.files_deleted} disk files removed, {successResult.freed_mb} MB reclaimed)
              </span>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-3 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs">
              {error}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
          <button
            type="button"
            onClick={handleClose}
            disabled={isLoading}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-300 hover:text-white bg-zinc-800/80 hover:bg-zinc-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleExecutePurge}
            disabled={!isVerified || isLoading}
            className={`px-5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg transition-all ${
              isVerified && !isLoading
                ? 'bg-red-600 hover:bg-red-500 active:bg-red-700 text-white cursor-pointer shadow-red-900/40'
                : 'bg-zinc-800 text-zinc-500 border border-zinc-700/50 cursor-not-allowed'
            }`}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Executing Purge…
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                Confirm & Purge Surveillance Data
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
