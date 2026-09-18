import React, { useState } from 'react';
import { Save } from 'lucide-react';

export const BehaviorSettings: React.FC = () => {
  const [loiterThreshold, setLoiterThreshold] = useState<number>(15);
  const [pacingReversals, setPacingReversals] = useState<number>(3);
  const [vehicleStopThreshold, setVehicleStopThreshold] = useState<number>(20);
  const [crowdClusteringProximity, setCrowdClusteringProximity] = useState<number>(8);
  const [isSaved, setIsSaved] = useState<boolean>(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2500);
  };

  return (
    <div className="p-4 space-y-4 font-mono">
      <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">BEHAVIORAL AI SENSITIVITY & THRESHOLD CALIBRATION</h2>
        <p className="text-xs text-zinc-400">Tune spatial-temporal algorithms for loitering, perimeter pacing, stopped vehicles, and crowd clusters</p>
      </div>

      <form onSubmit={handleSave} className="p-5 rounded bg-zinc-950 border border-zinc-800 space-y-5 text-xs max-w-2xl">
        {/* Loitering */}
        <div className="space-y-1 pb-3 border-b border-zinc-800">
          <label className="font-bold text-white block text-sm">Zone Loitering Dwell Threshold</label>
          <p className="text-zinc-400 text-[11px]">Duration in seconds an individual or target must remain within a security zone before triggering loitering alert.</p>
          <div className="flex items-center space-x-3 pt-1">
            <input
              type="range"
              min="5"
              max="60"
              value={loiterThreshold}
              onChange={(e) => setLoiterThreshold(Number(e.target.value))}
              className="flex-1 accent-white"
            />
            <span className="w-16 text-right font-bold text-white text-sm">{loiterThreshold}s</span>
          </div>
        </div>

        {/* Perimeter Pacing */}
        <div className="space-y-1 pb-3 border-b border-zinc-800">
          <label className="font-bold text-white block text-sm">Perimeter Pacing / Reversal Count</label>
          <p className="text-zinc-400 text-[11px]">Number of trajectory direction reversals along border fence line signaling suspicious patrol/scouting behavior.</p>
          <div className="flex items-center space-x-3 pt-1">
            <input
              type="range"
              min="2"
              max="10"
              value={pacingReversals}
              onChange={(e) => setPacingReversals(Number(e.target.value))}
              className="flex-1 accent-white"
            />
            <span className="w-16 text-right font-bold text-white text-sm">{pacingReversals} flips</span>
          </div>
        </div>

        {/* Vehicle Stop */}
        <div className="space-y-1 pb-3 border-b border-zinc-800">
          <label className="font-bold text-white block text-sm">Unusual Vehicle Stop Delay</label>
          <p className="text-zinc-400 text-[11px]">Delay in seconds for a vehicle stationary on border road or buffer lane before flagging suspicious vehicle stop.</p>
          <div className="flex items-center space-x-3 pt-1">
            <input
              type="range"
              min="10"
              max="120"
              value={vehicleStopThreshold}
              onChange={(e) => setVehicleStopThreshold(Number(e.target.value))}
              className="flex-1 accent-white"
            />
            <span className="w-16 text-right font-bold text-white text-sm">{vehicleStopThreshold}s</span>
          </div>
        </div>

        {/* Crowd Clustering */}
        <div className="space-y-1 pb-3 border-b border-zinc-800">
          <label className="font-bold text-white block text-sm">Squad Formation / Proximity Clustering</label>
          <p className="text-zinc-400 text-[11px]">Spatial proximity threshold (meters) for grouping 3+ individuals into an active perimeter cluster.</p>
          <div className="flex items-center space-x-3 pt-1">
            <input
              type="range"
              min="3"
              max="25"
              value={crowdClusteringProximity}
              onChange={(e) => setCrowdClusteringProximity(Number(e.target.value))}
              className="flex-1 accent-white"
            />
            <span className="w-16 text-right font-bold text-white text-sm">{crowdClusteringProximity}m</span>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          {isSaved && (
            <span className="text-white font-bold">✓ THRESHOLDS COMMITTED TO AI PIPELINE</span>
          )}
          <button
            type="submit"
            className="ml-auto px-5 py-2 rounded bg-white hover:bg-zinc-200 font-bold text-black flex items-center space-x-1.5 transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>SAVE BEHAVIOR PARAMETERS</span>
          </button>
        </div>
      </form>
    </div>
  );
};
