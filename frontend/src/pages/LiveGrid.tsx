import React, { useState, useEffect } from 'react';
import { Layers, Maximize2, Camera as CameraIcon, Grid, Trash2 } from 'lucide-react';
import { Camera } from '../types';
import { API_BASE_URL } from '../api/client';
import { Badge } from '../components/common/Badge';

interface LiveGridProps {
  cameras: Camera[];
  onSelectCamera: (camId: number) => void;
  onOpenPurgeModal?: () => void;
}

type GridLayout = '1x1' | '2x2' | '3x3';

export const LiveGrid: React.FC<LiveGridProps> = ({ cameras, onSelectCamera, onOpenPurgeModal }) => {
  const [layout, setLayout] = useState<GridLayout>('2x2');
  const [selectedGroup, setSelectedGroup] = useState<string>('ALL');
  const [showOverlays, setShowOverlays] = useState<boolean>(true);
  const [isTabVisible, setIsTabVisible] = useState<boolean>(!document.hidden);

  useEffect(() => {
    const handleVis = () => setIsTabVisible(!document.hidden);
    document.addEventListener('visibilitychange', handleVis);
    return () => document.removeEventListener('visibilitychange', handleVis);
  }, []);

  const groups = ['ALL', ...Array.from(new Set(cameras.map(c => c.group_name)))];

  const filteredCameras = selectedGroup === 'ALL'
    ? cameras
    : cameras.filter(c => c.group_name === selectedGroup);

  const getGridClass = () => {
    switch (layout) {
      case '1x1':
        return 'grid-cols-1';
      case '2x2':
        return 'grid-cols-1 md:grid-cols-2';
      case '3x3':
        return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
      default:
        return 'grid-cols-2';
    }
  };

  return (
    <div className="p-3 space-y-3 h-[calc(100vh-3.25rem)] flex flex-col">
      {/* Compact Top Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 rounded-md bg-[#09090b] border border-[#27272a] shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xs text-zinc-400 font-medium">Layout:</span>
          {(['1x1', '2x2', '3x3'] as GridLayout[]).map((l) => (
            <button
              key={l}
              onClick={() => setLayout(l)}
              className={`px-2.5 py-1 rounded text-xs transition-colors border ${
                layout === l
                  ? 'bg-white text-black border-white font-semibold'
                  : 'bg-[#18181b] text-zinc-300 border-[#27272a] hover:bg-zinc-800'
              }`}
            >
              {l}
            </button>
          ))}
        </div>

        {/* Sector Group & Overlay Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-zinc-400">Sector:</span>
            <select
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
              className="bg-[#18181b] border border-[#27272a] text-white rounded px-2.5 py-1 text-xs focus:outline-none"
            >
              {groups.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setShowOverlays(!showOverlays)}
            className={`px-2.5 py-1 rounded text-xs border flex items-center gap-1.5 transition-colors ${
              showOverlays
                ? 'bg-zinc-800 border-zinc-500 text-white font-semibold'
                : 'bg-[#18181b] border-[#27272a] text-zinc-400 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>AI HUD</span>
          </button>

          {onOpenPurgeModal && (
            <button
              onClick={onOpenPurgeModal}
              title="Purge / Remove All Tracked Objects"
              className="px-2.5 py-1 rounded text-xs border border-red-800/80 bg-red-950/40 hover:bg-red-900/60 text-red-300 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5 text-red-400" />
              <span>Purge Tracks</span>
            </button>
          )}
        </div>
      </div>

      {/* Camera Video Matrix */}
      <div className={`grid ${getGridClass()} gap-2.5 flex-1 min-h-0 overflow-y-auto`}>
        {filteredCameras.map((cam) => (
          <div
            key={cam.id}
            className="rounded-md bg-black border border-[#27272a] flex flex-col overflow-hidden relative group hover:border-zinc-500 transition-colors"
          >
            {/* Top Video Header */}
            <div className="px-2.5 py-1.5 bg-[#09090b]/95 backdrop-blur-sm border-b border-[#27272a] flex items-center justify-between z-10">
              <div className="flex items-center gap-2 truncate">
                <span className={`w-2 h-2 rounded-full ${cam.status === 'ONLINE' ? 'bg-white animate-pulse' : 'bg-zinc-600'}`} />
                <span className="text-xs font-medium text-white truncate">{cam.name}</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-zinc-400 font-mono">
                <span>{cam.current_fps || 25} FPS</span>
                <button
                  onClick={() => onSelectCamera(cam.id)}
                  title="View detailed camera feeds and rules"
                  className="text-zinc-400 hover:text-white p-0.5 rounded"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Live Video Feed (GPU-Accelerated & Background-Suspended) */}
            <div className="flex-1 bg-black relative flex items-center justify-center min-h-[220px] overflow-hidden [transform:translateZ(0)]">
              {isTabVisible ? (
                <img
                  src={`${API_BASE_URL}/api/v1/streams/${cam.id}/live.mjpg?annotated=${showOverlays}&fps=15`}
                  alt={cam.name}
                  className="w-full h-full object-contain [will-change:transform]"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    setTimeout(() => {
                      target.src = `${API_BASE_URL}/api/v1/streams/${cam.id}/live.mjpg?annotated=${showOverlays}&fps=15&t=${Date.now()}`;
                    }, 2000);
                  }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center gap-1.5 text-zinc-500 font-mono text-xs">
                  <CameraIcon className="w-5 h-5 text-zinc-600" />
                  <span>Stream Paused (Background)</span>
                </div>
              )}

              {/* Minimal bottom metadata bar */}
              <div className="absolute bottom-1.5 left-2 text-[10px] font-mono text-zinc-300 bg-black/80 px-1.5 py-0.5 rounded border border-white/10">
                {cam.location}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
