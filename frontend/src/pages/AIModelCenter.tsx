import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Activity,
  Layers,
  RefreshCw,
  Power,
  Shield,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Play,
  Flame,
  UserCheck,
  Users,
  Eye,
  SlidersHorizontal,
  Info
} from 'lucide-react';
import { AIModel, CameraAIProfile, PerceptionTelemetry, Camera } from '../types';
import { apiClient } from '../api/client';

export const AIModelCenter: React.FC = () => {
  const [models, setModels] = useState<AIModel[]>([]);
  const [telemetry, setTelemetry] = useState<PerceptionTelemetry | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [profiles, setProfiles] = useState<CameraAIProfile[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<number>(1);
  const [activeProfile, setActiveProfile] = useState<CameraAIProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [savingProfile, setSavingProfile] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'models' | 'profiles' | 'diagnostics'>('models');
  
  // Simulator State
  const [simType, setSimType] = useState<string>('FALL_DETECTED');
  const [simResult, setSimResult] = useState<any>(null);
  const [simulating, setSimulating] = useState<boolean>(false);

  const currentUserRole = localStorage.getItem('arc_role') || 'VIEWER';
  const isOperatorOrAdmin = ['ADMIN', 'OPERATOR'].includes(currentUserRole);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [modelsRes, telemRes, camsRes, profsRes] = await Promise.all([
        apiClient.get('/models/'),
        apiClient.get('/models/telemetry'),
        apiClient.get('/cameras/'),
        apiClient.get('/models/camera-profiles')
      ]);
      setModels(modelsRes.data);
      setTelemetry(telemRes.data);
      setCameras(camsRes.data);
      setProfiles(profsRes.data);

      if (camsRes.data.length > 0 && !selectedCameraId) {
        setSelectedCameraId(camsRes.data[0].id);
      }
    } catch (e: any) {
      console.error('Failed to fetch AI perception data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(async () => {
      try {
        const telem = await apiClient.get('/models/telemetry');
        setTelemetry(telem.data);
      } catch (e) {}
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const prof = profiles.find((p) => p.camera_id === selectedCameraId);
    if (prof) {
      setActiveProfile({ ...prof });
    } else if (selectedCameraId) {
      // Fetch single
      apiClient.get(`/models/camera-profiles/${selectedCameraId}`).then((res) => {
        setActiveProfile(res.data);
      }).catch(() => {});
    }
  }, [selectedCameraId, profiles]);

  const handleReloadModel = async (modelId: number) => {
    if (!isOperatorOrAdmin) return;
    try {
      setStatusMsg(`Reloading model #${modelId}...`);
      await apiClient.post(`/models/${modelId}/reload`);
      setStatusMsg(`Model reloaded successfully`);
      fetchData();
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e: any) {
      setStatusMsg(`Error reloading model: ${e.response?.data?.detail || e.message}`);
      setTimeout(() => setStatusMsg(null), 4000);
    }
  };

  const handleUnloadModel = async (modelId: number) => {
    if (!isOperatorOrAdmin) return;
    try {
      setStatusMsg(`Unloading model #${modelId}...`);
      await apiClient.post(`/models/${modelId}/unload`);
      setStatusMsg(`Model unloaded to standby`);
      fetchData();
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e: any) {
      setStatusMsg(`Error unloading model: ${e.response?.data?.detail || e.message}`);
      setTimeout(() => setStatusMsg(null), 4000);
    }
  };

  const handleSaveProfile = async () => {
    if (!activeProfile || !isOperatorOrAdmin) return;
    try {
      setSavingProfile(true);
      const res = await apiClient.put(`/models/camera-profiles/${selectedCameraId}`, activeProfile);
      setActiveProfile(res.data);
      setStatusMsg(`Camera #${selectedCameraId} AI profile saved`);
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e: any) {
      setStatusMsg(`Save error: ${e.response?.data?.detail || e.message}`);
      setTimeout(() => setStatusMsg(null), 4000);
    } finally {
      setSavingProfile(false);
    }
  };

  const handleRunSimulation = async () => {
    try {
      setSimulating(true);
      setSimResult(null);
      const res = await apiClient.post('/models/simulate-perception', {
        event_type: simType,
        camera_id: selectedCameraId
      });
      setSimResult(res.data);
    } catch (e: any) {
      setSimResult({ error: e.response?.data?.detail || e.message });
    } finally {
      setSimulating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
      case 'LOADED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            ACTIVE
          </span>
        );
      case 'STANDBY':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-950/60 text-amber-300 border border-amber-800/60">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            STANDBY
          </span>
        );
      case 'MODEL_REQUIRED':
      case 'NOT_CONFIGURED':
      case 'NOT_INSTALLED':
      case 'UNAVAILABLE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-medium bg-zinc-900 text-zinc-400 border border-zinc-700">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
            NOT CONFIGURED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-medium bg-rose-950/80 text-rose-400 border border-rose-800">
            ERROR
          </span>
        );
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto text-zinc-100 select-none">
      {/* Header & Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
              <Cpu className="w-6 h-6 text-zinc-100" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-wider uppercase">AI Perception & Model Center</h1>
              <p className="text-xs text-zinc-400">Multi-Model AI Adapters, Task Scheduling, and Per-Camera Profiles</p>
            </div>
          </div>
        </div>

        {/* Global Action Bar */}
        <div className="flex items-center gap-3">
          <div className="flex bg-zinc-900 border border-zinc-800 rounded p-1">
            <button
              onClick={() => setActiveTab('models')}
              className={`px-3 py-1.5 text-xs font-mono rounded transition-colors ${
                activeTab === 'models' ? 'bg-zinc-800 text-white font-semibold' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Models & Adapters
            </button>
            <button
              onClick={() => setActiveTab('profiles')}
              className={`px-3 py-1.5 text-xs font-mono rounded transition-colors ${
                activeTab === 'profiles' ? 'bg-zinc-800 text-white font-semibold' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Camera AI Profiles
            </button>
            <button
              onClick={() => setActiveTab('diagnostics')}
              className={`px-3 py-1.5 text-xs font-mono rounded transition-colors ${
                activeTab === 'diagnostics' ? 'bg-zinc-800 text-white font-semibold' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Diagnostics & Sim
            </button>
          </div>
          <button
            onClick={fetchData}
            className="p-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded text-zinc-300 transition-colors"
            title="Refresh All Data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {statusMsg && (
        <div className="p-3 bg-zinc-900 border border-zinc-700 text-zinc-200 text-xs font-mono rounded flex items-center justify-between">
          <span>{statusMsg}</span>
          <button onClick={() => setStatusMsg(null)} className="text-zinc-500 hover:text-zinc-300">✕</button>
        </div>
      )}

      {/* Runtime Telemetry Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-lg">
          <div className="flex items-center justify-between text-zinc-400 text-xs mb-1">
            <span>CPU UTILIZATION</span>
            <Activity className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-white">
            {telemetry?.system_cpu_utilization_pct?.toFixed(1) || '0.0'}%
          </div>
          <div className="text-[10px] text-zinc-500 font-mono mt-1">Host process load</div>
        </div>

        <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-lg">
          <div className="flex items-center justify-between text-zinc-400 text-xs mb-1">
            <span>SYSTEM MEMORY</span>
            <Layers className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-white">
            {telemetry?.process_memory_mb?.toFixed(0) || '0'} MB
          </div>
          <div className="text-[10px] text-zinc-500 font-mono mt-1">Backend RSS footprint</div>
        </div>

        <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-lg">
          <div className="flex items-center justify-between text-zinc-400 text-xs mb-1">
            <span>AI MODELS MEMORY</span>
            <Cpu className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-white">
            {telemetry?.ai_models_memory_mb?.toFixed(0) || '0'} MB
          </div>
          <div className="text-[10px] text-zinc-500 font-mono mt-1">Weights & accelerators</div>
        </div>

        <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-lg">
          <div className="flex items-center justify-between text-zinc-400 text-xs mb-1">
            <span>ACTIVE ADAPTERS</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-mono font-bold text-white">
            {telemetry?.active_adapters_count || 0} / {telemetry?.total_adapters_count || 7}
          </div>
          <div className="text-[10px] text-zinc-500 font-mono mt-1">Fault-isolated pipelines</div>
        </div>
      </div>

      {/* TAB 1: MODELS & ADAPTERS */}
      {activeTab === 'models' && (
        <div className="space-y-4">
          <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg overflow-hidden">
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
              <h2 className="text-sm font-semibold tracking-wide uppercase flex items-center gap-2">
                <Layers className="w-4 h-4 text-zinc-400" />
                Registered Perception Adapters & Models
              </h2>
              <span className="text-xs font-mono text-zinc-500">
                {models.length} Registered Tasks
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-zinc-950/80 text-zinc-400 border-b border-zinc-800">
                  <tr>
                    <th className="p-3">MODEL NAME</th>
                    <th className="p-3">TASK</th>
                    <th className="p-3">PROVIDER</th>
                    <th className="p-3">DEVICE</th>
                    <th className="p-3">LATENCY / FPS</th>
                    <th className="p-3">STATUS</th>
                    <th className="p-3 text-right">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {models.map((m) => (
                    <tr key={m.id} className="hover:bg-zinc-800/30 transition-colors">
                      <td className="p-3 font-semibold text-zinc-200">
                        <div>{m.name}</div>
                        <div className="text-[10px] text-zinc-500">{m.model_path} ({m.format})</div>
                      </td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 bg-zinc-800 text-zinc-300 rounded text-[10px]">
                          {m.task}
                        </span>
                      </td>
                      <td className="p-3 text-zinc-400">{m.provider}</td>
                      <td className="p-3 text-zinc-300">{m.device}</td>
                      <td className="p-3 text-zinc-300">
                        {m.inference_latency_ms > 0 ? `${m.inference_latency_ms} ms (${m.inference_fps} FPS)` : 'Standby / 0 FPS'}
                      </td>
                      <td className="p-3">{getStatusBadge(m.status)}</td>
                      <td className="p-3 text-right space-x-2">
                        {isOperatorOrAdmin && (
                          <>
                            <button
                              onClick={() => handleReloadModel(m.id)}
                              className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-[11px] transition-colors"
                              title="Reload model weights"
                            >
                              Reload
                            </button>
                            <button
                              onClick={() => handleUnloadModel(m.id)}
                              className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 rounded text-[11px] transition-colors"
                              title="Unload from memory"
                            >
                              Unload
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: CAMERA AI PROFILES */}
      {activeTab === 'profiles' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Camera Selector */}
          <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Select Camera Target</h3>
            <div className="space-y-1">
              {cameras.map((cam) => (
                <button
                  key={cam.id}
                  onClick={() => setSelectedCameraId(cam.id)}
                  className={`w-full text-left p-3 rounded text-xs font-mono transition-colors flex items-center justify-between ${
                    selectedCameraId === cam.id
                      ? 'bg-zinc-800 text-white border border-zinc-600 font-semibold'
                      : 'bg-zinc-950/60 text-zinc-400 hover:bg-zinc-800/40 border border-zinc-800/60'
                  }`}
                >
                  <div>
                    <div className="font-semibold">{cam.name}</div>
                    <div className="text-[10px] text-zinc-500">ID: {cam.id} | {cam.location || 'Perimeter'}</div>
                  </div>
                  <span className={`w-2 h-2 rounded-full ${cam.status === 'ONLINE' ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
                </button>
              ))}
            </div>
          </div>

          {/* Profile Settings Matrix */}
          <div className="md:col-span-2 bg-zinc-900/70 border border-zinc-800 rounded-lg p-5 space-y-6">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide">
                  Perception Profile: Camera #{selectedCameraId}
                </h3>
                <p className="text-xs text-zinc-400">Enable/disable task modules and configure inference frame sampling intervals</p>
              </div>
              {isOperatorOrAdmin && (
                <button
                  onClick={handleSaveProfile}
                  disabled={savingProfile}
                  className="px-4 py-2 bg-white hover:bg-zinc-200 text-black font-semibold text-xs rounded transition-colors"
                >
                  {savingProfile ? 'Saving...' : 'Save Profile'}
                </button>
              )}
            </div>

            {activeProfile && (
              <div className="space-y-6">
                {/* Task Toggles */}
                <div>
                  <h4 className="text-xs font-mono font-semibold text-zinc-300 uppercase mb-3">AI Tasks Enablement</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {[
                      { key: 'person_detection', label: 'Person Detection' },
                      { key: 'vehicle_detection', label: 'Vehicle Detection' },
                      { key: 'anpr', label: 'ANPR / Plates' },
                      { key: 'face_recognition', label: 'Face Intelligence' },
                      { key: 'fall_detection', label: 'Fall Detection' },
                      { key: 'fire_smoke', label: 'Fire & Smoke' },
                      { key: 'crowd_analysis', label: 'Crowd Analytics' },
                      { key: 'behavior_analytics', label: 'Behavior Rules' },
                      { key: 'pose_estimation', label: 'Pose Estimation' },
                      { key: 'weapon_detection', label: 'Dangerous Objects' },
                      { key: 'action_recognition', label: 'Action Recognition' },
                      { key: 'attribute_analysis', label: 'Visual Attributes' },
                    ].map((item) => (
                      <label
                        key={item.key}
                        className={`flex items-center gap-2 p-2.5 rounded border text-xs font-mono cursor-pointer transition-colors ${
                          (activeProfile as any)[item.key]
                            ? 'bg-zinc-800/80 border-zinc-600 text-zinc-100'
                            : 'bg-zinc-950/60 border-zinc-800 text-zinc-500'
                        }`}
                      >
                        <input
                          type="checkbox"
                          disabled={!isOperatorOrAdmin}
                          checked={!!(activeProfile as any)[item.key]}
                          onChange={(e) =>
                            setActiveProfile({
                              ...activeProfile,
                              [item.key]: e.target.checked
                            })
                          }
                          className="rounded border-zinc-700 bg-zinc-900 text-zinc-200"
                        />
                        <span>{item.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Sampling Intervals */}
                <div>
                  <h4 className="text-xs font-mono font-semibold text-zinc-300 uppercase mb-3">Frame Sampling Intervals (Every N Frames)</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs font-mono">
                    {[
                      { key: 'fall_interval_frames', label: 'Fall Engine (Frames)' },
                      { key: 'fire_smoke_interval_frames', label: 'Fire & Smoke (Frames)' },
                      { key: 'crowd_interval_frames', label: 'Crowd Analyzer (Frames)' },
                      { key: 'pose_interval_frames', label: 'Pose Estimator (Frames)' },
                      { key: 'weapon_interval_frames', label: 'Weapon Model (Frames)' },
                      { key: 'action_interval_frames', label: 'Action Model (Frames)' },
                    ].map((item) => (
                      <div key={item.key} className="space-y-1">
                        <label className="text-zinc-400">{item.label}</label>
                        <input
                          type="number"
                          min="1"
                          max="30"
                          disabled={!isOperatorOrAdmin}
                          value={(activeProfile as any)[item.key] || 1}
                          onChange={(e) =>
                            setActiveProfile({
                              ...activeProfile,
                              [item.key]: parseInt(e.target.value) || 1
                            })
                          }
                          className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 text-xs focus:border-zinc-500 outline-none"
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Confidence & Persistence Thresholds */}
                <div>
                  <h4 className="text-xs font-mono font-semibold text-zinc-300 uppercase mb-3">Detection & Persistence Thresholds</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs font-mono">
                    <div className="space-y-1">
                      <label className="text-zinc-400">Detection Conf (0-1)</label>
                      <input
                        type="number"
                        step="0.05"
                        min="0.1"
                        max="0.99"
                        disabled={!isOperatorOrAdmin}
                        value={activeProfile.detection_threshold}
                        onChange={(e) =>
                          setActiveProfile({ ...activeProfile, detection_threshold: parseFloat(e.target.value) || 0.35 })
                        }
                        className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 text-xs focus:border-zinc-500 outline-none"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-zinc-400">Crowd Density Threshold</label>
                      <input
                        type="number"
                        min="2"
                        max="100"
                        disabled={!isOperatorOrAdmin}
                        value={activeProfile.crowd_density_threshold}
                        onChange={(e) =>
                          setActiveProfile({ ...activeProfile, crowd_density_threshold: parseInt(e.target.value) || 8 })
                        }
                        className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 text-xs focus:border-zinc-500 outline-none"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-zinc-400">Fire Persistence (sec)</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0.5"
                        max="10.0"
                        disabled={!isOperatorOrAdmin}
                        value={activeProfile.fire_smoke_persistence_sec}
                        onChange={(e) =>
                          setActiveProfile({ ...activeProfile, fire_smoke_persistence_sec: parseFloat(e.target.value) || 1.5 })
                        }
                        className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 text-xs focus:border-zinc-500 outline-none"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: DIAGNOSTICS & SIMULATION */}
      {activeTab === 'diagnostics' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-5 space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide flex items-center gap-2">
              <Play className="w-4 h-4 text-zinc-400" />
              Perception Engine Dry-Run Simulator
            </h3>
            <p className="text-xs text-zinc-400">Test specialized perception pipelines (Fall, Crowd, Fire) against the backend verification harness.</p>

            <div className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Select Event Type</label>
                <select
                  value={simType}
                  onChange={(e) => setSimType(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 focus:border-zinc-500 outline-none"
                >
                  <option value="FALL_DETECTED">FALL_DETECTED (Kinematic & Prone Collapse)</option>
                  <option value="CROWD_DENSITY">CROWD_DENSITY (Spatial Zone Breach & Surge)</option>
                </select>
              </div>

              <button
                onClick={handleRunSimulation}
                disabled={simulating}
                className="w-full py-2.5 bg-white hover:bg-zinc-200 text-black font-semibold rounded text-xs transition-colors flex items-center justify-center gap-2"
              >
                {simulating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                Execute Perception Simulation
              </button>
            </div>
          </div>

          <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-5 space-y-3 font-mono">
            <h3 className="text-xs font-semibold uppercase text-zinc-400">Simulation Output Diagnostic</h3>
            <pre className="w-full h-64 p-3 bg-zinc-950 border border-zinc-800/80 rounded text-[11px] text-zinc-300 overflow-auto whitespace-pre-wrap">
              {simResult ? JSON.stringify(simResult, null, 2) : '// Output payload will appear here...'}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
