import React, { useState, useEffect } from 'react';
import {
  Search,
  Plus,
  Trash2,
  RefreshCw,
  AlertCircle,
  ShieldAlert,
  Car,
  Clock,
  Eye,
  CheckCircle2,
  XCircle,
  HelpCircle,
  SlidersHorizontal,
  ChevronRight,
  TrendingUp,
  Cpu,
  Camera as CameraIcon,
  Tag
} from 'lucide-react';
import { ANPRRecord, ANPRWatchlist, VehicleIntelligenceStats, ANPRStatus, ANPRCaptureResponse } from '../types';
import { apiClient, getMediaUrl } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Tabs } from '../components/common/Tabs';

export const ANPRIntelligence: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('records');
  const [records, setRecords] = useState<ANPRRecord[]>([]);
  const [watchlist, setWatchlist] = useState<ANPRWatchlist[]>([]);
  const [statusInfo, setStatusInfo] = useState<ANPRStatus | null>(null);
  const [analytics, setAnalytics] = useState<VehicleIntelligenceStats | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Search state
  const [searchPlate, setSearchPlate] = useState<string>('');
  const [searchResult, setSearchResult] = useState<any | null>(null);
  const [searchVehicleClass, setSearchVehicleClass] = useState<string>('');
  const [searchValidationStatus, setSearchValidationStatus] = useState<string>('');
  const [searchIsMatched, setSearchIsMatched] = useState<string>('');

  // Watchlist filters
  const [watchlistCategoryFilter, setWatchlistCategoryFilter] = useState<string>('ALL');
  const [watchlistPriorityFilter, setWatchlistPriorityFilter] = useState<string>('ALL');

  // Add Watchlist Modal state
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [newPlate, setNewPlate] = useState('');
  const [newCategory, setNewCategory] = useState('SUSPECT');
  const [newPriority, setNewPriority] = useState('HIGH');
  const [newModel, setNewModel] = useState('');
  const [newNotes, setNewNotes] = useState('');

  // Capture & Detect Modal state
  const [showCaptureModal, setShowCaptureModal] = useState<boolean>(false);
  const [capturePreview, setCapturePreview] = useState<string | null>(null);
  const [captureImageBase64, setCaptureImageBase64] = useState<string | null>(null);
  const [captureSubmitting, setCaptureSubmitting] = useState<boolean>(false);
  const [captureResult, setCaptureResult] = useState<ANPRCaptureResponse | null>(null);
  const [captureCameraId, setCaptureCameraId] = useState<number>(1);
  const [captureNotes, setCaptureNotes] = useState<string>('');

  // Detail Modal state
  const [selectedRecord, setSelectedRecord] = useState<ANPRRecord | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [rRes, wRes, sRes, aRes] = await Promise.all([
        apiClient.get('/anpr/records?limit=50'),
        apiClient.get('/anpr/watchlist'),
        apiClient.get('/anpr/status'),
        apiClient.get('/anpr/vehicles/analytics?hours=24')
      ]);
      setRecords(rRes.data.items || rRes.data || []);
      setWatchlist(wRes.data || []);
      setStatusInfo(sRes.data || null);
      setAnalytics(aRes.data || null);
    } catch (e) {
      console.error('Failed to fetch ANPR data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchPlate.trim()) return;
    try {
      const res = await apiClient.get(`/anpr/query/${encodeURIComponent(searchPlate.trim().toUpperCase())}`);
      setSearchResult(res.data);
    } catch (e) {
      alert('Plate query failed');
    }
  };

  const handleFilteredSearch = async () => {
    setLoading(true);
    try {
      const payload: any = { limit: 50 };
      if (searchPlate.trim()) payload.plate_number = searchPlate.trim();
      if (searchVehicleClass) payload.vehicle_type = searchVehicleClass;
      if (searchValidationStatus) payload.validation_status = searchValidationStatus;
      if (searchIsMatched !== '') payload.is_matched = searchIsMatched === 'true';

      const res = await apiClient.post('/anpr/search', payload);
      setRecords(res.data.items || []);
    } catch (e) {
      console.error('Search failed:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleAddWatchlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlate.trim()) return;
    try {
      await apiClient.post('/anpr/watchlist', {
        plate_number: newPlate.trim().toUpperCase(),
        category: newCategory,
        priority: newPriority,
        vehicle_model: newModel,
        notes: newNotes,
        is_active: true
      });
      setNewPlate('');
      setNewModel('');
      setNewNotes('');
      setShowAddModal(false);
      fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to add plate to watchlist');
    }
  };

  const handleDeleteWatchlist = async (id: number) => {
    if (!confirm('Are you sure you want to remove this plate from the watchlist?')) return;
    try {
      await apiClient.delete(`/anpr/watchlist/${id}`);
      fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to remove watchlist plate');
    }
  };

  const filteredWatchlist = watchlist.filter((item) => {
    if (watchlistCategoryFilter !== 'ALL' && item.category !== watchlistCategoryFilter) return false;
    if (watchlistPriorityFilter !== 'ALL' && item.priority !== watchlistPriorityFilter) return false;
    return true;
  });

  const getValidationBadge = (status: string, format: string) => {
    switch (status) {
      case 'VALID':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-100 border border-zinc-700">
            <CheckCircle2 className="w-3 h-3 text-white" />
            {format === 'BHARAT_SERIES' ? 'BH SERIES' : 'VALID RTO'}
          </span>
        );
      case 'UNCERTAIN':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-900 text-zinc-300 border border-zinc-800">
            <HelpCircle className="w-3 h-3 text-zinc-400" />
            UNCERTAIN
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-950 text-zinc-500 border border-zinc-800">
            <XCircle className="w-3 h-3 text-zinc-600" />
            INVALID
          </span>
        );
    }
  };

  const handleCaptureFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const b64 = event.target?.result as string;
      setCapturePreview(b64);
      setCaptureImageBase64(b64);
      setCaptureResult(null);
    };
    reader.readAsDataURL(file);
  };

  const handleCaptureSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!captureImageBase64) {
      alert('Please select or upload a vehicle image with a visible number plate.');
      return;
    }
    setCaptureSubmitting(true);
    setCaptureResult(null);
    try {
      const res = await apiClient.post<ANPRCaptureResponse>('/anpr/capture-and-detect', {
        image_base64: captureImageBase64,
        camera_id: captureCameraId,
        notes: captureNotes.trim() || undefined
      });
      setCaptureResult(res.data);
      if (res.data.success) {
        fetchData();
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Plate detection failed';
      setCaptureResult({
        success: false,
        confidence: 0,
        ocr_confidence: 0,
        is_matched: false,
        diagnostics: msg,
        error: msg
      });
    } finally {
      setCaptureSubmitting(false);
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-full font-sans">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <div>
          <div className="flex items-center gap-2">
            <Car className="w-4 h-4 text-white" />
            <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
              Automatic Number Plate Recognition & Vehicle Intelligence
            </h1>
          </div>
          <p className="text-xs text-zinc-400 mt-0.5">
            Modular ANPR pipeline, EasyOCR character extraction, Indian RTO / Bharat Series validation, watchlist hotlists, and vehicle trajectory analytics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" icon={<RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />} onClick={fetchData}>
            Refresh
          </Button>
          <Button
            variant="secondary"
            size="sm"
            icon={<CameraIcon className="w-3.5 h-3.5" />}
            onClick={() => setShowCaptureModal(true)}
          >
            Capture & Detect Plate
          </Button>
          <Button variant="primary" size="sm" icon={<Plus className="w-3.5 h-3.5" />} onClick={() => setShowAddModal(true)}>
            Add to Watchlist
          </Button>
        </div>
      </div>

      {/* Engine Status & Telemetry Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-xs">
        <div className="p-2.5 bg-zinc-950 border border-zinc-800 rounded flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-white shrink-0" />
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Detector Adapter</div>
              <div className="font-semibold text-zinc-200">{statusInfo?.detector_adapter || 'Heuristic Plate Detector'}</div>
            </div>
          </div>
          <span className="px-1.5 py-0.5 text-[10px] rounded font-mono bg-zinc-900 border border-zinc-800 text-zinc-300">
            {statusInfo?.detector_status || 'LOADED'}
          </span>
        </div>

        <div className="p-2.5 bg-zinc-950 border border-zinc-800 rounded flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-white shrink-0" />
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">OCR Engine</div>
              <div className="font-semibold text-zinc-200">{statusInfo?.ocr_adapter || 'EasyOCR Engine'}</div>
            </div>
          </div>
          <span className={`px-1.5 py-0.5 text-[10px] rounded font-mono border ${statusInfo?.ocr_status === 'LOADED' ? 'bg-zinc-800 text-white border-zinc-600' : 'bg-zinc-950 text-zinc-500 border-zinc-800'}`}>
            {statusInfo?.ocr_status || 'UNAVAILABLE'}
          </span>
        </div>

        <div className="p-2.5 bg-zinc-950 border border-zinc-800 rounded flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-white shrink-0" />
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Watchlist Hotlist</div>
              <div className="font-semibold text-zinc-200">{watchlist.filter(w => w.is_active).length} Active Targets</div>
            </div>
          </div>
          <span className="px-1.5 py-0.5 text-[10px] rounded font-mono bg-zinc-900 border border-zinc-800 text-zinc-300">
            MONITORING
          </span>
        </div>

        <div className="p-2.5 bg-zinc-950 border border-zinc-800 rounded flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-white shrink-0" />
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Format Validator</div>
              <div className="font-semibold text-zinc-200">IN RTO + BH Series</div>
            </div>
          </div>
          <span className="px-1.5 py-0.5 text-[10px] rounded font-mono bg-zinc-900 border border-zinc-800 text-zinc-300">
            36 STATES
          </span>
        </div>
      </div>

      {/* Main Tabs */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-hidden">
        <Tabs
          activeTab={activeTab}
          onChange={setActiveTab}
          className="px-4 pt-2 bg-zinc-950"
          tabs={[
            { id: 'records', label: 'Live Sightings Log', count: records.length },
            { id: 'watchlist', label: 'Security Watchlists', count: watchlist.length },
            { id: 'search', label: 'Forensic Plate Search' },
            { id: 'analytics', label: 'Vehicle Intelligence' }
          ]}
        />

        <div className="p-4 space-y-4">
          {/* TAB 1: RECORDS */}
          {activeTab === 'records' && (
            <div className="space-y-3">
              {/* Quick Filter Bar */}
              <div className="flex flex-wrap items-center justify-between gap-2 p-2 bg-zinc-900 border border-zinc-800 rounded text-xs">
                <div className="flex items-center gap-2">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-400" />
                  <span className="text-zinc-400 uppercase text-[11px] font-semibold">Filter:</span>
                  <select
                    value={searchVehicleClass}
                    onChange={(e) => setSearchVehicleClass(e.target.value)}
                    className="bg-black border border-zinc-800 rounded px-2 py-1 text-white focus:outline-none"
                  >
                    <option value="">All Vehicles</option>
                    <option value="car">Car</option>
                    <option value="motorcycle">Motorcycle</option>
                    <option value="truck">Truck</option>
                    <option value="bus">Bus</option>
                  </select>
                  <select
                    value={searchValidationStatus}
                    onChange={(e) => setSearchValidationStatus(e.target.value)}
                    className="bg-black border border-zinc-800 rounded px-2 py-1 text-white focus:outline-none"
                  >
                    <option value="">All Formats</option>
                    <option value="VALID">Valid Format</option>
                    <option value="UNCERTAIN">Uncertain</option>
                    <option value="INVALID">Invalid</option>
                  </select>
                  <select
                    value={searchIsMatched}
                    onChange={(e) => setSearchIsMatched(e.target.value)}
                    className="bg-black border border-zinc-800 rounded px-2 py-1 text-white focus:outline-none"
                  >
                    <option value="">All Sightings</option>
                    <option value="true">Watchlist Hits Only</option>
                    <option value="false">Unflagged Only</option>
                  </select>
                  <Button variant="secondary" size="xs" onClick={handleFilteredSearch}>
                    Apply
                  </Button>
                </div>
                <div className="text-zinc-500 text-[11px]">
                  Showing {records.length} recent plate captures
                </div>
              </div>

              {/* Records Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase">
                    <tr>
                      <th className="p-2.5">TIMESTAMP</th>
                      <th className="p-2.5">PLATE NUMBER</th>
                      <th className="p-2.5">VEHICLE CLASS</th>
                      <th className="p-2.5">VALIDATION</th>
                      <th className="p-2.5">CONFIDENCE</th>
                      <th className="p-2.5">WATCHLIST STATUS</th>
                      <th className="p-2.5">LOCATION / CAM</th>
                      <th className="p-2.5 text-right">ACTION</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800 text-zinc-300">
                    {records.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="p-8 text-center text-zinc-500 text-xs">
                          No vehicle license plates detected yet on active cameras.
                        </td>
                      </tr>
                    ) : (
                      records.map((r) => (
                        <tr key={r.id} className="hover:bg-zinc-900/50 transition-colors">
                          <td className="p-2.5 font-mono text-zinc-400 text-[11px]">
                            {new Date(r.timestamp).toLocaleString()}
                          </td>
                          <td className="p-2.5">
                            <div className="flex items-center gap-2">
                              {r.crop_path ? (
                                <img
                                  src={getMediaUrl(r.crop_path)}
                                  alt={r.plate_number}
                                  className="w-14 h-7 object-cover rounded bg-black border border-zinc-700 shadow-sm"
                                  onError={(e) => {
                                    (e.target as HTMLElement).style.display = 'none';
                                  }}
                                />
                              ) : (
                                <div className="w-14 h-7 bg-zinc-900 border border-zinc-800 rounded flex items-center justify-center text-[9px] text-zinc-500 font-mono">
                                  NO CROP
                                </div>
                              )}
                              <div>
                                <span className="font-mono font-bold text-white text-sm tracking-wide">
                                  {r.plate_number}
                                </span>
                                {r.raw_text && r.raw_text !== r.plate_number && (
                                  <div className="text-[10px] text-zinc-500 font-mono">
                                    Raw: {r.raw_text}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="p-2.5">
                            <span className="capitalize text-zinc-200 font-medium">
                              {r.vehicle_type}
                            </span>
                            {r.is_stationary && (
                              <span className="ml-1.5 px-1 py-0.5 text-[9px] bg-zinc-800 border border-zinc-700 text-zinc-200 rounded font-mono">
                                STATIONARY ({r.dwell_duration_sec}s)
                              </span>
                            )}
                          </td>
                          <td className="p-2.5">
                            {getValidationBadge(r.validation_status, r.validation_format)}
                          </td>
                          <td className="p-2.5 font-mono text-zinc-300">
                            {(r.confidence * 100).toFixed(1)}%
                          </td>
                          <td className="p-2.5">
                            {r.is_matched ? (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-white text-black font-bold">
                                <ShieldAlert className="w-3 h-3" />
                                {r.watchlist_category || 'WATCHLIST HIT'}
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-900 text-zinc-500 border border-zinc-800">
                                CLEARED
                              </span>
                            )}
                          </td>
                          <td className="p-2.5 font-mono text-zinc-400">
                            Cam #{r.camera_id} (Trk #{r.track_id})
                          </td>
                          <td className="p-2.5 text-right">
                            <Button
                              variant="ghost"
                              size="xs"
                              onClick={() => setSelectedRecord(r)}
                              className="text-zinc-400 hover:text-white"
                            >
                              Inspect
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

          {/* TAB 2: WATCHLIST */}
          {activeTab === 'watchlist' && (
            <div className="space-y-3">
              {/* Watchlist Filter Bar */}
              <div className="flex flex-wrap items-center justify-between gap-2 p-2 bg-zinc-900 border border-zinc-800 rounded text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-zinc-400 uppercase text-[11px] font-semibold">Category:</span>
                  <select
                    value={watchlistCategoryFilter}
                    onChange={(e) => setWatchlistCategoryFilter(e.target.value)}
                    className="bg-black border border-zinc-800 rounded px-2 py-1 text-white focus:outline-none"
                  >
                    <option value="ALL">All Categories</option>
                    <option value="SUSPECT">SUSPECT</option>
                    <option value="STOLEN">STOLEN</option>
                    <option value="BLOCKLIST">BLOCKLIST</option>
                    <option value="ALLOWLIST">ALLOWLIST</option>
                    <option value="CUSTOMS_FLAGGED">CUSTOMS FLAGGED</option>
                    <option value="WANTED">WANTED</option>
                  </select>

                  <span className="text-zinc-400 uppercase text-[11px] font-semibold ml-2">Priority:</span>
                  <select
                    value={watchlistPriorityFilter}
                    onChange={(e) => setWatchlistPriorityFilter(e.target.value)}
                    className="bg-black border border-zinc-800 rounded px-2 py-1 text-white focus:outline-none"
                  >
                    <option value="ALL">All Priorities</option>
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>

                <Button variant="primary" size="sm" icon={<Plus className="w-3.5 h-3.5" />} onClick={() => setShowAddModal(true)}>
                  Add Target Plate
                </Button>
              </div>

              {/* Watchlist Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase">
                    <tr>
                      <th className="p-2.5">PLATE NUMBER</th>
                      <th className="p-2.5">CATEGORY</th>
                      <th className="p-2.5">PRIORITY</th>
                      <th className="p-2.5">VEHICLE DETAILS</th>
                      <th className="p-2.5">ALERT REASON / INVESTIGATION NOTES</th>
                      <th className="p-2.5">STATUS</th>
                      <th className="p-2.5 text-right">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800 text-zinc-300">
                    {filteredWatchlist.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="p-8 text-center text-zinc-500 text-xs">
                          No plates found in security watchlist matching current filters.
                        </td>
                      </tr>
                    ) : (
                      filteredWatchlist.map((w) => (
                        <tr key={w.id} className="hover:bg-zinc-900/50">
                          <td className="p-2.5 font-bold font-mono text-white text-sm">{w.plate_number}</td>
                          <td className="p-2.5">
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-white border border-zinc-700 font-semibold">
                              {w.category}
                            </span>
                          </td>
                          <td className="p-2.5">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${w.priority === 'CRITICAL' ? 'bg-white text-black' : 'bg-zinc-900 text-zinc-300 border border-zinc-800'}`}>
                              {w.priority}
                            </span>
                          </td>
                          <td className="p-2.5 text-zinc-300">{w.vehicle_model || 'Unspecified'}</td>
                          <td className="p-2.5 text-zinc-400 text-[11px]">{w.notes || 'Surveillance priority target'}</td>
                          <td className="p-2.5">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${w.is_active ? 'text-zinc-200 border border-zinc-700 bg-zinc-900' : 'text-zinc-600 border border-zinc-900'}`}>
                              {w.is_active ? 'ACTIVE' : 'INACTIVE'}
                            </span>
                          </td>
                          <td className="p-2.5 text-right">
                            <Button
                              variant="ghost"
                              size="xs"
                              icon={<Trash2 className="w-3 h-3 text-zinc-400 hover:text-white" />}
                              onClick={() => handleDeleteWatchlist(w.id)}
                            />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: FORENSIC SEARCH */}
          {activeTab === 'search' && (
            <div className="space-y-4">
              <div className="bg-zinc-900 border border-zinc-800 rounded-md p-4 space-y-3">
                <form onSubmit={handleSearch} className="flex gap-2">
                  <input
                    type="text"
                    value={searchPlate}
                    onChange={(e) => setSearchPlate(e.target.value)}
                    placeholder="Enter license plate number to query (e.g. DL01AB1234, 22BH1234AA)..."
                    className="flex-1 bg-black border border-zinc-800 rounded px-3 py-2 text-xs text-white uppercase font-mono placeholder-zinc-600 focus:outline-none focus:border-white"
                  />
                  <Button variant="primary" size="sm" type="submit" icon={<Search className="w-3.5 h-3.5" />}>
                    Lookup History
                  </Button>
                </form>
              </div>

              {searchResult && (
                <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xl font-bold text-white tracking-wider">
                          {searchResult.normalized_plate || searchResult.plate_number}
                        </span>
                        {getValidationBadge(searchResult.validation_status, searchResult.validation_format)}
                      </div>
                      <p className="text-xs text-zinc-400 mt-1">
                        Total Sightings: <strong>{searchResult.sightings_count}</strong> across cameras.
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {searchResult.is_flagged ? (
                        <div className="px-3 py-1.5 bg-white text-black font-bold font-mono text-xs rounded flex items-center gap-1.5">
                          <ShieldAlert className="w-4 h-4" />
                          WATCHLIST HIT: {searchResult.watchlist_info?.category || 'FLAGGED'}
                        </div>
                      ) : (
                        <div className="px-3 py-1.5 bg-zinc-900 border border-zinc-800 text-zinc-400 font-mono text-xs rounded">
                          CLEARED / NOT IN WATCHLIST
                        </div>
                      )}
                    </div>
                  </div>

                  {searchResult.watchlist_info && (
                    <div className="p-3 bg-zinc-900 border border-zinc-800 rounded text-xs space-y-1">
                      <div className="text-zinc-400 font-semibold uppercase text-[10px]">Watchlist Record</div>
                      <div className="text-zinc-200">
                        Priority: <strong>{searchResult.watchlist_info.priority}</strong> | Model: {searchResult.watchlist_info.vehicle_model || 'N/A'}
                      </div>
                      <div className="text-zinc-400">{searchResult.watchlist_info.notes}</div>
                    </div>
                  )}

                  {/* Sighting Timeline */}
                  <div>
                    <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-2">
                      Sighting Sighting Trail ({searchResult.history.length})
                    </h4>
                    <div className="space-y-2">
                      {searchResult.history.length === 0 ? (
                        <div className="text-xs text-zinc-500">No historical sightings recorded for this plate.</div>
                      ) : (
                        searchResult.history.map((h: ANPRRecord) => (
                          <div key={h.id} className="p-2.5 bg-zinc-900 border border-zinc-800 rounded flex items-center justify-between text-xs">
                            <div className="flex items-center gap-3">
                              {h.crop_path ? (
                                <img src={h.crop_path} alt="Plate crop" className="w-12 h-6 object-cover rounded bg-black border border-zinc-800" />
                              ) : (
                                <div className="w-12 h-6 bg-black border border-zinc-800 rounded flex items-center justify-center text-[9px] text-zinc-500">CROP</div>
                              )}
                              <div>
                                <span className="font-mono text-zinc-200 font-semibold">{new Date(h.timestamp).toLocaleString()}</span>
                                <div className="text-zinc-400 text-[11px]">Cam #{h.camera_id} • Vehicle: {h.vehicle_type} • Conf: {(h.confidence * 100).toFixed(1)}%</div>
                              </div>
                            </div>
                            <Button variant="ghost" size="xs" onClick={() => setSelectedRecord(h)}>
                              Details
                            </Button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: VEHICLE INTELLIGENCE */}
          {activeTab === 'analytics' && (
            <div className="space-y-4">
              {/* Analytics Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
                  <div className="text-zinc-400 text-[11px] uppercase">Total Sightings (24h)</div>
                  <div className="text-2xl font-bold font-mono text-white mt-1">
                    {analytics?.total_sightings || 0}
                  </div>
                </div>

                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
                  <div className="text-zinc-400 text-[11px] uppercase">Unique Plates Detected</div>
                  <div className="text-2xl font-bold font-mono text-white mt-1">
                    {analytics?.unique_plates || 0}
                  </div>
                </div>

                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
                  <div className="text-zinc-400 text-[11px] uppercase">Watchlist Hotlist Hits</div>
                  <div className="text-2xl font-bold font-mono text-white mt-1">
                    {analytics?.watchlist_hits || 0}
                  </div>
                </div>

                <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
                  <div className="text-zinc-400 text-[11px] uppercase">Stationary Vehicle Alerts</div>
                  <div className="text-2xl font-bold font-mono text-white mt-1">
                    {analytics?.stationary_vehicles_count || 0}
                  </div>
                </div>
              </div>

              {/* Breakdown Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Vehicle Class Distribution */}
                <div className="bg-zinc-900 border border-zinc-800 rounded-md p-4 space-y-3">
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                    Vehicle Class Distribution
                  </h3>
                  <div className="space-y-2 text-xs">
                    {Object.entries(analytics?.vehicle_class_distribution || {}).length === 0 ? (
                      <div className="text-zinc-500 py-4 text-center">No vehicle data available.</div>
                    ) : (
                      Object.entries(analytics?.vehicle_class_distribution || {}).map(([vClass, count]) => (
                        <div key={vClass} className="flex items-center justify-between p-2 bg-zinc-950 border border-zinc-800 rounded">
                          <span className="capitalize font-medium text-zinc-200">{vClass}</span>
                          <span className="font-mono text-white font-bold">{count}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Top Repeated Sightings */}
                <div className="bg-zinc-900 border border-zinc-800 rounded-md p-4 space-y-3">
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                    Frequent Sighting Targets (Top Repeaters)
                  </h3>
                  <div className="space-y-2 text-xs">
                    {(analytics?.top_seen_plates || []).length === 0 ? (
                      <div className="text-zinc-500 py-4 text-center">No repeated plate sightings logged.</div>
                    ) : (
                      (analytics?.top_seen_plates || []).map((p) => (
                        <div key={p.plate_number} className="flex items-center justify-between p-2 bg-zinc-950 border border-zinc-800 rounded">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-white">{p.plate_number}</span>
                            <span className="text-zinc-500 text-[10px] capitalize">({p.vehicle_type})</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-zinc-300 text-xs">{p.sightings_count} sightings</span>
                            {p.is_matched && (
                              <span className="px-1 py-0.5 text-[9px] bg-white text-black font-bold rounded">
                                HIT
                              </span>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Detail Inspection Modal */}
      {selectedRecord && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-md max-w-lg w-full p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div>
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                  Plate Sighting Detail
                </h3>
                <span className="font-mono text-xs text-zinc-400">ID #{selectedRecord.id} • Cam #{selectedRecord.camera_id}</span>
              </div>
              <Button variant="ghost" size="xs" onClick={() => setSelectedRecord(null)}>
                Close
              </Button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 bg-zinc-900 border border-zinc-800 rounded">
                <div>
                  <div className="text-[10px] text-zinc-500 uppercase">Normalized Plate</div>
                  <div className="text-xl font-bold font-mono text-white tracking-wider">{selectedRecord.plate_number}</div>
                </div>
                {getValidationBadge(selectedRecord.validation_status, selectedRecord.validation_format)}
              </div>

              {/* Crop Previews */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="text-[10px] text-zinc-500 uppercase mb-1 font-semibold">Plate Crop</div>
                  {selectedRecord.crop_path ? (
                    <img
                      src={getMediaUrl(selectedRecord.crop_path)}
                      alt="Plate crop"
                      className="w-full h-24 object-cover rounded bg-black border border-zinc-700 shadow-sm"
                    />
                  ) : (
                    <div className="w-full h-24 bg-zinc-900 border border-zinc-800 rounded flex items-center justify-center text-zinc-500 font-mono">
                      No Plate Crop
                    </div>
                  )}
                </div>

                <div>
                  <div className="text-[10px] text-zinc-500 uppercase mb-1 font-semibold">Vehicle / Scene Frame</div>
                  {selectedRecord.vehicle_crop_path || selectedRecord.full_frame_path ? (
                    <img
                      src={getMediaUrl(selectedRecord.vehicle_crop_path || selectedRecord.full_frame_path)}
                      alt="Vehicle crop"
                      className="w-full h-24 object-cover rounded bg-black border border-zinc-700 shadow-sm"
                    />
                  ) : (
                    <div className="w-full h-24 bg-zinc-900 border border-zinc-800 rounded flex items-center justify-center text-zinc-500 font-mono">
                      No Vehicle Crop
                    </div>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-zinc-300">
                <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                  <span className="text-zinc-500 text-[10px] block uppercase">Raw OCR Output</span>
                  <span className="font-mono font-bold text-white">{selectedRecord.raw_text || 'N/A'}</span>
                </div>
                <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                  <span className="text-zinc-500 text-[10px] block uppercase">Confidence</span>
                  <span className="font-mono text-white">{(selectedRecord.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                  <span className="text-zinc-500 text-[10px] block uppercase">Vehicle Class</span>
                  <span className="capitalize text-white">{selectedRecord.vehicle_type}</span>
                </div>
                <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                  <span className="text-zinc-500 text-[10px] block uppercase">Track ID</span>
                  <span className="font-mono text-white">#{selectedRecord.track_id}</span>
                </div>
              </div>

              {selectedRecord.diagnostics && (
                <div className="p-2.5 bg-zinc-900 border border-zinc-800 rounded text-zinc-400 text-[11px]">
                  <strong>Diagnostics:</strong> {selectedRecord.diagnostics}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setNewPlate(selectedRecord.plate_number);
                  setSelectedRecord(null);
                  setShowAddModal(true);
                }}
              >
                Add to Watchlist
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Add Watchlist Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-md max-w-md w-full p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
              Add Target Plate to Watchlist
            </h3>
            <form onSubmit={handleAddWatchlist} className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Plate Number</label>
                <input
                  type="text"
                  required
                  value={newPlate}
                  onChange={(e) => setNewPlate(e.target.value)}
                  placeholder="e.g. DL01AB1234, 22BH1234AA"
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white uppercase font-mono focus:outline-none focus:border-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-zinc-400 mb-1">Category</label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                  >
                    <option value="SUSPECT">SUSPECT</option>
                    <option value="STOLEN">STOLEN</option>
                    <option value="BLOCKLIST">BLOCKLIST</option>
                    <option value="ALLOWLIST">ALLOWLIST</option>
                    <option value="CUSTOMS_FLAGGED">CUSTOMS FLAGGED</option>
                    <option value="WANTED">WANTED</option>
                    <option value="DIPLOMATIC">DIPLOMATIC</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-400 mb-1">Priority</label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Vehicle Details (Optional)</label>
                <input
                  type="text"
                  value={newModel}
                  onChange={(e) => setNewModel(e.target.value)}
                  placeholder="e.g. White Mahindra Scorpio, Black Fortuner"
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Alert Reason / Investigation Notes</label>
                <textarea
                  rows={2}
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="Reason for surveillance, FIR case number, or POI context..."
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white resize-none focus:outline-none focus:border-white"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="text-zinc-400 hover:text-white"
                >
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit">
                  Save Target
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Forensic Vehicle Plate Capture & Neural Recognition Modal */}
      {showCaptureModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-zinc-950 border border-zinc-800 rounded-md max-w-xl w-full p-5 space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <Car className="w-5 h-5 text-white" />
                <div>
                  <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                    Vehicle Number Plate Capture & Detect
                  </h3>
                  <p className="text-[11px] text-zinc-400">
                    High-precision neural OCR & plate localization (YOLO & EasyOCR)
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowCaptureModal(false)}
                className="text-zinc-500 hover:text-white text-lg leading-none"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleCaptureSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-zinc-300 font-medium mb-1">
                  Upload Vehicle Photo / Traffic CCTV Snapshot *
                </label>
                <input
                  type="file"
                  accept="image/*"
                  required
                  onChange={handleCaptureFileChange}
                  className="w-full text-zinc-400 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-zinc-800 file:text-white hover:file:bg-zinc-700 bg-black border border-zinc-800 rounded p-1.5 focus:outline-none"
                />
              </div>

              {capturePreview && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-zinc-400 uppercase font-semibold">
                    <span>
                      {captureResult?.annotated_frame_url ? 'Target Detection & Tactical Box (HUD)' : 'Snapshot Preview'}
                    </span>
                    {captureResult?.annotated_frame_url && (
                      <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Plate Target Square Locked
                      </span>
                    )}
                  </div>
                  <div className="relative rounded overflow-hidden border border-zinc-800 bg-black flex items-center justify-center max-h-72">
                    <img
                      src={captureResult?.annotated_frame_url ? getMediaUrl(captureResult.annotated_frame_url) : capturePreview}
                      alt="Vehicle Preview"
                      className="max-h-72 w-full object-contain"
                    />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-zinc-400 mb-1">Surveillance Camera ID</label>
                  <select
                    value={captureCameraId}
                    onChange={(e) => setCaptureCameraId(parseInt(e.target.value, 10))}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none"
                  >
                    <option value={1}>Camera #1 (Main Entrance Gate)</option>
                    <option value={2}>Camera #2 (North Perimeter)</option>
                    <option value={3}>Camera #3 (South Checkpost)</option>
                    <option value={4}>Camera #4 (Highway Toll Point)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-400 mb-1">Operational Notes (Optional)</label>
                  <input
                    type="text"
                    value={captureNotes}
                    onChange={(e) => setCaptureNotes(e.target.value)}
                    placeholder="e.g. Checkpost inspection, suspicious vehicle"
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none"
                  />
                </div>
              </div>

              {captureResult && (
                <div className={`p-3 rounded border text-xs space-y-2 ${
                  captureResult.success ? 'bg-zinc-900/90 border-zinc-700' : 'bg-red-950/40 border-red-800 text-red-300'
                }`}>
                  {captureResult.success ? (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                          Plate Detection Result
                        </span>
                        {captureResult.is_matched ? (
                          <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-red-600 text-white flex items-center gap-1 animate-pulse">
                            <ShieldAlert className="w-3 h-3" />
                            WATCHLIST MATCH ({captureResult.watchlist_category})
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 text-zinc-300 border border-zinc-700 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3 text-white" />
                            CLEARED / NO WATCHLIST HIT
                          </span>
                        )}
                      </div>

                      <div className="p-3 bg-black border-2 border-white/80 rounded flex items-center justify-between">
                        <div>
                          <div className="text-[10px] text-zinc-500 font-mono">RECOGNIZED PLATE NUMBER</div>
                          <div className="text-xl font-black font-mono tracking-widest text-white">
                            {captureResult.plate_number}
                          </div>
                          {captureResult.raw_text && captureResult.raw_text !== captureResult.plate_number && (
                            <div className="text-[10px] text-zinc-400 font-mono">
                              Raw OCR: {captureResult.raw_text}
                            </div>
                          )}
                        </div>

                        <div className="text-right">
                          <div className="text-[10px] text-zinc-500 font-mono">CONFIDENCE</div>
                          <div className="text-lg font-bold font-mono text-emerald-400">
                            {(captureResult.confidence * 100).toFixed(1)}%
                          </div>
                          <div className="text-[10px] text-zinc-400 font-mono">
                            {captureResult.validation_format || 'VALID RTO'}
                          </div>
                        </div>
                      </div>

                      {captureResult.plate_crop_url && (
                        <div className="flex items-center gap-3">
                          <div className="border border-zinc-700 rounded overflow-hidden bg-black p-1">
                            <div className="text-[9px] text-zinc-400 font-mono mb-0.5">PLATE CROP</div>
                            <img
                              src={getMediaUrl(captureResult.plate_crop_url)}
                              alt="Plate Crop"
                              className="h-10 w-28 object-cover rounded bg-zinc-900"
                            />
                          </div>

                          <div className="text-[11px] text-zinc-300 space-y-1 flex-1">
                            <div><strong>RTO Diagnostics:</strong> {captureResult.diagnostics || 'Verified against 36 Indian RTO State Formats'}</div>
                            <div><strong>Record ID:</strong> #{captureResult.record_id} saved with SHA-256 evidence proof</div>
                          </div>
                        </div>
                      )}

                      <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
                        <Button
                          variant="secondary"
                          size="xs"
                          type="button"
                          onClick={() => {
                            if (captureResult.plate_number) {
                              setNewPlate(captureResult.plate_number);
                              setShowCaptureModal(false);
                              setShowAddModal(true);
                            }
                          }}
                        >
                          Add {captureResult.plate_number} to Watchlist
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="font-semibold flex items-center gap-1.5">
                        <AlertCircle className="w-4 h-4 text-red-400" />
                        Plate Detection Failed
                      </div>
                      <div className="mt-1 text-zinc-300">{captureResult.error}</div>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-3 border-t border-zinc-800">
                <Button
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={() => setShowCaptureModal(false)}
                  className="text-zinc-400 hover:text-white"
                >
                  Close
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  type="submit"
                  disabled={captureSubmitting || !captureImageBase64}
                >
                  {captureSubmitting ? 'Detecting & Extracting OCR...' : 'Run Neural ANPR Detection'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
