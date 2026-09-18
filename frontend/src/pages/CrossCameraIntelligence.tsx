import React, { useState, useEffect } from 'react';
import {
  Share2,
  Car,
  UserCheck,
  Search,
  ArrowRight,
  Shield,
  Activity,
  Layers,
  MapPin,
  Clock,
  Compass,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  GitCommit,
  Eye,
  Sliders,
  Sparkles,
  Info
} from 'lucide-react';
import { apiClient } from '../api/client';

interface GlobalTrackItem {
  id: number;
  global_id: string;
  entity_type: string;
  current_camera_id: number;
  current_sector: string;
  plate_number?: string;
  face_identity_id?: number;
  face_identity_name?: string;
  confidence: number;
  identity_source: string;
  first_seen: string;
  last_seen: string;
  is_active: boolean;
  total_observations: number;
  journey_hops?: Array<{
    camera_id: number;
    camera_name: string;
    sector?: string;
    timestamp: string;
    zones?: string[];
    duration_sec?: number;
  }>;
}

interface CameraTopologyLink {
  id: number;
  from_camera_id: number;
  to_camera_id: number;
  distance_meters: number;
  min_travel_sec: number;
  max_travel_sec: number;
  direction: string;
  sector: string;
  is_active: boolean;
}

interface CrossCameraStatus {
  status: string;
  timestamp: string;
  subsystems: {
    plate_correlation: { status: string; mode: string; description: string };
    face_correlation: { status: string; mode: string; description: string };
    topology_graph: { status: string; links_count: number; description: string };
    appearance_person_reid: { status: string; model_name: string; provider: string; reason: string };
    appearance_vehicle_reid: { status: string; model_name: string; provider: string; reason: string };
  };
  active_global_tracks_count: number;
}

export const CrossCameraIntelligence: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'tracks' | 'topology' | 'search' | 'status'>('tracks');
  const [statusData, setStatusData] = useState<CrossCameraStatus | null>(null);
  const [tracks, setTracks] = useState<GlobalTrackItem[]>([]);
  const [selectedTrack, setSelectedTrack] = useState<GlobalTrackItem | null>(null);
  const [topologyLinks, setTopologyLinks] = useState<CameraTopologyLink[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [filterType, setFilterType] = useState<string>('ALL');

  // Simulator state
  const [simFromCam, setSimFromCam] = useState<number>(1);
  const [simToCam, setSimToCam] = useState<number>(2);
  const [simDeltaSec, setSimDeltaSec] = useState<number>(15);
  const [simResult, setSimResult] = useState<any | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  useEffect(() => {
    fetchInitialData();
    const interval = setInterval(fetchTracksOnly, 6000);
    return () => clearInterval(interval);
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [statusRes, tracksRes, topoRes] = await Promise.all([
        apiClient.get('/api/v1/cross-camera/status'),
        apiClient.get('/api/v1/cross-camera/tracks?limit=50'),
        apiClient.get('/api/v1/cross-camera/topology')
      ]);
      setStatusData(statusRes.data);
      setTracks(tracksRes.data);
      setTopologyLinks(topoRes.data);

      if (tracksRes.data.length > 0 && !selectedTrack) {
        loadTrackDetail(tracksRes.data[0].global_id);
      }
    } catch (err) {
      console.error('Failed to load Cross-Camera Intelligence data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTracksOnly = async () => {
    try {
      const tracksRes = await apiClient.get('/api/v1/cross-camera/tracks?limit=50');
      setTracks(tracksRes.data);
    } catch (err) {
      console.error('Error polling global tracks:', err);
    }
  };

  const loadTrackDetail = async (globalId: string) => {
    try {
      const res = await apiClient.get(`/api/v1/cross-camera/tracks/${globalId}`);
      setSelectedTrack(res.data);
    } catch (err) {
      console.error('Failed to load global track detail:', err);
    }
  };

  const runSimulation = async () => {
    try {
      const res = await apiClient.post(
        `/api/v1/cross-camera/simulate?from_camera_id=${simFromCam}&to_camera_id=${simToCam}&delta_seconds=${simDeltaSec}`
      );
      setSimResult(res.data);
    } catch (err) {
      console.error('Simulation failed:', err);
    }
  };

  const runSightingSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const isVehicle = searchQuery.toUpperCase().startsWith('DL') || searchQuery.toUpperCase().startsWith('UP') || searchQuery.toUpperCase().startsWith('GLOBAL-V');
      const payload: any = { limit: 20 };
      if (searchQuery.startsWith('GLOBAL-')) {
        payload.global_id = searchQuery;
      } else if (isVehicle) {
        payload.plate_number = searchQuery;
      } else {
        payload.face_name = searchQuery;
      }

      const res = await apiClient.post('/api/v1/cross-camera/search', payload);
      setSearchResults(res.data.results || []);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const filteredTracks = tracks.filter((t) => {
    if (filterType === 'ALL') return true;
    return t.entity_type === filterType;
  });

  return (
    <div className="flex-1 flex flex-col bg-[#09090b] text-zinc-100 min-h-0 overflow-y-auto">
      {/* Top Header */}
      <div className="px-6 py-4 border-b border-[#27272a] bg-[#121215] flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-700 flex items-center justify-center text-white shadow-inner">
            <Share2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold tracking-wide text-zinc-100">
                Cross-Camera Intelligence & Entity Re-ID
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                MULTI-CAM CORRELATION OPERATIONAL
              </span>
            </div>
            <p className="text-xs text-zinc-400">
              Spatial-temporal topology, license plate correlation & verified biometric tracking across camera sectors
            </p>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1 bg-zinc-900/90 p-1 rounded-lg border border-zinc-800">
          <button
            onClick={() => setActiveTab('tracks')}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'tracks'
                ? 'bg-zinc-800 text-white border border-zinc-700 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Global Tracks ({tracks.length})
          </button>
          <button
            onClick={() => setActiveTab('topology')}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'topology'
                ? 'bg-zinc-800 text-white border border-zinc-700 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            Camera Topology ({topologyLinks.length})
          </button>
          <button
            onClick={() => setActiveTab('search')}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'search'
                ? 'bg-zinc-800 text-white border border-zinc-700 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            Sighting Search
          </button>
          <button
            onClick={() => setActiveTab('status')}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'status'
                ? 'bg-zinc-800 text-white border border-zinc-700 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            Subsystem Status
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="p-6 flex-1 flex flex-col gap-6">
        {/* TAB 1: GLOBAL TRACKS & JOURNEY VISUALIZER */}
        {activeTab === 'tracks' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
            {/* Left Column: Track Feed */}
            <div className="lg:col-span-5 bg-[#121215] border border-[#27272a] rounded-lg flex flex-col overflow-hidden">
              <div className="p-3 border-b border-[#27272a] bg-[#18181b] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-zinc-300">Active Global Entities</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                    {filteredTracks.length} items
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {['ALL', 'PERSON', 'VEHICLE'].map((type) => (
                    <button
                      key={type}
                      onClick={() => setFilterType(type)}
                      className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                        filterType === type
                          ? 'bg-zinc-700 text-white'
                          : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                  <button
                    onClick={fetchInitialData}
                    className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 ml-1"
                    title="Refresh"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>

              {/* Entity List */}
              <div className="flex-1 overflow-y-auto divide-y divide-[#27272a]">
                {filteredTracks.length === 0 ? (
                  <div className="p-8 text-center text-xs text-zinc-500 flex flex-col items-center gap-2">
                    <Info className="w-6 h-6 text-zinc-600" />
                    No global tracks currently active. Detections across cameras will automatically correlate here.
                  </div>
                ) : (
                  filteredTracks.map((t) => {
                    const isSelected = selectedTrack?.global_id === t.global_id;
                    const isPerson = t.entity_type === 'PERSON';

                    return (
                      <div
                        key={t.global_id}
                        onClick={() => loadTrackDetail(t.global_id)}
                        className={`p-3 cursor-pointer transition-colors flex items-start justify-between gap-3 ${
                          isSelected
                            ? 'bg-zinc-900 border-l-2 border-white'
                            : 'hover:bg-zinc-900/60'
                        }`}
                      >
                        <div className="flex items-start gap-2.5 min-w-0">
                          <div
                            className={`p-2 rounded-md shrink-0 border ${
                              isPerson
                                ? 'bg-zinc-800/80 border-zinc-700 text-zinc-200'
                                : 'bg-zinc-800/80 border-zinc-700 text-zinc-200'
                            }`}
                          >
                            {isPerson ? <UserCheck className="w-4 h-4" /> : <Car className="w-4 h-4" />}
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs font-bold text-white tracking-wide">
                                {t.global_id}
                              </span>
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 font-mono border border-zinc-700">
                                {t.identity_source}
                              </span>
                            </div>
                            <div className="text-xs text-zinc-300 truncate mt-0.5 font-medium">
                              {t.plate_number ? (
                                <span className="font-mono text-amber-400">Plate: {t.plate_number}</span>
                              ) : t.face_identity_name ? (
                                <span className="text-sky-300">Identity: {t.face_identity_name}</span>
                              ) : (
                                <span className="text-zinc-400">Unidentified Track</span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-[11px] text-zinc-400 mt-1">
                              <span className="flex items-center gap-1">
                                <MapPin className="w-3 h-3 text-zinc-500" />
                                Cam #{t.current_camera_id} ({t.current_sector})
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                            Conf {Math.round(t.confidence * 100)}%
                          </span>
                          <div className="text-[10px] text-zinc-400 mt-1 font-mono">
                            {new Date(t.last_seen).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right Column: Detailed Journey Flow & Associated Intelligence */}
            <div className="lg:col-span-7 bg-[#121215] border border-[#27272a] rounded-lg p-5 flex flex-col overflow-hidden">
              {selectedTrack ? (
                <div className="flex flex-col h-full gap-5 overflow-y-auto">
                  {/* Entity Header Banner */}
                  <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold font-mono text-white tracking-wide">
                          {selectedTrack.global_id}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded font-mono font-medium bg-zinc-800 text-zinc-200 border border-zinc-700">
                          {selectedTrack.entity_type}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-400 mt-1 flex items-center gap-4">
                        <span>Current Sector: <strong className="text-zinc-200">{selectedTrack.current_sector}</strong></span>
                        <span>Current Camera: <strong className="text-zinc-200">Camera #{selectedTrack.current_camera_id}</strong></span>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-xs text-zinc-400">Correlation Engine</div>
                      <div className="text-xs font-mono font-semibold text-emerald-400">
                        {selectedTrack.identity_source} ({Math.round(selectedTrack.confidence * 100)}%)
                      </div>
                    </div>
                  </div>

                  {/* Associated Intelligence Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-md">
                      <div className="text-[11px] text-zinc-400 uppercase font-semibold">License Plate</div>
                      <div className="text-sm font-mono font-bold text-amber-400 mt-1">
                        {selectedTrack.plate_number || 'NOT_DETECTED'}
                      </div>
                      <div className="text-[10px] text-zinc-400 mt-0.5">Verified ALPR Optical OCR</div>
                    </div>

                    <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-md">
                      <div className="text-[11px] text-zinc-400 uppercase font-semibold">Face Biometric Identity</div>
                      <div className="text-sm font-semibold text-sky-400 mt-1 truncate">
                        {selectedTrack.face_identity_name || 'UNVERIFIED_INDIVIDUAL'}
                      </div>
                      <div className="text-[10px] text-zinc-400 mt-0.5">Biometric Gallery Verification</div>
                    </div>

                    <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-md">
                      <div className="text-[11px] text-zinc-400 uppercase font-semibold">Appearance Re-ID</div>
                      <div className="text-sm font-mono text-zinc-400 mt-1">
                        STANDBY (METADATA)
                      </div>
                      <div className="text-[10px] text-zinc-400 mt-0.5">Deep Feature Extraction</div>
                    </div>
                  </div>

                  {/* Multi-Camera Journey Timeline */}
                  <div className="flex-1 bg-zinc-900/40 border border-zinc-800/80 rounded-lg p-4 flex flex-col min-h-0">
                    <div className="flex items-center justify-between mb-4 border-b border-zinc-800 pb-2">
                      <h3 className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                        <GitCommit className="w-4 h-4 text-zinc-400" />
                        Multi-Camera Journey Timeline ({selectedTrack.journey_hops?.length || 1} Sightings)
                      </h3>
                      <span className="text-[10px] font-mono text-zinc-400">
                        First: {new Date(selectedTrack.first_seen).toLocaleTimeString()} → Last: {new Date(selectedTrack.last_seen).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="flex-1 overflow-y-auto space-y-4 relative pl-4 border-l-2 border-zinc-800 ml-2">
                      {selectedTrack.journey_hops && selectedTrack.journey_hops.length > 0 ? (
                        selectedTrack.journey_hops.map((hop, idx) => (
                          <div key={idx} className="relative group">
                            {/* Node Dot */}
                            <div className="absolute -left-[21px] top-1.5 w-3 h-3 rounded-full bg-zinc-900 border-2 border-white" />

                            <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3 hover:border-zinc-700 transition-colors">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-bold text-white">
                                    Hop #{idx + 1}: {hop.camera_name || `Camera #${hop.camera_id}`}
                                  </span>
                                  {hop.sector && (
                                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                                      {hop.sector}
                                    </span>
                                  )}
                                </div>
                                <span className="text-xs font-mono text-zinc-400">
                                  {hop.timestamp}
                                </span>
                              </div>

                              {hop.zones && hop.zones.length > 0 && (
                                <div className="mt-2 flex flex-wrap gap-1">
                                  {hop.zones.map((z, zidx) => (
                                    <span
                                      key={zidx}
                                      className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-300 border border-zinc-700"
                                    >
                                      Traversed: {z}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="p-4 bg-zinc-900/50 rounded border border-zinc-800 text-xs text-zinc-400">
                          Initial sighting at Camera #{selectedTrack.current_camera_id} in {selectedTrack.current_sector}.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-xs text-zinc-500 gap-2">
                  <Layers className="w-8 h-8 text-zinc-600" />
                  Select a global track from the left to view complete multi-camera journey history.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: CAMERA TOPOLOGY GRAPH & SIMULATOR */}
        {activeTab === 'topology' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
            {/* Left: Adjacency Table */}
            <div className="lg:col-span-7 bg-[#121215] border border-[#27272a] rounded-lg flex flex-col overflow-hidden">
              <div className="p-4 border-b border-[#27272a] bg-[#18181b] flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-zinc-200">Camera Adjacency & Transition Graph</h2>
                  <p className="text-xs text-zinc-400">
                    Spatial links and travel time windows (min_t ≤ Δt ≤ max_t) preventing impossible transit merges
                  </p>
                </div>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                  {topologyLinks.length} Configured Links
                </span>
              </div>

              <div className="flex-1 overflow-y-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-zinc-900/80 border-b border-zinc-800 text-zinc-400 font-mono text-[11px]">
                      <th className="p-3 font-semibold">FROM CAMERA</th>
                      <th className="p-3 font-semibold">TO CAMERA</th>
                      <th className="p-3 font-semibold">DISTANCE</th>
                      <th className="p-3 font-semibold">TRAVEL WINDOW</th>
                      <th className="p-3 font-semibold">SECTOR / CORRIDOR</th>
                      <th className="p-3 font-semibold">DIRECTION</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60 font-mono">
                    {topologyLinks.map((link) => (
                      <tr key={link.id} className="hover:bg-zinc-900/40 text-zinc-300">
                        <td className="p-3 font-semibold text-white">Camera #{link.from_camera_id}</td>
                        <td className="p-3 font-semibold text-white">Camera #{link.to_camera_id}</td>
                        <td className="p-3">{link.distance_meters}m</td>
                        <td className="p-3 text-emerald-400">
                          {link.min_travel_sec}s - {link.max_travel_sec}s
                        </td>
                        <td className="p-3 text-zinc-400 truncate max-w-[160px]">{link.sector}</td>
                        <td className="p-3">
                          <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 text-[10px] border border-zinc-700">
                            {link.direction}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right: Transition Feasibility Simulator */}
            <div className="lg:col-span-5 bg-[#121215] border border-[#27272a] rounded-lg p-5 flex flex-col gap-4">
              <div className="border-b border-[#27272a] pb-3">
                <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-1.5">
                  <Compass className="w-4 h-4 text-zinc-400" />
                  Transition Feasibility Dry-Run Simulator
                </h3>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Test spatial-temporal correlation feasibility between any two cameras under configured topology rules.
                </p>
              </div>

              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-zinc-400 font-medium">From Camera</label>
                    <select
                      value={simFromCam}
                      onChange={(e) => setSimFromCam(Number(e.target.value))}
                      className="w-full mt-1 bg-zinc-900 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-white"
                    >
                      {[1, 2, 3, 4, 5].map((id) => (
                        <option key={id} value={id}>Camera #{id}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-xs text-zinc-400 font-medium">To Camera</label>
                    <select
                      value={simToCam}
                      onChange={(e) => setSimToCam(Number(e.target.value))}
                      className="w-full mt-1 bg-zinc-900 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-white"
                    >
                      {[1, 2, 3, 4, 5].map((id) => (
                        <option key={id} value={id}>Camera #{id}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs text-zinc-400">
                    <label>Transit Delta (Seconds)</label>
                    <span className="font-mono text-white font-semibold">{simDeltaSec}s</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="180"
                    value={simDeltaSec}
                    onChange={(e) => setSimDeltaSec(Number(e.target.value))}
                    className="w-full mt-2 accent-white"
                  />
                </div>

                <button
                  onClick={runSimulation}
                  className="w-full py-2 bg-zinc-100 hover:bg-white text-zinc-900 font-semibold rounded text-xs transition-colors shadow"
                >
                  Evaluate Transition Feasibility
                </button>
              </div>

              {simResult && (
                <div
                  className={`p-4 rounded-lg border text-xs flex flex-col gap-2 mt-2 ${
                    simResult.is_feasible
                      ? 'bg-emerald-950/40 border-emerald-800/80 text-emerald-300'
                      : 'bg-rose-950/40 border-rose-800/80 text-rose-300'
                  }`}
                >
                  <div className="flex items-center gap-2 font-bold text-sm">
                    {simResult.is_feasible ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        FEASIBLE TRANSITION
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-4 h-4 text-rose-400" />
                        INFEASIBLE TRANSITION
                      </>
                    )}
                  </div>
                  <div className="font-mono text-[11px] space-y-1">
                    <div>Transition Confidence: {(simResult.confidence * 100).toFixed(1)}%</div>
                    <div>Link Configured: {simResult.link_configured ? 'YES' : 'NO (GENERAL CORRIDOR)'}</div>
                    {simResult.link_metadata && (
                      <div>
                        Permitted Window: {simResult.link_metadata.min_travel_sec}s - {simResult.link_metadata.max_travel_sec}s ({simResult.link_metadata.sector})
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: SIGHTING SEARCH */}
        {activeTab === 'search' && (
          <div className="bg-[#121215] border border-[#27272a] rounded-lg p-6 flex flex-col gap-5">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">Multi-Camera Sighting & Route Search</h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Query full cross-camera journey history by License Plate (e.g. DL01AB1234), Biometric Face Name, or Global ID.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Enter Plate (e.g. DL01AB1234), Officer/Subject Name, or GLOBAL-P-00042..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && runSightingSearch()}
                  className="w-full bg-zinc-900 border border-zinc-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
                />
              </div>
              <button
                onClick={runSightingSearch}
                disabled={isSearching}
                className="px-5 py-2 bg-zinc-100 hover:bg-white text-zinc-900 font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow shrink-0 disabled:opacity-50"
              >
                {isSearching ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                Search Sightings
              </button>
            </div>

            {/* Results */}
            <div className="space-y-4">
              {searchResults.length > 0 ? (
                searchResults.map((res, idx) => (
                  <div key={idx} className="p-4 bg-zinc-900/80 border border-zinc-800 rounded-lg space-y-3">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-white text-sm">{res.global_id}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-300 border border-zinc-700">
                          {res.entity_type}
                        </span>
                        {res.plate_number && (
                          <span className="text-xs font-mono font-bold text-amber-400">Plate: {res.plate_number}</span>
                        )}
                        {res.face_name && (
                          <span className="text-xs font-semibold text-sky-400">Identity: {res.face_name}</span>
                        )}
                      </div>
                      <span className="text-xs font-mono text-zinc-400">
                        Total Sightings: {res.total_sightings}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-xs">
                      {res.journey_hops.map((hop: any, hidx: number) => (
                        <div key={hidx} className="p-2.5 bg-zinc-900 border border-zinc-800/80 rounded flex flex-col">
                          <span className="font-semibold text-white">
                            {hop.camera_name || `Camera #${hop.camera_id}`}
                          </span>
                          <span className="text-[10px] text-zinc-400 font-mono mt-0.5">{hop.sector}</span>
                          <span className="text-[10px] text-zinc-500 font-mono mt-1">
                            {hop.timestamp ? new Date(hop.timestamp).toLocaleTimeString() : ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs text-zinc-500">
                  Enter an entity identifier above to track and visualize sightings across all camera sectors.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: SUBSYSTEM STATUS */}
        {activeTab === 'status' && statusData && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 bg-[#121215] border border-[#27272a] rounded-lg space-y-4">
              <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Operational Identity Correlation Subsystems
              </h2>

              <div className="space-y-3">
                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">Plate Correlation (ALPR)</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                      OPERATIONAL
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">
                    {statusData.subsystems.plate_correlation.description}
                  </p>
                </div>

                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">Face Biometrics Correlation</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                      OPERATIONAL
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">
                    {statusData.subsystems.face_correlation.description}
                  </p>
                </div>

                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">Camera Topology Adjacency</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                      OPERATIONAL
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">
                    {statusData.subsystems.topology_graph.description} ({statusData.subsystems.topology_graph.links_count} links active)
                  </p>
                </div>
              </div>
            </div>

            <div className="p-5 bg-[#121215] border border-[#27272a] rounded-lg space-y-4">
              <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <Info className="w-4 h-4 text-amber-400" />
                Deep Appearance Re-ID Model Adapters
              </h2>

              <div className="space-y-3">
                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">OSNet Person Re-ID</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                      {statusData.subsystems.appearance_person_reid.status}
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-zinc-400 mt-1">
                    Provider: {statusData.subsystems.appearance_person_reid.provider}
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">
                    {statusData.subsystems.appearance_person_reid.reason}
                  </p>
                </div>

                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">VeRi Vehicle Re-ID</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                      {statusData.subsystems.appearance_vehicle_reid.status}
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-zinc-400 mt-1">
                    Provider: {statusData.subsystems.appearance_vehicle_reid.provider}
                  </div>
                  <p className="text-xs text-zinc-400 mt-1">
                    {statusData.subsystems.appearance_vehicle_reid.reason}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
