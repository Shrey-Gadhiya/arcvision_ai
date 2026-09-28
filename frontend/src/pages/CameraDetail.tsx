import React, { useState, useEffect, useCallback } from 'react';
import {
  Video, Shapes, RefreshCw, Layers, Trash2, ArrowLeft,
  ChevronUp, ChevronDown, ChevronLeft, ChevronRight,
  ZoomIn, ZoomOut, Square, Home, Wifi, WifiOff, Plus,
  Crosshair, RotateCcw, Bookmark, Shield, Eye, Navigation,
  UserCheck, Car, ScanFace, Plane, AlertTriangle, Users
} from 'lucide-react';
import { Camera, Zone, Tripwire, PTZStatus, PTZPreset } from '../types';
import { apiClient, API_BASE_URL } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

interface CameraDetailProps {
  cameraId: number;
  cameras: Camera[];
  onBack: () => void;
}

export const CameraDetail: React.FC<CameraDetailProps> = ({ cameraId, cameras, onBack }) => {
  const camera = cameras.find(c => c.id === cameraId) || cameras[0];
  const [zones, setZones] = useState<Zone[]>([]);
  const [tripwires, setTripwires] = useState<Tripwire[]>([]);
  const [showOverlays, setShowOverlays] = useState<boolean>(true);

  // Drawing state for new polygon zone
  const [isDrawingZone, setIsDrawingZone] = useState<boolean>(false);
  const [newZonePoints, setNewZonePoints] = useState<{ x: number; y: number }[]>([]);
  const [zoneName, setZoneName] = useState<string>('Restricted Buffer');
  const [zoneType, setZoneType] = useState<string>('RESTRICTED');
  const [loiterTime] = useState<number>(15);

  // Drawing state for tripwire
  const [isDrawingWire, setIsDrawingWire] = useState<boolean>(false);
  const [wirePoints, setWirePoints] = useState<{ x: number; y: number }[]>([]);
  const [wireName, setWireName] = useState<string>('Border Zero Line');
  const [wireDirection, setWireDirection] = useState<string>('BIDIRECTIONAL');

  // PTZ Control State
  const [ptzStatus, setPtzStatus] = useState<PTZStatus | null>(null);
  const [ptzPresets, setPtzPresets] = useState<PTZPreset[]>([]);
  const [ptzSpeed, setPtzSpeed] = useState<number>(0.5);
  const [newPresetName, setNewPresetName] = useState<string>('');
  const [showPtzPanel, setShowPtzPanel] = useState<boolean>(false);

  // Tactical AI Perception Matrix state
  const [featureToggles, setFeatureToggles] = useState({
    drone_detection_enabled: camera?.drone_detection_enabled ?? true,
    face_concealment_enabled: camera?.face_concealment_enabled ?? true,
    one_way_lane_enabled: camera?.one_way_lane_enabled ?? true,
    weapon_detection_enabled: camera?.weapon_detection_enabled ?? true,
    people_counting_enabled: camera?.people_counting_enabled ?? true,
    anpr_enabled: camera?.anpr_enabled ?? true,
    face_recognition_enabled: camera?.face_recognition_enabled ?? true,
    cross_camera_reid_enabled: camera?.cross_camera_reid_enabled ?? true,
    night_mode_enabled: camera?.night_mode_enabled ?? true
  });

  const handleToggleFeature = async (key: string, val: boolean) => {
    const updated = { ...featureToggles, [key]: val };
    setFeatureToggles(updated);
    try {
      await apiClient.put(`/cameras/${camera.id}`, { [key]: val });
    } catch (e) {
      console.error('Failed to update feature toggle:', e);
    }
  };

  const fetchZonesAndWires = async () => {
    if (!camera) return;
    try {
      const zRes = await apiClient.get(`/zones/camera/${camera.id}`);
      setZones(zRes.data);
      const twRes = await apiClient.get(`/zones/tripwires/camera/${camera.id}`);
      setTripwires(twRes.data);
    } catch (e) {
      // fallback
    }
  };

  const fetchPtzStatus = useCallback(async () => {
    if (!camera) return;
    try {
      const res = await apiClient.get(`/ptz/${camera.id}/status`);
      setPtzStatus(res.data);
    } catch (e) {
      setPtzStatus(null);
    }
  }, [camera?.id]);

  const fetchPtzPresets = useCallback(async () => {
    if (!camera) return;
    try {
      const res = await apiClient.get(`/ptz/${camera.id}/presets`);
      setPtzPresets(res.data);
    } catch (e) {
      setPtzPresets([]);
    }
  }, [camera?.id]);

  useEffect(() => {
    fetchZonesAndWires();
    fetchPtzStatus();
    fetchPtzPresets();
  }, [camera?.id]);

  // PTZ polling when panel is open
  useEffect(() => {
    if (!showPtzPanel) return;
    const interval = setInterval(fetchPtzStatus, 2000);
    return () => clearInterval(interval);
  }, [showPtzPanel, fetchPtzStatus]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

    if (isDrawingZone) {
      setNewZonePoints(prev => [...prev, { x, y }]);
    } else if (isDrawingWire) {
      if (wirePoints.length < 2) {
        setWirePoints(prev => [...prev, { x, y }]);
      }
    }
  };

  const handleSaveZone = async () => {
    if (newZonePoints.length < 3) {
      alert('A polygon zone requires at least 3 points.');
      return;
    }
    try {
      await apiClient.post('/zones/', {
        camera_id: camera.id,
        name: zoneName,
        zone_type: zoneType,
        points_json: JSON.stringify(newZonePoints),
        color_hex: '#ffffff',
        loitering_time_sec: loiterTime
      });
      setIsDrawingZone(false);
      setNewZonePoints([]);
      fetchZonesAndWires();
    } catch (e) {
      alert('Failed to save zone');
    }
  };

  const handleSaveWire = async () => {
    if (wirePoints.length !== 2) {
      alert('A tripwire line requires 2 points.');
      return;
    }
    try {
      await apiClient.post('/zones/tripwires', {
        camera_id: camera.id,
        name: wireName,
        line_json: JSON.stringify({
          start: wirePoints[0],
          end: wirePoints[1]
        }),
        direction: wireDirection,
        color_hex: '#ffffff'
      });
      setIsDrawingWire(false);
      setWirePoints([]);
      fetchZonesAndWires();
    } catch (e) {
      alert('Failed to save virtual fence');
    }
  };

  const handleDeleteZone = async (zoneId: number) => {
    try {
      await apiClient.delete(`/zones/${zoneId}`);
      fetchZonesAndWires();
    } catch (e) {
      alert('Failed to delete zone');
    }
  };

  const handleDeleteWire = async (wireId: number) => {
    try {
      await apiClient.delete(`/zones/tripwires/${wireId}`);
      fetchZonesAndWires();
    } catch (e) {
      alert('Failed to delete virtual fence');
    }
  };

  // ── PTZ Commands ──────────────────────────────────────────
  const ptzMove = async (panSpeed: number, tiltSpeed: number, zoomSpeed: number = 0) => {
    try {
      await apiClient.post(`/ptz/${camera.id}/move`, {
        pan_speed: panSpeed,
        tilt_speed: tiltSpeed,
        zoom_speed: zoomSpeed,
        speed: ptzSpeed
      });
      fetchPtzStatus();
    } catch (e) { /* handled by status */ }
  };

  const ptzStop = async () => {
    try {
      await apiClient.post(`/ptz/${camera.id}/stop`);
      fetchPtzStatus();
    } catch (e) { /* handled */ }
  };

  const ptzHome = async () => {
    try {
      await apiClient.post(`/ptz/${camera.id}/home`);
      fetchPtzStatus();
    } catch (e) { /* handled */ }
  };

  const ptzGotoPreset = async (presetToken: string) => {
    try {
      await apiClient.post(`/ptz/${camera.id}/presets/${presetToken}/goto`);
      fetchPtzStatus();
    } catch (e) { /* handled */ }
  };

  const ptzCreatePreset = async () => {
    if (!newPresetName.trim()) return;
    try {
      await apiClient.post(`/ptz/${camera.id}/presets`, { name: newPresetName.trim() });
      setNewPresetName('');
      fetchPtzPresets();
    } catch (e) {
      alert('Failed to save preset');
    }
  };

  const ptzDeletePreset = async (presetToken: string) => {
    try {
      await apiClient.delete(`/ptz/${camera.id}/presets/${presetToken}`);
      fetchPtzPresets();
    } catch (e) {
      alert('Failed to delete preset');
    }
  };

  const ptzTestConnection = async () => {
    try {
      await apiClient.post(`/ptz/${camera.id}/test`);
      fetchPtzStatus();
    } catch (e) { /* handled */ }
  };

  const ptzStatusColor = (status?: string) => {
    if (!status) return 'text-zinc-500';
    switch (status) {
      case 'CONNECTED': return 'text-emerald-400';
      case 'NOT_CONFIGURED': return 'text-zinc-500';
      case 'UNAVAILABLE': return 'text-amber-400';
      case 'ERROR': return 'text-red-400';
      default: return 'text-zinc-400';
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <div className="flex items-center gap-3">
          <Button variant="secondary" size="xs" icon={<ArrowLeft className="w-3.5 h-3.5" />} onClick={onBack}>
            Back
          </Button>

          <div className="h-5 w-px bg-zinc-800 hidden sm:block" />

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-semibold text-white">{camera?.name}</h1>
              <Badge variant={camera?.status === 'ONLINE' ? 'success' : 'critical'} dot>
                {camera?.status}
              </Badge>
              {camera?.ptz_enabled && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-zinc-800 text-white border border-zinc-700">
                  PTZ
                </span>
              )}
            </div>
            <div className="text-xs text-zinc-400 mt-0.5 font-sans">
              {camera?.location} &bull; {camera?.group_name} &bull; {camera?.stream_type}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant={showPtzPanel ? 'primary' : 'secondary'}
            size="xs"
            icon={<Crosshair className="w-3.5 h-3.5" />}
            onClick={() => setShowPtzPanel(!showPtzPanel)}
          >
            PTZ Control
          </Button>
          <Button
            variant={showOverlays ? 'primary' : 'secondary'}
            size="xs"
            icon={<Layers className="w-3.5 h-3.5" />}
            onClick={() => setShowOverlays(!showOverlays)}
          >
            HUD Overlay
          </Button>
          <Button variant="secondary" size="xs" icon={<RefreshCw className="w-3 h-3" />} onClick={fetchZonesAndWires}>
            Reload
          </Button>
        </div>
      </div>

      {/* Main Grid: Video Canvas on Left (8 Cols) | Config & Zones on Right (4 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left 8 Cols: Video Viewport & Interactive Drawing Canvas */}
        <div className="lg:col-span-8 bg-zinc-950 border border-zinc-800 rounded-md flex flex-col overflow-hidden">
          <div className="px-3.5 py-2 border-b border-zinc-800 flex items-center justify-between text-xs text-zinc-300">
            <div className="flex items-center gap-2 font-medium">
              <Video className="w-4 h-4 text-white" />
              <span>Sensor Viewport</span>
            </div>
            {ptzStatus?.is_moving && (
              <span className="text-white font-medium text-[11px] animate-pulse flex items-center gap-1">
                <RotateCcw className="w-3 h-3 animate-spin" />
                PTZ MOVING
              </span>
            )}
            {(isDrawingZone || isDrawingWire) && (
              <span className="text-white font-medium text-[11px] animate-pulse">
                Click video to place {isDrawingZone ? `polygon points (${newZonePoints.length})` : `fence points (${wirePoints.length}/2)`}
              </span>
            )}
          </div>

          <div
            onClick={handleCanvasClick}
            className={`flex-1 bg-black relative flex items-center justify-center min-h-[440px] select-none ${
              isDrawingZone || isDrawingWire ? 'cursor-crosshair' : 'cursor-default'
            }`}
          >
            <img
              src={`${API_BASE_URL}/api/v1/streams/${camera.id}/live.mjpg?annotated=${showOverlays}&fps=20`}
              alt={camera.name}
              className="w-full h-full object-contain pointer-events-none"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                setTimeout(() => {
                  target.src = `${API_BASE_URL}/api/v1/streams/${camera.id}/live.mjpg?annotated=${showOverlays}&fps=20&t=${Date.now()}`;
                }, 2000);
              }}
            />

            {/* SVG Interactive Overlay for drawing points */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              {/* Active Polygon in Progress */}
              {isDrawingZone && newZonePoints.length > 0 && (
                <>
                  <polygon
                    points={newZonePoints.map(p => `${p.x * 100}%,${p.y * 100}%`).join(' ')}
                    fill="rgba(255, 255, 255, 0.15)"
                    stroke="#ffffff"
                    strokeWidth="2"
                    strokeDasharray="4 2"
                  />
                  {newZonePoints.map((p, idx) => (
                    <circle
                      key={idx}
                      cx={`${p.x * 100}%`}
                      cy={`${p.y * 100}%`}
                      r="4"
                      fill="#ffffff"
                      stroke="#000000"
                      strokeWidth="1.5"
                    />
                  ))}
                </>
              )}

              {/* Active Tripwire in Progress */}
              {isDrawingWire && wirePoints.length > 0 && (
                <>
                  {wirePoints.length === 2 && (
                    <line
                      x1={`${wirePoints[0].x * 100}%`}
                      y1={`${wirePoints[0].y * 100}%`}
                      x2={`${wirePoints[1].x * 100}%`}
                      y2={`${wirePoints[1].y * 100}%`}
                      stroke="#ffffff"
                      strokeWidth="2"
                      strokeDasharray="4 2"
                    />
                  )}
                  {wirePoints.map((p, idx) => (
                    <circle
                      key={idx}
                      cx={`${p.x * 100}%`}
                      cy={`${p.y * 100}%`}
                      r="4"
                      fill="#ffffff"
                      stroke="#000000"
                      strokeWidth="1.5"
                    />
                  ))}
                </>
              )}
            </svg>

            {/* PTZ Position Overlay */}
            {showPtzPanel && ptzStatus && (
              <div className="absolute bottom-2 left-2 px-2 py-1 rounded bg-black/80 border border-zinc-800 text-[10px] font-mono text-zinc-300">
                P:{ptzStatus.pan.toFixed(2)} T:{ptzStatus.tilt.toFixed(2)} Z:{ptzStatus.zoom.toFixed(1)}
              </div>
            )}
          </div>

          {/* Drawing Action Bar */}
          {(isDrawingZone || isDrawingWire) && (
            <div className="p-3 bg-zinc-900 border-t border-zinc-800 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                {isDrawingZone ? (
                  <>
                    <input
                      type="text"
                      value={zoneName}
                      onChange={(e) => setZoneName(e.target.value)}
                      placeholder="Zone Name"
                      className="bg-black border border-zinc-800 rounded px-2 py-1 text-white"
                    />
                    <select
                      value={zoneType}
                      onChange={(e) => setZoneType(e.target.value)}
                      className="bg-black border border-zinc-800 rounded px-2 py-1 text-white"
                    >
                      <option value="RESTRICTED">Restricted</option>
                      <option value="BUFFER">Buffer</option>
                      <option value="EXCLUSION">Exclusion</option>
                    </select>
                  </>
                ) : (
                  <>
                    <input
                      type="text"
                      value={wireName}
                      onChange={(e) => setWireName(e.target.value)}
                      placeholder="Fence Line Name"
                      className="bg-black border border-zinc-800 rounded px-2 py-1 text-white"
                    />
                    <select
                      value={wireDirection}
                      onChange={(e) => setWireDirection(e.target.value)}
                      className="bg-black border border-zinc-800 rounded px-2 py-1 text-white"
                    >
                      <option value="BIDIRECTIONAL">Bidirectional</option>
                      <option value="A_TO_B">Ingress (A to B)</option>
                      <option value="B_TO_A">Egress (B to A)</option>
                    </select>
                  </>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={() => {
                    setIsDrawingZone(false);
                    setIsDrawingWire(false);
                    setNewZonePoints([]);
                    setWirePoints([]);
                  }}
                  className="text-zinc-400 hover:text-white"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="xs"
                  onClick={isDrawingZone ? handleSaveZone : handleSaveWire}
                >
                  Save Definition
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Right 4 Cols: Active Zones & Fences List + PTZ Panel */}
        <div className="lg:col-span-4 space-y-4">

          {/* ── PTZ Control Panel ────────────────────────────── */}
          {showPtzPanel && (
            <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
                <h3 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Crosshair className="w-3.5 h-3.5" />
                  PTZ CAMERA CONTROL
                </h3>
                <div className="flex items-center gap-1.5">
                  {ptzStatus?.status === 'CONNECTED' ? (
                    <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <WifiOff className="w-3.5 h-3.5 text-zinc-500" />
                  )}
                  <span className={`text-[10px] font-bold ${ptzStatusColor(ptzStatus?.status)}`}>
                    {ptzStatus?.status || 'LOADING'}
                  </span>
                </div>
              </div>

              {/* ONVIF Connection Info */}
              <div className="p-2 rounded bg-black border border-zinc-800 text-[11px]">
                <div className="flex justify-between text-zinc-400">
                  <span>ONVIF HOST</span>
                  <span className="text-zinc-200 font-mono">{ptzStatus?.onvif_host || 'NOT_CONFIGURED'}</span>
                </div>
                <div className="flex justify-between text-zinc-400 mt-1">
                  <span>ONVIF PORT</span>
                  <span className="text-zinc-200 font-mono">{ptzStatus?.onvif_port || 80}</span>
                </div>
                {ptzStatus?.last_action && (
                  <div className="flex justify-between text-zinc-400 mt-1">
                    <span>LAST CMD</span>
                    <span className="text-zinc-300 font-mono text-[10px] truncate max-w-[140px]">{ptzStatus.last_action}</span>
                  </div>
                )}
                {ptzStatus?.error_message && (
                  <div className="mt-1 text-red-400 text-[10px]">{ptzStatus.error_message}</div>
                )}
              </div>

              {/* D-Pad Joystick */}
              <div className="flex flex-col items-center gap-1">
                <span className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">DIRECTIONAL CONTROL</span>
                <div className="grid grid-cols-3 gap-1 w-fit">
                  <div />
                  <button
                    onMouseDown={() => ptzMove(0, 1)}
                    onMouseUp={ptzStop}
                    onMouseLeave={ptzStop}
                    className="w-10 h-10 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center hover:bg-zinc-800 hover:border-zinc-600 active:bg-white active:text-black transition-all"
                  >
                    <ChevronUp className="w-5 h-5" />
                  </button>
                  <div />

                  <button
                    onMouseDown={() => ptzMove(-1, 0)}
                    onMouseUp={ptzStop}
                    onMouseLeave={ptzStop}
                    className="w-10 h-10 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center hover:bg-zinc-800 hover:border-zinc-600 active:bg-white active:text-black transition-all"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <button
                    onClick={ptzStop}
                    className="w-10 h-10 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center hover:bg-red-950 hover:border-red-800 active:bg-red-500 active:text-black transition-all"
                  >
                    <Square className="w-4 h-4" />
                  </button>
                  <button
                    onMouseDown={() => ptzMove(1, 0)}
                    onMouseUp={ptzStop}
                    onMouseLeave={ptzStop}
                    className="w-10 h-10 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center hover:bg-zinc-800 hover:border-zinc-600 active:bg-white active:text-black transition-all"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>

                  <div />
                  <button
                    onMouseDown={() => ptzMove(0, -1)}
                    onMouseUp={ptzStop}
                    onMouseLeave={ptzStop}
                    className="w-10 h-10 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center hover:bg-zinc-800 hover:border-zinc-600 active:bg-white active:text-black transition-all"
                  >
                    <ChevronDown className="w-5 h-5" />
                  </button>
                  <div />
                </div>
              </div>

              {/* Zoom + Speed Row */}
              <div className="flex items-center gap-2">
                <button
                  onMouseDown={() => ptzMove(0, 0, -1)}
                  onMouseUp={ptzStop}
                  onMouseLeave={ptzStop}
                  className="flex-1 py-1.5 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center gap-1 text-xs hover:bg-zinc-800 active:bg-white active:text-black transition-all"
                >
                  <ZoomOut className="w-3.5 h-3.5" /> OUT
                </button>
                <button
                  onMouseDown={() => ptzMove(0, 0, 1)}
                  onMouseUp={ptzStop}
                  onMouseLeave={ptzStop}
                  className="flex-1 py-1.5 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center gap-1 text-xs hover:bg-zinc-800 active:bg-white active:text-black transition-all"
                >
                  <ZoomIn className="w-3.5 h-3.5" /> IN
                </button>
              </div>

              {/* Speed Slider */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-[10px] text-zinc-400">
                  <span>SPEED</span>
                  <span className="font-mono text-zinc-200">{ptzSpeed.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.1"
                  value={ptzSpeed}
                  onChange={(e) => setPtzSpeed(parseFloat(e.target.value))}
                  className="w-full h-1 accent-white bg-zinc-800 rounded-full appearance-none cursor-pointer"
                />
              </div>

              {/* Home + Test */}
              <div className="flex items-center gap-2">
                <button
                  onClick={ptzHome}
                  className="flex-1 py-1.5 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center gap-1 text-xs hover:bg-zinc-800 active:bg-white active:text-black transition-all"
                >
                  <Home className="w-3.5 h-3.5" /> HOME
                </button>
                <button
                  onClick={ptzTestConnection}
                  className="flex-1 py-1.5 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center gap-1 text-xs hover:bg-zinc-800 active:bg-white active:text-black transition-all"
                >
                  <Wifi className="w-3.5 h-3.5" /> TEST
                </button>
              </div>

              {/* PTZ Presets */}
              <div className="border-t border-zinc-800 pt-2 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-zinc-500 uppercase tracking-wider flex items-center gap-1">
                    <Bookmark className="w-3 h-3" /> SAVED PRESETS
                  </span>
                  <span className="text-[10px] text-zinc-600 font-mono">{ptzPresets.length}</span>
                </div>

                <div className="space-y-1.5 max-h-[120px] overflow-y-auto">
                  {ptzPresets.length === 0 ? (
                    <div className="text-[11px] text-zinc-500 py-2 text-center">No presets saved</div>
                  ) : (
                    ptzPresets.map((p) => (
                      <div key={p.id} className="flex items-center justify-between p-1.5 rounded bg-black border border-zinc-800 text-[11px]">
                        <button
                          onClick={() => ptzGotoPreset(p.preset_token)}
                          className="flex-1 text-left text-zinc-200 hover:text-white transition-colors font-medium truncate"
                        >
                          {p.name}
                        </button>
                        <div className="flex items-center gap-1 shrink-0 ml-2">
                          <span className="text-[9px] text-zinc-600 font-mono">
                            {p.pan.toFixed(1)}/{p.tilt.toFixed(1)}/{p.zoom.toFixed(1)}
                          </span>
                          <button
                            onClick={() => ptzDeletePreset(p.preset_token)}
                            className="p-0.5 text-zinc-600 hover:text-red-400"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Create Preset */}
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    value={newPresetName}
                    onChange={(e) => setNewPresetName(e.target.value)}
                    placeholder="Preset name..."
                    className="flex-1 bg-black border border-zinc-800 rounded px-2 py-1 text-[11px] text-white placeholder:text-zinc-600"
                    onKeyDown={(e) => e.key === 'Enter' && ptzCreatePreset()}
                  />
                  <button
                    onClick={ptzCreatePreset}
                    disabled={!newPresetName.trim()}
                    className="p-1.5 rounded bg-zinc-900 border border-zinc-700 text-zinc-300 hover:bg-white hover:text-black disabled:opacity-30 disabled:pointer-events-none transition-all"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Action Card to start drawing */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-2">
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Spatial Perimeter Tools
            </h3>
            <p className="text-xs text-zinc-400">
              Draw virtual security boundaries directly on this camera feed.
            </p>
            <div className="flex gap-2 pt-1">
              <Button
                variant={isDrawingZone ? 'primary' : 'secondary'}
                size="xs"
                className="flex-1"
                icon={<Shapes className="w-3.5 h-3.5" />}
                onClick={() => {
                  setIsDrawingWire(false);
                  setIsDrawingZone(true);
                  setNewZonePoints([]);
                }}
              >
                + Polygon Zone
              </Button>
              <Button
                variant={isDrawingWire ? 'primary' : 'secondary'}
                size="xs"
                className="flex-1"
                icon={<Layers className="w-3.5 h-3.5" />}
                onClick={() => {
                  setIsDrawingZone(false);
                  setIsDrawingWire(true);
                  setWirePoints([]);
                }}
              >
                + Virtual Fence
              </Button>
            </div>
          </div>

          {/* Tactical AI Perception Matrix & Feature Toggles */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
              <span className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-white" />
                Tactical AI Perception Matrix
              </span>
              <Badge variant="success">Active</Badge>
            </div>

            <div className="grid grid-cols-1 gap-2 text-xs">
              {[
                { key: 'drone_detection_enabled', label: 'SkyShield Drone & UAV Threat Detection', desc: 'Neural aerial radar & trajectory classifier for low-altitude drones', icon: Plane },
                { key: 'face_concealment_enabled', label: 'Facial Concealment & Masking Alert', desc: 'Alerts when subjects hide face via balaclavas, masks, or deep hoods', icon: AlertTriangle },
                { key: 'one_way_lane_enabled', label: 'One-Way Lane & Wrong-Way Driving', desc: 'Flags vehicles travelling against authorized lane traffic direction', icon: Navigation },
                { key: 'weapon_detection_enabled', label: 'Firearms, Knives & Dangerous Objects', desc: 'Neural detection of handguns, rifles, blades, and suspicious parcels', icon: Shield },
                { key: 'people_counting_enabled', label: 'Bidirectional People & Vehicle Counting', desc: 'Real-time entry/exit accumulator and occupancy tracking HUD', icon: Users },
                { key: 'anpr_enabled', label: 'Automated ANPR License Plate Capture', desc: 'Real-time vehicle license plate OCR and hotlist matching', icon: Car },
                { key: 'face_recognition_enabled', label: 'YuNet + SFace Biometric Watchlist Matching', desc: '128-D facial feature embeddings and wanted person instant alerts', icon: ScanFace },
                { key: 'cross_camera_reid_enabled', label: 'Cross-Camera Re-ID & Journey Tracking', desc: 'Fuses multi-camera sensor observations into unified target paths', icon: Eye }
              ].map((feat) => {
                const Icon = feat.icon;
                const isEnabled = (featureToggles as any)[feat.key] ?? true;
                return (
                  <div
                    key={feat.key}
                    onClick={() => handleToggleFeature(feat.key, !isEnabled)}
                    className={`p-2.5 rounded border flex items-start justify-between gap-2 cursor-pointer transition-colors ${
                      isEnabled ? 'bg-zinc-900 border-zinc-700' : 'bg-black border-zinc-800 opacity-60'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${isEnabled ? 'text-white' : 'text-zinc-500'}`} />
                      <div>
                        <div className={`font-medium text-xs ${isEnabled ? 'text-white' : 'text-zinc-400'}`}>
                          {feat.label}
                        </div>
                        <div className="text-[10px] text-zinc-400 mt-0.5">{feat.desc}</div>
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={isEnabled}
                      onChange={() => {}}
                      className="w-3.5 h-3.5 rounded text-white bg-black border-zinc-700 accent-white shrink-0 mt-1 cursor-pointer"
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Zones List */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
              <span className="text-xs font-semibold text-white uppercase tracking-wider">
                Active Zones ({zones.length})
              </span>
            </div>

            <div className="space-y-2 max-h-[180px] overflow-y-auto">
              {zones.length === 0 ? (
                <div className="text-xs text-zinc-500 py-3 text-center">
                  No polygon zones defined.
                </div>
              ) : (
                zones.map((z) => (
                  <div
                    key={z.id}
                    className="p-2.5 rounded bg-zinc-900 border border-zinc-800 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-1.5 font-medium text-white">
                        <span className="w-2 h-2 rounded-full bg-white" />
                        <span>{z.name}</span>
                      </div>
                      <div className="text-[11px] text-zinc-400 font-mono mt-0.5">
                        {z.zone_type} &bull; Loiter {z.loitering_time_sec}s
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteZone(z.id)}
                      className="p-1 rounded text-zinc-400 hover:text-white"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Tripwires List */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
              <span className="text-xs font-semibold text-white uppercase tracking-wider">
                Virtual Tripwires ({tripwires.length})
              </span>
            </div>

            <div className="space-y-2 max-h-[180px] overflow-y-auto">
              {tripwires.length === 0 ? (
                <div className="text-xs text-zinc-500 py-3 text-center">
                  No virtual fence lines defined.
                </div>
              ) : (
                tripwires.map((tw) => (
                  <div
                    key={tw.id}
                    className="p-2.5 rounded bg-zinc-900 border border-zinc-800 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-1.5 font-medium text-white">
                        <span className="w-2 h-2 rounded-full bg-zinc-400" />
                        <span>{tw.name}</span>
                      </div>
                      <div className="text-[11px] text-zinc-400 font-mono mt-0.5">
                        {tw.direction}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteWire(tw.id)}
                      className="p-1 rounded text-zinc-400 hover:text-white"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
