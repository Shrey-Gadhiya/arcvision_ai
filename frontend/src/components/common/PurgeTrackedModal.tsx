import React, { useState } from 'react';
import { AlertTriangle, Trash2, X, Check, ShieldAlert, Loader2, RefreshCw } from 'lucide-react';
import { nvrApi } from '../../api/nvr';
import { Camera } from '../../types';

interface PurgeTrackedModalProps {
  isOpen: boolean;
  onClose: () => void;
  cameras?: Camera[];
  initialCameraId?: number | null;
  onPurgeComplete?: (result: { streamers_reset: number; deleted_snapshots: number }) => void;
}

export const PurgeTrackedModal: React.FC<PurgeTrackedModalProps> = ({
  isOpen,
  onClose,
  cameras = [],
  initialCameraId = null,
  onPurgeComplete,
}) => {
  const [selectedCameraId, setSelectedCameraId] = useState<number | 'ALL'>(
    initialCameraId ? initialCameraId : 'ALL'
  );
  const [deleteSnapshots, setDeleteSnapshots] = useState<boolean>(true);
  const [verificationInput, setVerificationInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [successResult, setSuccessResult] = useState<{
    streamers_reset: number;
    deleted_snapshots: number;
    message: string;
  } | null>(null);

  if (!isOpen) return null;

  const isVerified = verificationInput.trim().toUpperCase() === 'PURGE';

  const handleExecutePurge = async () => {
    if (!isVerified || isLoading) return;
    setIsLoading(true);
    setError('');

    try {
      const camId = selectedCameraId === 'ALL' ? undefined : selectedCameraId;
      const res = await nvrApi.clearAllTrackedObjects({
        cameraId: camId,
        deleteSnapshots
      });

      setSuccessResult({
        streamers_reset: res.streamers_reset ?? 0,
        deleted_snapshots: res.deleted_snapshots ?? 0,
        message: res.message || 'Tracked objects purged successfully.'
      });

      if (onPurgeComplete) {
        onPurgeComplete({
          streamers_reset: res.streamers_reset ?? 0,
          deleted_snapshots: res.deleted_snapshots ?? 0
        });
      }

      // Auto close after brief display
      setTimeout(() => {
        handleClose();
      }, 1500);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Failed to purge tracked objects. Check authentication and permissions.';
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg bg-[#0c0c0e] border border-red-900/60 rounded-2xl shadow-2xl p-6 text-white overflow-hidden">
        {/* Glowing tactical warning accent */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-600 via-amber-500 to-red-600" />
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-red-600/10 blur-[80px] pointer-events-none rounded-full" />

        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-zinc-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-950/80 border border-red-700/80 flex items-center justify-center text-red-400 shrink-0 shadow-lg">
              <ShieldAlert className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
                Remove All Tracked Objects
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800">
                  TACTICAL CLEAR
                </span>
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Operator Verification & Multi-Object Tracker Flush
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
        <div className="py-4 space-y-4">
          {/* Warning Banner */}
          <div className="p-3.5 rounded-xl bg-red-950/30 border border-red-800/60 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-zinc-300 space-y-1">
              <p className="font-semibold text-red-300">
                Security-Critical Action
              </p>
              <p className="text-zinc-400 leading-relaxed">
                This operation will immediately flush active tracking IDs, Kalman trajectories, bounding box overlays, and cross-camera associations across live video feeds.
              </p>
            </div>
          </div>

          {/* Scope Selector */}
          <div>
            <label className="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1.5">
              Scope of Purge
            </label>
            <select
              value={selectedCameraId}
              onChange={(e) => setSelectedCameraId(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
              disabled={isLoading}
              className="w-full bg-black/60 border border-zinc-700/80 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-red-500 transition-colors font-mono"
            >
              <option value="ALL">All Active Cameras ({cameras.length} Streamers)</option>
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>
                  Camera #{c.id}: {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Delete database records checkbox */}
          <label className="flex items-center gap-2.5 cursor-pointer select-none p-2 rounded-lg bg-zinc-900/60 border border-zinc-800 hover:border-zinc-700 transition-colors">
            <input
              type="checkbox"
              checked={deleteSnapshots}
              onChange={(e) => setDeleteSnapshots(e.target.checked)}
              disabled={isLoading}
              className="w-4 h-4 rounded border-zinc-700 text-red-600 focus:ring-red-500 bg-black cursor-pointer"
            />
            <span className="text-xs text-zinc-300">
              Also delete all saved tracked object snapshots & crops from database
            </span>
          </label>

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
                {successResult.message} ({successResult.streamers_reset} streamers reset, {successResult.deleted_snapshots} snapshots removed)
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
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            onClick={handleClose}
            disabled={isLoading}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-300 hover:text-white bg-zinc-800/80 hover:bg-zinc-700/80 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleExecutePurge}
            disabled={!isVerified || isLoading}
            className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg transition-all ${
              isVerified && !isLoading
                ? 'bg-red-600 hover:bg-red-500 active:bg-red-700 text-white cursor-pointer shadow-red-900/40'
                : 'bg-zinc-800 text-zinc-500 border border-zinc-700/50 cursor-not-allowed'
            }`}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Flushing Trackers…
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                Verify & Remove All Tracked Objects
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
