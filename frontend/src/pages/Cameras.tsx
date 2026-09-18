import React, { useState } from 'react';
import { Camera as CameraIcon, Plus, RefreshCw, Trash2, Eye, Map, List, Compass, RotateCcw, AlertTriangle, Loader2 } from 'lucide-react';
import { Camera } from '../types';
import { apiClient } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { AddCameraWizard } from '../components/cameras/AddCameraWizard';

interface CamerasProps {
  cameras: Camera[];
  onRefresh: () => void;
  onSelectCamera: (camId: number) => void;
}

export const Cameras: React.FC<CamerasProps> = ({ cameras, onRefresh, onSelectCamera }) => {
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');
  const [selectedCam, setSelectedCam] = useState<Camera | null>(cameras[0] || null);
  const [showAddWizard, setShowAddWizard] = useState<boolean>(false);
  const [cameraToDelete, setCameraToDelete] = useState<Camera | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [restartCamId, setRestartCamId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleRestart = async (camId: number) => {
    try {
      setRestartCamId(camId);
      await apiClient.post(`/cameras/${camId}/restart`);
      onRefresh();
    } catch (e) {
      alert('Failed to restart camera process');
    } finally {
      setRestartCamId(null);
    }
  };

  const handleDeleteClick = (cam: Camera) => {
    setErrorMessage(null);
    setCameraToDelete(cam);
  };

  const handleConfirmDelete = async () => {
    if (!cameraToDelete) return;
    setIsDeleting(true);
    setErrorMessage(null);
    try {
      await apiClient.delete(`/cameras/${cameraToDelete.id}`);
      if (selectedCam?.id === cameraToDelete.id) {
        setSelectedCam(cameras.find(c => c.id !== cameraToDelete.id) || null);
      }
      setCameraToDelete(null);
      onRefresh();
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Failed to delete camera';
      setErrorMessage(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Top Header & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#09090b] border border-[#27272a] rounded-md px-4 py-3">
        <div>
          <h1 className="text-sm font-semibold text-white uppercase tracking-wide">
            Camera Fleet & Sensor Grid
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Configure surveillance cameras, RTSP ingestion parameters, and spatial orientations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-[#18181b] border border-[#27272a] rounded p-0.5">
            <button
              onClick={() => setViewMode('list')}
              className={`px-2.5 py-1 rounded text-xs flex items-center gap-1.5 transition-colors ${
                viewMode === 'list'
                  ? 'bg-white text-black font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <List className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
            <button
              onClick={() => setViewMode('map')}
              className={`px-2.5 py-1 rounded text-xs flex items-center gap-1.5 transition-colors ${
                viewMode === 'map'
                  ? 'bg-white text-black font-semibold'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Map className="w-3.5 h-3.5" />
              <span>Map (GIS)</span>
            </button>
          </div>

          <Button variant="secondary" size="sm" icon={<RefreshCw className="w-3 h-3" />} onClick={onRefresh}>
            Refresh
          </Button>

          <Button variant="primary" size="sm" icon={<Plus className="w-3.5 h-3.5" />} onClick={() => setShowAddWizard(true)}>
            Add Camera
          </Button>
        </div>
      </div>

      {viewMode === 'list' ? (
        /* VMS Fleet Table */
        <div className="bg-[#09090b] border border-[#27272a] rounded-md overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#121215] text-zinc-400 border-b border-[#27272a] font-semibold text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="p-3">STATUS</th>
                  <th className="p-3">NAME</th>
                  <th className="p-3">LOCATION</th>
                  <th className="p-3">SOURCE</th>
                  <th className="p-3">FPS</th>
                  <th className="p-3">RESOLUTION</th>
                  <th className="p-3">LATENCY</th>
                  <th className="p-3 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1c1c20] text-zinc-300">
                {cameras.map((cam) => (
                  <tr key={cam.id} className="hover:bg-[#18181b]/60 transition-colors">
                    <td className="p-3">
                      <Badge variant={cam.status === 'ONLINE' ? 'success' : 'critical'} dot>
                        {cam.status}
                      </Badge>
                    </td>
                    <td className="p-3 font-medium text-white">
                      <div>{cam.name}</div>
                      <div className="text-[11px] text-zinc-400 font-mono">{cam.group_name}</div>
                    </td>
                    <td className="p-3 text-zinc-200 font-sans">
                      {cam.location}
                    </td>
                    <td className="p-3 font-mono text-[11px] text-zinc-400">
                      {cam.stream_type}
                    </td>
                    <td className="p-3 font-mono text-white">
                      {cam.current_fps || 25}
                    </td>
                    <td className="p-3 font-mono text-zinc-400">
                      1280x720
                    </td>
                    <td className="p-3 font-mono text-zinc-400">
                      {cam.latency_ms || 24} ms
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => onSelectCamera(cam.id)}
                          className="px-2 py-1 rounded bg-[#18181b] hover:bg-zinc-800 text-white text-xs border border-[#27272a]"
                        >
                          View
                        </button>
                        <button
                          onClick={() => handleRestart(cam.id)}
                          disabled={restartCamId === cam.id}
                          title="Restart Camera Stream"
                          className="p-1 rounded text-zinc-400 hover:text-white hover:bg-[#18181b] disabled:opacity-50"
                        >
                          <RotateCcw className={`w-3.5 h-3.5 ${restartCamId === cam.id ? 'animate-spin' : ''}`} />
                        </button>
                        <button
                          onClick={() => handleDeleteClick(cam)}
                          title="Delete Camera"
                          className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* GIS Tactical Radar Canvas */
        <div className="bg-[#09090b] border border-[#27272a] rounded-md p-3">
          <div className="relative aspect-[16/9] max-h-[540px] bg-[#000000] rounded border border-[#27272a] overflow-hidden flex items-center justify-center select-none">
            {/* Compass */}
            <div className="absolute top-3 right-3 text-zinc-500 flex flex-col items-center">
              <Compass className="w-6 h-6 text-zinc-400" />
              <span className="text-[9px] font-bold text-zinc-400">N</span>
            </div>

            {/* Zero Line */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              <path
                d="M 50 280 Q 300 240 600 300 T 1100 250"
                fill="none"
                stroke="#a1a1aa"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />
              <text x="60" y="270" fill="#a1a1aa" fontSize="10" fontFamily="sans-serif">
                INTERNATIONAL BORDER ZERO LINE
              </text>
            </svg>

            {/* Camera Nodes */}
            <div className="relative w-full h-full">
              {cameras.map((cam, idx) => {
                const posX = 15 + (idx * 18);
                const posY = 35 + (idx % 2 === 0 ? 15 : -10);
                const isSel = selectedCam?.id === cam.id;
                return (
                  <div
                    key={cam.id}
                    onClick={() => setSelectedCam(cam)}
                    style={{ left: `${posX}%`, top: `${posY}%` }}
                    className="absolute cursor-pointer -translate-x-1/2 -translate-y-1/2 group"
                  >
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center border transition-all ${
                        isSel
                          ? 'bg-white text-black border-white scale-110 shadow-sm'
                          : 'bg-[#18181b] text-zinc-300 border-[#27272a] hover:border-zinc-500'
                      }`}
                    >
                      <CameraIcon className="w-3.5 h-3.5" />
                    </div>
                    <div className="absolute top-8 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-medium bg-[#09090b] px-1.5 py-0.5 rounded border border-[#27272a] text-zinc-200">
                      {cam.name}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selected Camera Details Bar */}
          {selectedCam && (
            <div className="mt-3 p-3 bg-[#18181b] border border-[#27272a] rounded flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-white">{selectedCam.name}</span>
                <span className="text-xs text-zinc-400 ml-2 font-mono">{selectedCam.location}</span>
                <span className="text-[11px] text-zinc-400 ml-2 font-mono">({selectedCam.stream_type})</span>
              </div>
              <div className="flex items-center gap-2">
                <Button size="xs" variant="secondary" icon={<Trash2 className="w-3 h-3" />} onClick={() => handleDeleteClick(selectedCam)}>
                  Delete
                </Button>
                <Button size="xs" variant="primary" onClick={() => onSelectCamera(selectedCam.id)}>
                  Open Diagnostics
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {cameraToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#09090b] border border-[#27272a] rounded-lg max-w-md w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-[#18181b] border border-[#27272a] rounded text-white flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-white uppercase tracking-wide">
                  Decommission Camera
                </h3>
                <p className="text-xs text-zinc-400 mt-1">
                  Are you sure you want to permanently decommission{' '}
                  <span className="font-semibold text-white font-mono">{cameraToDelete.name}</span>?
                </p>
              </div>
            </div>

            <div className="bg-[#121215] border border-[#27272a] rounded p-3 text-xs space-y-1.5 font-mono text-zinc-400">
              <div className="flex justify-between">
                <span>Location:</span>
                <span className="text-white">{cameraToDelete.location || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span>Stream Type:</span>
                <span className="text-white">{cameraToDelete.stream_type}</span>
              </div>
              <div className="flex justify-between">
                <span>RTSP Source:</span>
                <span className="text-white truncate max-w-[200px]" title={cameraToDelete.rtsp_url}>
                  {cameraToDelete.rtsp_url}
                </span>
              </div>
            </div>

            {errorMessage && (
              <div className="p-2.5 bg-black border border-white text-white text-xs rounded">
                {errorMessage}
              </div>
            )}

            <p className="text-[11px] text-zinc-400">
              This action terminates active ingestion pipelines and deletes historical detections and logs for this camera.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#27272a]">
              <button
                type="button"
                onClick={() => {
                  if (!isDeleting) {
                    setCameraToDelete(null);
                    setErrorMessage(null);
                  }
                }}
                disabled={isDeleting}
                className="px-3 py-1.5 rounded bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-xs font-medium text-zinc-300 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="px-3 py-1.5 rounded bg-white text-black hover:bg-zinc-200 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Confirm Decommission</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Camera Wizard Modal */}
      <AddCameraWizard
        isOpen={showAddWizard}
        onClose={() => setShowAddWizard(false)}
        onCameraAdded={() => onRefresh()}
      />
    </div>
  );
};
