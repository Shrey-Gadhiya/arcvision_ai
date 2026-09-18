import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  UserX,
  ShieldAlert,
  Search,
  Plus,
  RefreshCw,
  Sliders,
  Cpu,
  Eye,
  Camera,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Clock,
  Sparkles,
  Info
} from 'lucide-react';
import {
  FaceRecord,
  FaceIdentity,
  FaceStatus,
  FaceEnrollmentResponse,
  FaceWatchlistCategory,
  FaceWatchlistPriority,
  FaceMatchStatus
} from '../types';
import { apiClient, getMediaUrl } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Tabs } from '../components/common/Tabs';

export const FaceIntelligence: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('live');
  const [loading, setLoading] = useState<boolean>(false);

  // Data states
  const [records, setRecords] = useState<FaceRecord[]>([]);
  const [identities, setIdentities] = useState<FaceIdentity[]>([]);
  const [engineStatus, setEngineStatus] = useState<FaceStatus | null>(null);

  // Search & Filters state
  const [searchName, setSearchName] = useState<string>('');
  const [searchStatus, setSearchStatus] = useState<string>('');
  const [searchCamera, setSearchCamera] = useState<string>('');
  const [minSimilarity, setMinSimilarity] = useState<number>(0.50);
  const [searchResults, setSearchResults] = useState<FaceRecord[]>([]);
  const [searchTotal, setSearchTotal] = useState<number>(0);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  // Enrollment Modal state
  const [showEnrollModal, setShowEnrollModal] = useState<boolean>(false);
  const [enrollName, setEnrollName] = useState<string>('');
  const [enrollIdentifier, setEnrollIdentifier] = useState<string>('');
  const [enrollCategory, setEnrollCategory] = useState<FaceWatchlistCategory>('WATCH');
  const [enrollPriority, setEnrollPriority] = useState<FaceWatchlistPriority>('HIGH');
  const [enrollNotes, setEnrollNotes] = useState<string>('');
  const [enrollImageBase64, setEnrollImageBase64] = useState<string>('');
  const [enrollPreview, setEnrollPreview] = useState<string | null>(null);
  const [enrollSubmitting, setEnrollSubmitting] = useState<boolean>(false);
  const [enrollResult, setEnrollResult] = useState<FaceEnrollmentResponse | null>(null);

  // Media inspection modal
  const [selectedCrop, setSelectedCrop] = useState<{ url: string; title: string; meta?: string } | null>(null);

  const fetchCoreData = async () => {
    setLoading(true);
    try {
      const [recordsRes, identitiesRes, statusRes] = await Promise.all([
        apiClient.get('/face/records?limit=50'),
        apiClient.get('/face/identities'),
        apiClient.get('/face/status')
      ]);
      setRecords(recordsRes.data.items || []);
      setIdentities(identitiesRes.data || []);
      setEngineStatus(statusRes.data || null);
    } catch (e) {
      console.error('Failed to fetch face intelligence data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCoreData();
    const timer = setInterval(() => {
      // Auto-poll status and records gently
      fetchCoreData();
    }, 15000);
    return () => clearInterval(timer);
  }, []);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const b64 = event.target?.result as string;
      setEnrollPreview(b64);
      setEnrollImageBase64(b64);
      setEnrollResult(null);
    };
    reader.readAsDataURL(file);
  };

  const handleEnrollSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!enrollName.trim() || !enrollImageBase64) {
      alert('Please provide a full name and reference face portrait image.');
      return;
    }

    setEnrollSubmitting(true);
    setEnrollResult(null);

    try {
      const res = await apiClient.post<FaceEnrollmentResponse>('/face/enroll', {
        name: enrollName.trim(),
        identifier: enrollIdentifier.trim() || undefined,
        watchlist_category: enrollCategory,
        watchlist_priority: enrollPriority,
        notes: enrollNotes.trim() || undefined,
        image_base64: enrollImageBase64
      });

      setEnrollResult(res.data);
      if (res.data.success) {
        fetchCoreData();
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Enrollment request failed';
      setEnrollResult({
        success: false,
        quality_score: 0,
        sharpness_score: 0,
        diagnostics: msg,
        embedding_generated: false,
        error: msg
      });
    } finally {
      setEnrollSubmitting(false);
    }
  };

  const handleExecuteSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsSearching(true);
    try {
      const payload: any = {
        limit: 50,
        offset: 0,
        min_similarity: minSimilarity > 0 ? minSimilarity : undefined
      };
      if (searchName.trim()) payload.name = searchName.trim();
      if (searchStatus) payload.match_status = searchStatus;
      if (searchCamera) payload.camera_id = parseInt(searchCamera, 10);

      const res = await apiClient.post('/face/search', payload);
      setSearchResults(res.data.items || []);
      setSearchTotal(res.data.total || 0);
    } catch (err) {
      console.error('Forensic face search error:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleToggleActive = async (id: number, currentActive: boolean) => {
    try {
      await apiClient.patch(`/face/identities/${id}`, { is_active: !currentActive });
      fetchCoreData();
    } catch (err) {
      alert('Failed to update identity status');
    }
  };

  const getMatchBadge = (status: FaceMatchStatus) => {
    switch (status) {
      case 'KNOWN':
        return <Badge variant="success">KNOWN</Badge>;
      case 'UNCERTAIN':
        return <Badge variant="warning">UNCERTAIN</Badge>;
      case 'UNKNOWN':
        return <Badge variant="neutral">UNKNOWN</Badge>;
      case 'UNAVAILABLE':
      default:
        return <Badge variant="neutral">UNAVAILABLE</Badge>;
    }
  };

  const getWatchlistCategoryBadge = (cat?: FaceWatchlistCategory) => {
    if (!cat) return null;
    switch (cat) {
      case 'ALERT':
      case 'WATCH':
        return <Badge variant="critical">{cat}</Badge>;
      case 'ALLOW':
        return <Badge variant="success">{cat}</Badge>;
      case 'CUSTOM':
      default:
        return <Badge variant="neutral">{cat}</Badge>;
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Top Header & Telemetry Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
              Face Recognition & Biometric Intelligence
            </h1>
            <Badge variant="neutral">Phase G Production</Badge>
          </div>
          <p className="text-xs text-zinc-400 mt-0.5">
            Neural YuNet face detection, ArcFace/SFace biometric embedding extraction, watchlist matching, and forensic gallery search.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
            onClick={fetchCoreData}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={<Plus className="w-3.5 h-3.5" />}
            onClick={() => {
              setEnrollResult(null);
              setEnrollPreview(null);
              setEnrollImageBase64('');
              setShowEnrollModal(true);
            }}
          >
            Enroll Subject
          </Button>
        </div>
      </div>

      {/* Engine Status & Telemetry Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between text-zinc-400">
            <span className="uppercase text-[11px] font-semibold tracking-wider flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5 text-zinc-300" /> Detector Adapter
            </span>
            <Badge variant={engineStatus?.detector_status === 'LOADED' ? 'success' : 'warning'}>
              {engineStatus?.detector_status || 'OFFLINE'}
            </Badge>
          </div>
          <div className="mt-2">
            <span className="text-white font-medium">{engineStatus?.detector_adapter || 'YuNet-ONNX'}</span>
            <div className="flex items-center gap-2 text-zinc-400 text-[11px] mt-0.5">
              <span>Latency: {engineStatus?.detector_latency_ms || 0} ms</span>
              <span>•</span>
              <span>FPS: {engineStatus?.detector_fps || 0}</span>
            </div>
          </div>
        </div>

        <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between text-zinc-400">
            <span className="uppercase text-[11px] font-semibold tracking-wider flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-zinc-300" /> Embedding Engine
            </span>
            <Badge variant={engineStatus?.embedding_status === 'LOADED' ? 'success' : 'warning'}>
              {engineStatus?.embedding_status || 'NOT_CONFIGURED'}
            </Badge>
          </div>
          <div className="mt-2">
            <span className="text-white font-medium">{engineStatus?.embedding_adapter || 'SFace-128d'}</span>
            <div className="flex items-center gap-2 text-zinc-400 text-[11px] mt-0.5">
              <span>Dim: {engineStatus?.embedding_dimension || 0}-d vector</span>
              <span>•</span>
              <span>{engineStatus?.detector_device || 'CPU'}</span>
            </div>
          </div>
        </div>

        <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between text-zinc-400">
            <span className="uppercase text-[11px] font-semibold tracking-wider flex items-center gap-1.5">
              <UserCheck className="w-3.5 h-3.5 text-zinc-300" /> Enrolled Gallery
            </span>
            <span className="font-mono text-zinc-400">{engineStatus?.total_identities || identities.length} subjects</span>
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-white font-mono">{identities.filter(i => i.is_active).length}</div>
            <div className="text-zinc-400 text-[11px]">Active biometric identity templates</div>
          </div>
        </div>

        <div className="bg-zinc-950 border border-zinc-800 rounded-md p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between text-zinc-400">
            <span className="uppercase text-[11px] font-semibold tracking-wider flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-zinc-300" /> Security Watchlist
            </span>
            <Badge variant="critical">
              {identities.filter(i => i.is_active && (i.watchlist_category === 'WATCH' || i.watchlist_category === 'ALERT')).length} TARGETS
            </Badge>
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-white font-mono">
              {records.filter(r => r.watchlist_category === 'WATCH' || r.watchlist_category === 'ALERT').length}
            </div>
            <div className="text-zinc-400 text-[11px]">Watchlist sighting events</div>
          </div>
        </div>
      </div>

      {/* Main Tabs Container */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-hidden">
        <Tabs
          activeTab={activeTab}
          onChange={setActiveTab}
          className="px-4 pt-2 bg-zinc-950"
          tabs={[
            { id: 'live', label: 'Live Face Captures', count: records.length },
            { id: 'identities', label: 'Identity Directory', count: identities.length },
            { id: 'watchlist', label: 'Watchlist Targets', count: identities.filter(i => i.watchlist_category === 'WATCH' || i.watchlist_category === 'ALERT').length },
            { id: 'search', label: 'Forensic Search', count: searchTotal },
            { id: 'telemetry', label: 'AI Model Registry & Health' }
          ]}
        />

        <div className="p-4">
          {/* TAB 1: LIVE FACE CAPTURES */}
          {activeTab === 'live' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>Real-time optical face sightings across all streaming camera feeds.</span>
                <span>{records.length} recent captures</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase tracking-wider">
                    <tr>
                      <th className="p-2.5">FACE CROP</th>
                      <th className="p-2.5">UNIQUE PERSON ID</th>
                      <th className="p-2.5">TIMESTAMP</th>
                      <th className="p-2.5">MATCH STATUS</th>
                      <th className="p-2.5">IDENTITY</th>
                      <th className="p-2.5">SIMILARITY</th>
                      <th className="p-2.5">QUALITY / SHARPNESS</th>
                      <th className="p-2.5">CAMERA & TRACK</th>
                      <th className="p-2.5 text-right">ACTION</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800 text-zinc-300 font-mono">
                    {records.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="p-10 text-center text-zinc-500 font-sans text-xs">
                          No face detections recorded on active camera streams yet.
                        </td>
                      </tr>
                    ) : (
                      records.map((rec) => (
                        <tr key={rec.id} className="hover:bg-zinc-900/50">
                          <td className="p-2.5">
                            {rec.crop_path ? (
                              <button
                                onClick={() => setSelectedCrop({
                                  url: getMediaUrl(rec.crop_path!),
                                  title: `${rec.unique_person_id || 'Person'} | ${rec.identity_name || 'Face Record'}`,
                                  meta: `Sim: ${(rec.similarity_score * 100).toFixed(1)}% | Cam #${rec.camera_id}`
                                })}
                                className="w-10 h-10 rounded border border-zinc-700 bg-black overflow-hidden flex items-center justify-center hover:border-white transition-colors"
                              >
                                <img src={getMediaUrl(rec.crop_path)} alt="Face" className="w-full h-full object-cover" />
                              </button>
                            ) : (
                              <div className="w-10 h-10 rounded border border-zinc-800 bg-zinc-900 flex items-center justify-center text-zinc-600">
                                <UserX className="w-4 h-4" />
                              </div>
                            )}
                          </td>
                          <td className="p-2.5 font-mono">
                            <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-700 text-white text-[11px] font-bold tracking-wider">
                              {rec.unique_person_id || `PERSON-${rec.id + 1000}`}
                            </span>
                          </td>
                          <td className="p-2.5 text-zinc-400">
                            {new Date(rec.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </td>
                          <td className="p-2.5 font-sans">
                            {getMatchBadge(rec.match_status)}
                          </td>
                          <td className="p-2.5 font-sans font-medium text-white">
                            <div className="flex items-center gap-1.5">
                              <span>{rec.identity_name || 'Unknown Subject'}</span>
                              {rec.watchlist_category && getWatchlistCategoryBadge(rec.watchlist_category)}
                            </div>
                          </td>
                          <td className="p-2.5">
                            <span className={rec.similarity_score >= rec.recognition_threshold ? 'text-white font-bold' : 'text-zinc-400'}>
                              {(rec.similarity_score * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td className="p-2.5 text-zinc-400 text-[11px] font-sans">
                            <span>Q: {(rec.quality_score * 100).toFixed(0)}%</span>
                            <span className="mx-1">•</span>
                            <span>Sharp: {rec.sharpness_score.toFixed(0)}</span>
                          </td>
                          <td className="p-2.5 text-zinc-400">
                            <span>Cam #{rec.camera_id}</span>
                            {rec.track_id && <span className="text-zinc-500"> (Trk #{rec.track_id})</span>}
                          </td>
                          <td className="p-2.5 text-right font-sans">
                            {rec.full_frame_path && (
                              <Button
                                variant="ghost"
                                size="xs"
                                icon={<Camera className="w-3.5 h-3.5 text-zinc-400 hover:text-white" />}
                                onClick={() => setSelectedCrop({
                                  url: getMediaUrl(rec.full_frame_path!),
                                  title: `Full Frame Context (${rec.unique_person_id || 'Person'}) - Cam #${rec.camera_id}`,
                                  meta: `Recorded at ${new Date(rec.timestamp).toLocaleString()}`
                                })}
                              />
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: IDENTITIES DIRECTORY */}
          {activeTab === 'identities' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>Enrolled biometric gallery subjects and access control templates.</span>
                <Button
                  variant="primary"
                  size="sm"
                  icon={<Plus className="w-3.5 h-3.5" />}
                  onClick={() => {
                    setEnrollResult(null);
                    setEnrollPreview(null);
                    setEnrollImageBase64('');
                    setShowEnrollModal(true);
                  }}
                >
                  Enroll New Identity
                </Button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase tracking-wider">
                    <tr>
                      <th className="p-2.5">PORTRAIT</th>
                      <th className="p-2.5">FULL NAME</th>
                      <th className="p-2.5">IDENTIFIER / PASSPORT</th>
                      <th className="p-2.5">CATEGORY</th>
                      <th className="p-2.5">PRIORITY</th>
                      <th className="p-2.5">EMBEDDINGS</th>
                      <th className="p-2.5">STATUS</th>
                      <th className="p-2.5">ENROLLED BY</th>
                      <th className="p-2.5 text-right">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800 text-zinc-300">
                    {identities.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="p-10 text-center text-zinc-500 text-xs">
                          No identities enrolled in gallery yet. Click "Enroll Subject" to register biometric templates.
                        </td>
                      </tr>
                    ) : (
                      identities.map((idnt) => (
                        <tr key={idnt.id} className="hover:bg-zinc-900/50">
                          <td className="p-2.5">
                            {idnt.reference_image_path ? (
                              <button
                                onClick={() => setSelectedCrop({
                                  url: getMediaUrl(idnt.reference_image_path!),
                                  title: idnt.name,
                                  meta: `Enrolled reference portrait (${idnt.identifier || 'No ID'})`
                                })}
                                className="w-9 h-9 rounded border border-zinc-700 bg-black overflow-hidden flex items-center justify-center hover:border-white transition-colors"
                              >
                                <img src={getMediaUrl(idnt.reference_image_path)} alt={idnt.name} className="w-full h-full object-cover" />
                              </button>
                            ) : (
                              <div className="w-9 h-9 rounded border border-zinc-800 bg-zinc-900 flex items-center justify-center text-zinc-600">
                                <UserCheck className="w-4 h-4" />
                              </div>
                            )}
                          </td>
                          <td className="p-2.5 font-medium text-white">
                            <div>{idnt.name}</div>
                            {idnt.notes && <div className="text-[11px] text-zinc-500 truncate max-w-xs">{idnt.notes}</div>}
                          </td>
                          <td className="p-2.5 font-mono text-zinc-300">{idnt.identifier || '—'}</td>
                          <td className="p-2.5">
                            {getWatchlistCategoryBadge(idnt.watchlist_category)}
                          </td>
                          <td className="p-2.5 font-mono text-[11px]">
                            <span className={idnt.watchlist_priority === 'CRITICAL' ? 'text-white font-bold' : 'text-zinc-400'}>
                              {idnt.watchlist_priority}
                            </span>
                          </td>
                          <td className="p-2.5 font-mono text-zinc-400">
                            {idnt.embedding_count} vector{idnt.embedding_count !== 1 ? 's' : ''}
                          </td>
                          <td className="p-2.5">
                            <Badge variant={idnt.is_active ? 'success' : 'neutral'}>
                              {idnt.is_active ? 'ACTIVE' : 'DEACTIVATED'}
                            </Badge>
                          </td>
                          <td className="p-2.5 text-zinc-400 text-[11px]">
                            {idnt.created_by || 'system'}
                          </td>
                          <td className="p-2.5 text-right">
                            <Button
                              variant="secondary"
                              size="xs"
                              onClick={() => handleToggleActive(idnt.id, idnt.is_active)}
                            >
                              {idnt.is_active ? 'Deactivate' : 'Activate'}
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: WATCHLIST TARGETS */}
          {activeTab === 'watchlist' && (
            <div className="space-y-4">
              <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md flex items-center justify-between text-xs text-zinc-300">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-white shrink-0" />
                  <span>
                    Watched subjects will automatically trigger <strong>CRITICAL Incidents</strong>, capture SHA-256 protected evidence, and dispatch real-time SOC alerts when recognized on any camera feed.
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {identities.filter(i => i.is_active && (i.watchlist_category === 'WATCH' || i.watchlist_category === 'ALERT')).length === 0 ? (
                  <div className="col-span-full p-10 text-center text-zinc-500 text-xs">
                    No active WATCH or ALERT targets enrolled.
                  </div>
                ) : (
                  identities
                    .filter(i => i.is_active && (i.watchlist_category === 'WATCH' || i.watchlist_category === 'ALERT'))
                    .map((target) => (
                      <div key={target.id} className="bg-zinc-900/60 border border-zinc-800 rounded-md p-3.5 space-y-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-3">
                            {target.reference_image_path ? (
                              <img src={target.reference_image_path} alt={target.name} className="w-12 h-12 rounded object-cover border border-zinc-700 bg-black" />
                            ) : (
                              <div className="w-12 h-12 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-500">
                                <UserX className="w-6 h-6" />
                              </div>
                            )}
                            <div>
                              <div className="font-semibold text-white text-sm">{target.name}</div>
                              <div className="text-[11px] font-mono text-zinc-400">{target.identifier || 'ID: UNRECORDED'}</div>
                            </div>
                          </div>
                          <Badge variant="critical">{target.watchlist_priority}</Badge>
                        </div>

                        <div className="text-xs text-zinc-400 bg-zinc-950 border border-zinc-800/80 rounded p-2">
                          {target.notes || 'Interception alert active upon facial recognition.'}
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-zinc-500 pt-1 border-t border-zinc-800">
                          <span>Updated: {new Date(target.updated_at).toLocaleDateString()}</span>
                          <Button
                            variant="ghost"
                            size="xs"
                            className="text-zinc-400 hover:text-white"
                            onClick={() => handleToggleActive(target.id, target.is_active)}
                          >
                            Remove
                          </Button>
                        </div>
                      </div>
                    ))
                )}
              </div>
            </div>
          )}

          {/* TAB 4: FORENSIC SEARCH */}
          {activeTab === 'search' && (
            <div className="space-y-4">
              <form onSubmit={handleExecuteSearch} className="bg-zinc-900 border border-zinc-800 rounded-md p-3.5 space-y-3 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block text-zinc-400 mb-1">Subject Name / Substring</label>
                    <input
                      type="text"
                      value={searchName}
                      onChange={(e) => setSearchName(e.target.value)}
                      placeholder="e.g. John Doe"
                      className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                    />
                  </div>

                  <div>
                    <label className="block text-zinc-400 mb-1">Match Status</label>
                    <select
                      value={searchStatus}
                      onChange={(e) => setSearchStatus(e.target.value)}
                      className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                    >
                      <option value="">ALL STATUSES</option>
                      <option value="KNOWN">KNOWN ONLY</option>
                      <option value="UNCERTAIN">UNCERTAIN ONLY</option>
                      <option value="UNKNOWN">UNKNOWN ONLY</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-zinc-400 mb-1">Camera ID</label>
                    <input
                      type="number"
                      value={searchCamera}
                      onChange={(e) => setSearchCamera(e.target.value)}
                      placeholder="e.g. 1"
                      className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                    />
                  </div>

                  <div>
                    <label className="block text-zinc-400 mb-1">Min Similarity: {(minSimilarity * 100).toFixed(0)}%</label>
                    <input
                      type="range"
                      min="0.20"
                      max="0.95"
                      step="0.05"
                      value={minSimilarity}
                      onChange={(e) => setMinSimilarity(parseFloat(e.target.value))}
                      className="w-full accent-white"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-1">
                  <Button
                    variant="primary"
                    size="sm"
                    type="submit"
                    icon={<Search className="w-3.5 h-3.5" />}
                    disabled={isSearching}
                  >
                    {isSearching ? 'Executing Query...' : 'Run Forensic Search'}
                  </Button>
                </div>
              </form>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase tracking-wider">
                    <tr>
                      <th className="p-2.5">FACE CROP</th>
                      <th className="p-2.5">TIMESTAMP</th>
                      <th className="p-2.5">MATCH STATUS</th>
                      <th className="p-2.5">IDENTIFIED AS</th>
                      <th className="p-2.5">SIMILARITY SCORE</th>
                      <th className="p-2.5">CAMERA</th>
                      <th className="p-2.5">EVIDENCE ID</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800 text-zinc-300 font-mono">
                    {searchResults.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="p-10 text-center text-zinc-500 font-sans text-xs">
                          {searchTotal === 0 ? 'Enter criteria above and click "Run Forensic Search".' : 'No matching face records found for specified query.'}
                        </td>
                      </tr>
                    ) : (
                      searchResults.map((rec) => (
                        <tr key={rec.id} className="hover:bg-zinc-900/50">
                          <td className="p-2.5">
                            {rec.crop_path ? (
                              <button
                                onClick={() => setSelectedCrop({
                                  url: rec.crop_path!,
                                  title: rec.identity_name || `Record #${rec.id}`,
                                  meta: `Sim: ${(rec.similarity_score * 100).toFixed(1)}%`
                                })}
                                className="w-10 h-10 rounded border border-zinc-700 bg-black overflow-hidden flex items-center justify-center hover:border-white transition-colors"
                              >
                                <img src={rec.crop_path} alt="Face" className="w-full h-full object-cover" />
                              </button>
                            ) : (
                              <div className="w-10 h-10 rounded border border-zinc-800 bg-zinc-900 flex items-center justify-center text-zinc-600">
                                <UserX className="w-4 h-4" />
                              </div>
                            )}
                          </td>
                          <td className="p-2.5 text-zinc-400">{new Date(rec.timestamp).toLocaleString()}</td>
                          <td className="p-2.5 font-sans">{getMatchBadge(rec.match_status)}</td>
                          <td className="p-2.5 font-sans font-medium text-white">{rec.identity_name || 'Unidentified'}</td>
                          <td className="p-2.5">{(rec.similarity_score * 100).toFixed(1)}%</td>
                          <td className="p-2.5 text-zinc-400">Cam #{rec.camera_id}</td>
                          <td className="p-2.5 text-zinc-400">{rec.evidence_id ? `#${rec.evidence_id}` : '—'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 5: AI MODEL TELEMETRY */}
          {activeTab === 'telemetry' && (
            <div className="space-y-4 text-xs">
              <div className="bg-zinc-900 border border-zinc-800 rounded-md p-4 space-y-4">
                <div className="flex items-center gap-2 text-white font-semibold text-sm">
                  <Cpu className="w-4 h-4 text-white" />
                  <span>Face Biometrics Model Architecture</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-zinc-300">
                  <div className="bg-zinc-950 border border-zinc-800 rounded p-3.5 space-y-2">
                    <div className="text-white font-semibold flex items-center justify-between">
                      <span>Face Localization Adapter</span>
                      <Badge variant={engineStatus?.detector_status === 'LOADED' ? 'success' : 'warning'}>
                        {engineStatus?.detector_status || 'NOT_CONFIGURED'}
                      </Badge>
                    </div>
                    <p className="text-zinc-400 text-[11px]">
                      YuNet lightweight neural detector optimized for real-time edge processing and 5-point facial landmark regression.
                    </p>
                    <div className="space-y-1 font-mono text-[11px] text-zinc-400 pt-1">
                      <div>Model: <span className="text-white">YuNet-ONNX (2023mar)</span></div>
                      <div>Input Size: <span className="text-white">320x320 Dynamic Scale</span></div>
                      <div>Quality Gates: <span className="text-white">Laplacian Variance &gt; 30.0</span></div>
                    </div>
                  </div>

                  <div className="bg-zinc-950 border border-zinc-800 rounded p-3.5 space-y-2">
                    <div className="text-white font-semibold flex items-center justify-between">
                      <span>Biometric Embedding Adapter</span>
                      <Badge variant={engineStatus?.embedding_status === 'LOADED' ? 'success' : 'warning'}>
                        {engineStatus?.embedding_status || 'NOT_CONFIGURED'}
                      </Badge>
                    </div>
                    <p className="text-zinc-400 text-[11px]">
                      SFace / ArcFace deep convolutional network producing L2-normalized hyperspherical biometric embeddings.
                    </p>
                    <div className="space-y-1 font-mono text-[11px] text-zinc-400 pt-1">
                      <div>Dimension: <span className="text-white">128-d Float32 Vector</span></div>
                      <div>Distance Metric: <span className="text-white">Cosine Similarity</span></div>
                      <div>Threshold: <span className="text-white">0.60 (Known) / 0.42 (Uncertain)</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ENROLLMENT MODAL */}
      {showEnrollModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-md max-w-lg w-full p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div>
                <h3 className="text-sm font-semibold text-white">Biometric Face Identity Enrollment</h3>
                <p className="text-[11px] text-zinc-400 mt-0.5">Strict quality gate: single face, sharp focus, normalized embedding vector.</p>
              </div>
              <button onClick={() => setShowEnrollModal(false)} className="text-zinc-400 hover:text-white text-lg">×</button>
            </div>

            <form onSubmit={handleEnrollSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Full Legal Name *</label>
                <input
                  type="text"
                  required
                  value={enrollName}
                  onChange={(e) => setEnrollName(e.target.value)}
                  placeholder="e.g. Inspector Vikram Rathore"
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-400 mb-1">Govt ID / Identifier</label>
                  <input
                    type="text"
                    value={enrollIdentifier}
                    onChange={(e) => setEnrollIdentifier(e.target.value)}
                    placeholder="e.g. IND-994012"
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono focus:outline-none focus:border-white"
                  />
                </div>

                <div>
                  <label className="block text-zinc-400 mb-1">Watchlist Category</label>
                  <select
                    value={enrollCategory}
                    onChange={(e) => setEnrollCategory(e.target.value as FaceWatchlistCategory)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                  >
                    <option value="WATCH">WATCH</option>
                    <option value="ALERT">ALERT (Immediate Intercept)</option>
                    <option value="ALLOW">ALLOW (Whitelisted)</option>
                    <option value="CUSTOM">CUSTOM</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-400 mb-1">Alert Priority</label>
                  <select
                    value={enrollPriority}
                    onChange={(e) => setEnrollPriority(e.target.value as FaceWatchlistPriority)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-400 mb-1">Reference Portrait Image *</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1 text-white text-[11px] file:mr-2 file:py-0.5 file:px-2 file:rounded file:border-0 file:text-xs file:bg-zinc-800 file:text-white hover:file:bg-zinc-700"
                  />
                </div>
              </div>

              {/* Preview & Diagnostics Box */}
              {enrollPreview && (
                <div className="flex items-center gap-3 p-2.5 bg-zinc-900 border border-zinc-800 rounded">
                  <img src={enrollPreview} alt="Preview" className="w-16 h-16 object-cover rounded border border-zinc-700 bg-black" />
                  <div className="text-[11px] text-zinc-400 space-y-0.5">
                    <div className="text-white font-medium">Portrait Ready for Quality Gate</div>
                    <div>Neural detector will crop face and extract L2 biometric embedding vector.</div>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-zinc-400 mb-1">Operational Notes / Clearance Info</label>
                <textarea
                  rows={2}
                  value={enrollNotes}
                  onChange={(e) => setEnrollNotes(e.target.value)}
                  placeholder="Security clearance info, watchlist reasons, or handling instructions..."
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white resize-none focus:outline-none focus:border-white"
                />
              </div>

              {/* Enrollment Result Diagnostics */}
              {enrollResult && (
                <div className={`p-3 rounded border text-xs ${enrollResult.success ? 'bg-zinc-900 border-zinc-700 text-zinc-200' : 'bg-zinc-900 border-zinc-800 text-zinc-300'}`}>
                  <div className="flex items-center gap-2 font-semibold">
                    {enrollResult.success ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-white" />
                        <span>Biometric Enrollment Successful (#{enrollResult.identity_id})</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-4 h-4 text-white" />
                        <span>Quality Gate Validation Failed</span>
                      </>
                    )}
                  </div>
                  <div className="mt-1 text-[11px] text-zinc-400">{enrollResult.diagnostics}</div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
                <Button
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={() => setShowEnrollModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  type="submit"
                  disabled={enrollSubmitting || !enrollImageBase64}
                >
                  {enrollSubmitting ? 'Evaluating Quality...' : 'Validate & Enroll'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Media Inspection Modal */}
      {selectedCrop && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4" onClick={() => setSelectedCrop(null)}>
          <div className="bg-zinc-950 border border-zinc-800 rounded-md max-w-lg w-full p-4 space-y-3" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <h3 className="text-sm font-semibold text-white">{selectedCrop.title}</h3>
              <button onClick={() => setSelectedCrop(null)} className="text-zinc-400 hover:text-white">×</button>
            </div>
            <div className="bg-black border border-zinc-800 rounded flex items-center justify-center overflow-hidden max-h-96">
              <img src={selectedCrop.url} alt={selectedCrop.title} className="max-w-full max-h-96 object-contain" />
            </div>
            {selectedCrop.meta && (
              <div className="text-xs font-mono text-zinc-400">{selectedCrop.meta}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
