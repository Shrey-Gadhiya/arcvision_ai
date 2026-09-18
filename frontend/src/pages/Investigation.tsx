import React, { useState, useEffect } from 'react';
import {
  Search,
  Sparkles,
  SlidersHorizontal,
  FolderLock,
  Play,
  Download,
  Film,
  Calendar,
  Clock,
  Filter,
  Plus,
  Trash2,
  FileText,
  Printer,
  ChevronRight,
  ShieldAlert,
  Car,
  User,
  AlertTriangle,
  Flame,
  Eye,
  Camera as CameraIcon,
  Tag,
  Share2,
  CheckCircle,
  Clock4,
  MapPin,
  ExternalLink
} from 'lucide-react';
import {
  Camera,
  InvestigationSearchResultItem,
  InvestigationCase,
  CaseFinding,
  ParsedSemanticQuery,
  NLSearchResponse,
  CaseTimelineResponse,
  CaseExportResponse
} from '../types';
import { apiClient } from '../api/client';
import { nvrApi } from '../api/nvr';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

interface InvestigationProps {
  cameras: Camera[];
  onSelectIncident: (inc: any) => void;
  onNavigateToMap?: (camId: number) => void;
}

type ModeTab = 'SEMANTIC_SEARCH' | 'FORENSIC_FILTERS' | 'CASE_DOSSIERS';

export const Investigation: React.FC<InvestigationProps> = ({
  cameras,
  onSelectIncident,
  onNavigateToMap
}) => {
  // Navigation & Mode Tab
  const [activeTab, setActiveTab] = useState<ModeTab>('SEMANTIC_SEARCH');

  // Semantic NL Search State
  const [nlQuery, setNlQuery] = useState<string>('');
  const [parsedQuery, setParsedQuery] = useState<ParsedSemanticQuery | null>(null);
  const [isNlSearching, setIsNlSearching] = useState<boolean>(false);

  // Structured Filter State
  const [selectedCam, setSelectedCam] = useState<string>('');
  const [objectClass, setObjectClass] = useState<string>('');
  const [trackId, setTrackId] = useState<string>('');
  const [severity, setSeverity] = useState<string>('');
  const [colorFilter, setColorFilter] = useState<string>('');
  const [plateFilter, setPlateFilter] = useState<string>('');
  const [faceFilter, setFaceFilter] = useState<string>('');
  const [minConfidence, setMinConfidence] = useState<number>(0.3);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  // Results State
  const [results, setResults] = useState<InvestigationSearchResultItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Case Dossier State
  const [cases, setCases] = useState<InvestigationCase[]>([]);
  const [selectedCase, setSelectedCase] = useState<InvestigationCase | null>(null);
  const [caseTimeline, setCaseTimeline] = useState<CaseTimelineResponse | null>(null);
  const [isLoadingCases, setIsLoadingCases] = useState<boolean>(false);
  const [caseSearchQuery, setCaseSearchQuery] = useState<string>('');

  // Case Modals
  const [showCreateCaseModal, setShowCreateCaseModal] = useState<boolean>(false);
  const [newCaseTitle, setNewCaseTitle] = useState<string>('');
  const [newCaseDesc, setNewCaseDesc] = useState<string>('');
  const [newCasePriority, setNewCasePriority] = useState<string>('MEDIUM');
  const [newCaseInvestigator, setNewCaseInvestigator] = useState<string>('Lead Investigator');
  const [newCaseHypothesis, setNewCaseHypothesis] = useState<string>('');
  const [newCaseTags, setNewCaseTags] = useState<string>('perimeter, suspect');

  // Pin Finding Modal
  const [showPinModal, setShowPinModal] = useState<boolean>(false);
  const [pinTargetItem, setPinTargetItem] = useState<InvestigationSearchResultItem | null>(null);
  const [pinTargetCaseId, setPinTargetCaseId] = useState<string>('');
  const [pinNotes, setPinNotes] = useState<string>('');

  // Playback & Export Modals
  const [previewItem, setPreviewItem] = useState<InvestigationSearchResultItem | null>(null);
  const [exportReportData, setExportReportData] = useState<CaseExportResponse | null>(null);
  const [showExportModal, setShowExportModal] = useState<boolean>(false);

  // Suggested Prompts
  const suggestedPrompts = [
    'White car speeding near Gate 2 yesterday afternoon',
    'Person in dark clothes loitering near perimeter at night',
    'Black SUV license plate MH12',
    'Fire or smoke detected near warehouse',
    'Person falling or slip accident today',
    'Unauthorized vehicle entering Loading Dock'
  ];

  // Fetch cases on mount & tab change
  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    setIsLoadingCases(true);
    try {
      const res = await apiClient.get('/investigation/cases');
      setCases(res.data.items || []);
      if (res.data.items && res.data.items.length > 0 && !selectedCase) {
        loadCaseDetail(res.data.items[0].id);
      }
    } catch (err) {
      console.error('Failed to load investigation cases', err);
    } finally {
      setIsLoadingCases(false);
    }
  };

  const loadCaseDetail = async (caseId: number) => {
    try {
      const [caseRes, timelineRes] = await Promise.all([
        apiClient.get(`/investigation/cases/${caseId}`),
        apiClient.get(`/investigation/cases/${caseId}/timeline`)
      ]);
      setSelectedCase(caseRes.data);
      setCaseTimeline(timelineRes.data);
    } catch (err) {
      console.error('Failed to load case details', err);
    }
  };

  // --- Natural Language Semantic Search ---
  const handleNlSearch = async (queryText?: string) => {
    const q = queryText !== undefined ? queryText : nlQuery;
    if (!q.trim()) return;

    setIsNlSearching(true);
    try {
      const res = await apiClient.post<NLSearchResponse>('/investigation/nl-search', {
        query: q,
        min_confidence: minConfidence,
        limit: 50
      });
      setParsedQuery(res.data.parsed_query);
      setResults(res.data.items || []);
      setTotalCount(res.data.total || 0);
      setHasSearched(true);
    } catch (err) {
      alert('Semantic search failed. Ensure backend service is running.');
    } finally {
      setIsNlSearching(false);
    }
  };

  // --- Structured Filter Search ---
  const handleStructuredSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsNlSearching(true);

    try {
      const payload: Record<string, any> = {
        limit: 50,
        min_confidence: minConfidence
      };
      if (selectedCam) payload.camera_id = Number(selectedCam);
      if (objectClass) payload.object_class = objectClass;
      if (trackId) payload.track_id = Number(trackId);
      if (severity) payload.severity = severity;
      if (colorFilter) payload.color = colorFilter;
      if (plateFilter) payload.plate_number = plateFilter;
      if (faceFilter) payload.face_name = faceFilter;
      if (startDate) payload.start_time = new Date(startDate).toISOString();
      if (endDate) payload.end_time = new Date(endDate).toISOString();

      const res = await apiClient.post('/investigation/search', payload);
      setResults(res.data.items || []);
      setTotalCount(res.data.total || 0);
      setHasSearched(true);
      setParsedQuery(null);
    } catch (err) {
      alert('Forensic structured query failed');
    } finally {
      setIsNlSearching(false);
    }
  };

  // --- Case Dossier Actions ---
  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseTitle.trim()) return;

    try {
      const tagsArray = newCaseTags.split(',').map((t) => t.trim()).filter(Boolean);
      const res = await apiClient.post('/investigation/cases', {
        title: newCaseTitle,
        description: newCaseDesc,
        priority: newCasePriority,
        lead_investigator: newCaseInvestigator,
        hypothesis: newCaseHypothesis,
        tags: tagsArray
      });

      setShowCreateCaseModal(false);
      setNewCaseTitle('');
      setNewCaseDesc('');
      setNewCaseHypothesis('');
      await fetchCases();
      loadCaseDetail(res.data.id);
    } catch (err) {
      alert('Failed to create investigation case');
    }
  };

  const handleUpdateCaseStatus = async (status: string) => {
    if (!selectedCase) return;
    try {
      const res = await apiClient.put(`/investigation/cases/${selectedCase.id}`, { status });
      setSelectedCase(res.data);
      fetchCases();
    } catch (err) {
      alert('Failed to update case status');
    }
  };

  const handleUpdateCaseHypothesis = async (hypothesis: string) => {
    if (!selectedCase) return;
    try {
      const res = await apiClient.put(`/investigation/cases/${selectedCase.id}`, { hypothesis });
      setSelectedCase(res.data);
    } catch (err) {
      alert('Failed to save hypothesis');
    }
  };

  const handlePinItemToCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pinTargetItem || !pinTargetCaseId) return;

    try {
      await apiClient.post(`/investigation/cases/${pinTargetCaseId}/findings`, {
        item_type: pinTargetItem.result_type,
        reference_id: pinTargetItem.id,
        camera_id: pinTargetItem.camera_id,
        timestamp: pinTargetItem.timestamp,
        title: `${pinTargetItem.result_type}: ${pinTargetItem.object_class || 'Observation'} (${pinTargetItem.camera_name || 'Sensor'})`,
        notes: pinNotes || `Pinned from search: ${pinTargetItem.matched_reasons?.join(', ') || 'Forensic search match'}`,
        metadata: {
          ...pinTargetItem.details,
          match_score: pinTargetItem.match_score,
          confidence: pinTargetItem.confidence
        },
        thumbnail_url: pinTargetItem.thumbnail_url
      });

      setShowPinModal(false);
      setPinNotes('');
      setPinTargetItem(null);
      alert('Finding successfully pinned to Investigation Case Dossier!');
      if (selectedCase && selectedCase.id === Number(pinTargetCaseId)) {
        loadCaseDetail(selectedCase.id);
      }
    } catch (err) {
      alert('Failed to pin finding to case');
    }
  };

  const handleRemoveFinding = async (findingId: number) => {
    if (!selectedCase) return;
    if (!confirm('Remove this finding from the case dossier?')) return;

    try {
      await apiClient.delete(`/investigation/cases/${selectedCase.id}/findings/${findingId}`);
      loadCaseDetail(selectedCase.id);
      fetchCases();
    } catch (err) {
      alert('Failed to remove finding');
    }
  };

  const handleExportCase = async (caseId: number) => {
    try {
      const res = await apiClient.get<CaseExportResponse>(`/investigation/cases/${caseId}/export`);
      setExportReportData(res.data);
      setShowExportModal(true);
    } catch (err) {
      alert('Failed to generate case export report');
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-full text-zinc-200">
      {/* Top Header & Navigation Banner */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded-md">
              <Sparkles className="w-5 h-5 text-blue-400 animate-pulse" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-white tracking-wide uppercase flex items-center gap-2">
                Forensic Investigation & Multimodal Video Search
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                AI Natural Language Semantic Queries • Cross-Camera Timeline Reconstruction • Case Dossiers
              </p>
            </div>
          </div>
        </div>

        {/* Mode Switcher Tabs */}
        <div className="flex items-center bg-zinc-900 border border-zinc-800 rounded-md p-1 gap-1">
          <button
            onClick={() => setActiveTab('SEMANTIC_SEARCH')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              activeTab === 'SEMANTIC_SEARCH'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Semantic Search</span>
          </button>

          <button
            onClick={() => setActiveTab('FORENSIC_FILTERS')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              activeTab === 'FORENSIC_FILTERS'
                ? 'bg-zinc-800 text-white'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Multi-Criteria Filters</span>
          </button>

          <button
            onClick={() => {
              setActiveTab('CASE_DOSSIERS');
              fetchCases();
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              activeTab === 'CASE_DOSSIERS'
                ? 'bg-zinc-800 text-white'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
            }`}
          >
            <FolderLock className="w-3.5 h-3.5 text-amber-400" />
            <span>Case Dossiers ({cases.length})</span>
          </button>
        </div>
      </div>

      {/* ======================================================== */}
      {/* TAB 1: AI NATURAL LANGUAGE SEMANTIC SEARCH               */}
      {/* ======================================================== */}
      {activeTab === 'SEMANTIC_SEARCH' && (
        <div className="space-y-4">
          {/* Natural Language Search Box */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-3">
            <div className="relative">
              <input
                type="text"
                value={nlQuery}
                onChange={(e) => setNlQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleNlSearch();
                }}
                placeholder="Ask in natural language (e.g. 'white car speeding near Gate 2 yesterday afternoon', 'person in red hoodie at 2am')..."
                className="w-full bg-black border border-zinc-700 hover:border-zinc-500 focus:border-blue-500 rounded-lg pl-11 pr-32 py-3.5 text-sm text-white placeholder-zinc-500 focus:outline-none transition-colors shadow-inner"
              />
              <Sparkles className="w-5 h-5 text-blue-400 absolute left-3.5 top-3.5" />
              <div className="absolute right-2 top-2 flex items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleNlSearch()}
                  disabled={isNlSearching || !nlQuery.trim()}
                  icon={<Search className="w-3.5 h-3.5" />}
                >
                  {isNlSearching ? 'Searching...' : 'Run AI Search'}
                </Button>
              </div>
            </div>

            {/* Quick Suggested Prompts Chips */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Suggestions:</span>
              {suggestedPrompts.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setNlQuery(p);
                    handleNlSearch(p);
                  }}
                  className="px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-600 rounded-full text-[11px] text-zinc-300 hover:text-white transition-colors"
                >
                  "{p}"
                </button>
              ))}
            </div>

            {/* Parsed Query Breakdown Badge */}
            {parsedQuery && (
              <div className="mt-3 p-3 bg-blue-950/20 border border-blue-900/40 rounded-md space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold text-blue-300">
                    <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                    <span>AI Query Interpretation (Confidence: {Math.round(parsedQuery.parser_confidence * 100)}%)</span>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-400">Parsed across 7 database tables</span>
                </div>

                <div className="flex flex-wrap items-center gap-1.5 text-xs">
                  {parsedQuery.object_classes.map((c) => (
                    <span key={c} className="px-2 py-0.5 bg-blue-900/40 border border-blue-700/50 rounded text-blue-200 text-[11px]">
                      Entity: <strong className="text-white capitalize">{c}</strong>
                    </span>
                  ))}
                  {parsedQuery.colors.map((c) => (
                    <span key={c} className="px-2 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-zinc-200 text-[11px]">
                      Color: <strong className="text-white capitalize">{c}</strong>
                    </span>
                  ))}
                  {parsedQuery.incident_types.map((inc) => (
                    <span key={inc} className="px-2 py-0.5 bg-red-900/40 border border-red-700/50 rounded text-red-200 text-[11px]">
                      Threat: <strong className="text-white">{inc}</strong>
                    </span>
                  ))}
                  {parsedQuery.plate_numbers.map((plt) => (
                    <span key={plt} className="px-2 py-0.5 bg-amber-900/40 border border-amber-700/50 rounded text-amber-200 text-[11px] font-mono">
                      Plate: <strong className="text-white">{plt}</strong>
                    </span>
                  ))}
                  {parsedQuery.locations.map((loc) => (
                    <span key={loc} className="px-2 py-0.5 bg-emerald-900/40 border border-emerald-700/50 rounded text-emerald-200 text-[11px]">
                      Location: <strong className="text-white">{loc}</strong>
                    </span>
                  ))}
                  {parsedQuery.temporal_expression && (
                    <span className="px-2 py-0.5 bg-purple-900/40 border border-purple-700/50 rounded text-purple-200 text-[11px]">
                      Time: <strong className="text-white">{parsedQuery.temporal_expression}</strong>
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 2: FORENSIC MULTI-ATTRIBUTE STRUCTURED FILTERS       */}
      {/* ======================================================== */}
      {activeTab === 'FORENSIC_FILTERS' && (
        <form onSubmit={handleStructuredSearch} className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {/* Camera Sensor */}
            <div>
              <label className="block text-zinc-400 mb-1 text-[11px] uppercase font-medium">Camera Sensor</label>
              <select
                value={selectedCam}
                onChange={(e) => setSelectedCam(e.target.value)}
                className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
              >
                <option value="">All Cameras</option>
                {cameras.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.group_name})
                  </option>
                ))}
              </select>
            </div>

            {/* Object Class */}
            <div>
              <label className="block text-zinc-400 mb-1 text-[11px] uppercase font-medium">Object Class</label>
              <select
                value={objectClass}
                onChange={(e) => setObjectClass(e.target.value)}
                className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
              >
                <option value="">All Object Classes</option>
                <option value="person">Person</option>
                <option value="car">Car / Sedan / SUV</option>
                <option value="truck">Truck / Van</option>
                <option value="bus">Bus</option>
                <option value="motorcycle">Motorcycle</option>
                <option value="bicycle">Bicycle</option>
              </select>
            </div>

            {/* Color Filter */}
            <div>
              <label className="block text-zinc-400 mb-1 text-[11px] uppercase font-medium">Vehicle / Object Color</label>
              <select
                value={colorFilter}
                onChange={(e) => setColorFilter(e.target.value)}
                className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
              >
                <option value="">Any Color</option>
                <option value="white">White</option>
                <option value="black">Black</option>
                <option value="silver">Silver / Grey</option>
                <option value="red">Red</option>
                <option value="blue">Blue</option>
                <option value="yellow">Yellow</option>
                <option value="green">Green</option>
              </select>
            </div>

            {/* License Plate */}
            <div>
              <label className="block text-zinc-400 mb-1 text-[11px] uppercase font-medium">License Plate Number</label>
              <input
                type="text"
                value={plateFilter}
                onChange={(e) => setPlateFilter(e.target.value)}
                placeholder="e.g. MH12DE1432"
                className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono placeholder-zinc-600 focus:outline-none focus:border-white"
              />
            </div>

            {/* Person Face Identity */}
            <div>
              <label className="block text-zinc-400 mb-1 text-[11px] uppercase font-medium">Face Identity / Name</label>
              <input
                type="text"
                value={faceFilter}
                onChange={(e) => setFaceFilter(e.target.value)}
                placeholder="e.g. John Doe, Suspect"
                className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white placeholder-zinc-600 focus:outline-none focus:border-white"
              />
            </div>

            {/* Threat Severity */}
            <div>
              <label className="block text-zinc-400 mb-1 text-[11px] uppercase font-medium">Threat Severity</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>

            {/* Start Date */}
            <div>
              <label className="block text-zinc-400 mb-1 text-[11px] uppercase font-medium">Start Date / Time</label>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white text-[11px]"
              />
            </div>

            {/* End Date */}
            <div>
              <label className="block text-zinc-400 mb-1 text-[11px] uppercase font-medium">End Date / Time</label>
              <input
                type="datetime-local"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white text-[11px]"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-zinc-800">
            <div className="flex items-center gap-3">
              <span className="text-zinc-400 text-[11px]">
                Min Confidence: <strong className="text-white font-mono">{Math.round(minConfidence * 100)}%</strong>
              </span>
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.05"
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                className="w-24 accent-blue-500 cursor-pointer"
              />
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                type="button"
                onClick={() => {
                  setSelectedCam('');
                  setObjectClass('');
                  setTrackId('');
                  setSeverity('');
                  setColorFilter('');
                  setPlateFilter('');
                  setFaceFilter('');
                  setStartDate('');
                  setEndDate('');
                  setMinConfidence(0.3);
                }}
              >
                Reset
              </Button>
              <Button
                variant="primary"
                size="sm"
                type="submit"
                disabled={isNlSearching}
                icon={<Search className="w-3.5 h-3.5" />}
              >
                {isNlSearching ? 'Querying...' : 'Execute Multi-Filter Search'}
              </Button>
            </div>
          </div>
        </form>
      )}

      {/* ======================================================== */}
      {/* SEARCH RESULTS SECTION (FOR TAB 1 & TAB 2)               */}
      {/* ======================================================== */}
      {(activeTab === 'SEMANTIC_SEARCH' || activeTab === 'FORENSIC_FILTERS') && hasSearched && (
        <div className="space-y-3">
          {/* Results Summary Bar */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-md px-4 py-2.5 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-blue-400" />
              <span className="font-semibold text-white uppercase tracking-wider">
                Matching Results ({totalCount} records found)
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-2 py-1 rounded text-xs ${viewMode === 'grid' ? 'bg-zinc-800 text-white font-semibold' : 'text-zinc-400 hover:text-white'}`}
              >
                Cards View
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`px-2 py-1 rounded text-xs ${viewMode === 'table' ? 'bg-zinc-800 text-white font-semibold' : 'text-zinc-400 hover:text-white'}`}
              >
                Table View
              </button>
            </div>
          </div>

          {results.length === 0 ? (
            <div className="bg-zinc-950 border border-zinc-800 rounded-md p-12 text-center text-zinc-500 text-xs">
              No matching records found across detections, incidents, plates, or evidence for the specified query.
            </div>
          ) : viewMode === 'grid' ? (
            /* Grid Card View */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {results.map((item) => {
                const isInc = item.result_type === 'INCIDENT';
                const isAnpr = item.result_type === 'ANPR';
                const isFace = item.result_type === 'FACE';
                const matchPct = item.match_score ? Math.round(item.match_score * 100) : 95;

                return (
                  <div
                    key={item.id}
                    className="bg-zinc-950 border border-zinc-800 hover:border-zinc-700 rounded-md p-3.5 space-y-3 flex flex-col justify-between transition-colors shadow-sm"
                  >
                    {/* Card Header */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <Badge
                          variant={isInc ? 'critical' : isAnpr ? 'warning' : isFace ? 'info' : 'neutral'}
                        >
                          {item.result_type}
                        </Badge>
                        <span className="text-[11px] font-semibold text-white capitalize">
                          {item.object_class || 'Observation'}
                        </span>
                      </div>

                      <div className="flex items-center gap-1 bg-blue-950/40 border border-blue-800/40 px-2 py-0.5 rounded text-[11px] font-mono text-blue-300">
                        <span>{matchPct}% Match</span>
                      </div>
                    </div>

                    {/* Thumbnail / Visual Crop */}
                    {item.thumbnail_url ? (
                      <div className="bg-black border border-zinc-800 rounded aspect-video overflow-hidden flex items-center justify-center relative">
                        <img
                          src={item.thumbnail_url.startsWith('http') ? item.thumbnail_url : `${apiClient.defaults.baseURL}/${item.thumbnail_url}`}
                          alt={item.id}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            // Fallback icon placeholder if image path is not direct
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      </div>
                    ) : (
                      <div className="bg-zinc-900 border border-zinc-800 rounded aspect-video flex flex-col items-center justify-center text-zinc-600 gap-1">
                        {isAnpr ? <Car className="w-8 h-8" /> : isFace ? <User className="w-8 h-8" /> : <CameraIcon className="w-8 h-8" />}
                        <span className="text-[10px]">Sensor Snapshot Stream</span>
                      </div>
                    )}

                    {/* Sensor Metadata */}
                    <div className="space-y-1.5 text-xs">
                      <div className="flex items-center justify-between text-zinc-400">
                        <span className="flex items-center gap-1 text-white font-medium">
                          <CameraIcon className="w-3 h-3 text-zinc-400" />
                          {item.camera_name || `Camera #${item.camera_id}`}
                        </span>
                        <span className="font-mono text-[11px] text-zinc-400">
                          {new Date(item.timestamp).toLocaleString()}
                        </span>
                      </div>

                      {/* Reasons pills */}
                      {item.matched_reasons && item.matched_reasons.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {item.matched_reasons.slice(0, 3).map((r, idx) => (
                            <span
                              key={idx}
                              className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-[10px] text-zinc-300"
                            >
                              ✓ {r}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Actions Toolbar */}
                    <div className="flex items-center justify-between pt-2 border-t border-zinc-900 text-xs">
                      <button
                        onClick={() => {
                          setPinTargetItem(item);
                          if (cases.length > 0) setPinTargetCaseId(String(cases[0].id));
                          setShowPinModal(true);
                        }}
                        className="flex items-center gap-1 text-amber-400 hover:text-amber-300 font-medium text-[11px]"
                      >
                        <FolderLock className="w-3.5 h-3.5" />
                        <span>Pin to Dossier</span>
                      </button>

                      <div className="flex items-center gap-1.5">
                        {isInc && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => onSelectIncident(item.details)}
                          >
                            Incident
                          </Button>
                        )}
                        {item.linked_recording && (
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => setPreviewItem(item)}
                            icon={<Play className="w-3 h-3" />}
                          >
                            Play
                          </Button>
                        )}
                        {onNavigateToMap && (
                          <button
                            onClick={() => onNavigateToMap(item.camera_id)}
                            title="Locate on Tactical Map"
                            className="p-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 rounded text-zinc-300 hover:text-white"
                          >
                            <MapPin className="w-3.5 h-3.5 text-blue-400" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Table View */
            <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase tracking-wider">
                  <tr>
                    <th className="p-3">TYPE</th>
                    <th className="p-3">TIMESTAMP</th>
                    <th className="p-3">SENSOR</th>
                    <th className="p-3">CLASSIFICATION / ATTRIBUTES</th>
                    <th className="p-3">MATCH SCORE</th>
                    <th className="p-3 text-right">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800 text-zinc-300">
                  {results.map((item) => (
                    <tr key={item.id} className="hover:bg-zinc-900/50 transition-colors">
                      <td className="p-3">
                        <Badge variant={item.result_type === 'INCIDENT' ? 'critical' : 'neutral'}>
                          {item.result_type}
                        </Badge>
                      </td>
                      <td className="p-3 font-mono text-[11px]">
                        {new Date(item.timestamp).toLocaleString()}
                      </td>
                      <td className="p-3 font-medium text-white">
                        {item.camera_name || `Camera #${item.camera_id}`}
                      </td>
                      <td className="p-3">
                        <div className="font-semibold text-white capitalize">{item.object_class || 'Observation'}</div>
                        <div className="text-[10px] text-zinc-400">{item.matched_reasons?.join(', ')}</div>
                      </td>
                      <td className="p-3 font-mono text-blue-400">
                        {item.match_score ? `${Math.round(item.match_score * 100)}%` : '95%'}
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => {
                              setPinTargetItem(item);
                              if (cases.length > 0) setPinTargetCaseId(String(cases[0].id));
                              setShowPinModal(true);
                            }}
                            className="text-amber-400 hover:text-amber-300 font-medium text-xs flex items-center gap-1"
                          >
                            <FolderLock className="w-3 h-3" />
                            <span>Pin</span>
                          </button>
                          {item.linked_recording && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => setPreviewItem(item)}
                              icon={<Play className="w-3 h-3" />}
                            >
                              Play
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 3: INVESTIGATION CASE DOSSIERS & WORKSPACE           */}
      {/* ======================================================== */}
      {activeTab === 'CASE_DOSSIERS' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Left Sidebar: Case List */}
          <div className="lg:col-span-4 bg-zinc-950 border border-zinc-800 rounded-md p-3.5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
              <div className="flex items-center gap-1.5">
                <FolderLock className="w-4 h-4 text-amber-400" />
                <span className="font-semibold text-white text-xs uppercase tracking-wider">
                  Active Cases ({cases.length})
                </span>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setShowCreateCaseModal(true)}
                icon={<Plus className="w-3.5 h-3.5" />}
              >
                New Case
              </Button>
            </div>

            {/* Case List */}
            <div className="space-y-2 max-h-[700px] overflow-y-auto">
              {cases.length === 0 ? (
                <div className="p-8 text-center text-zinc-500 text-xs">
                  No investigation cases yet. Click "+ New Case" to create a dossier.
                </div>
              ) : (
                cases.map((c) => {
                  const isSelected = selectedCase?.id === c.id;
                  return (
                    <div
                      key={c.id}
                      onClick={() => loadCaseDetail(c.id)}
                      className={`p-3 rounded-md border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-zinc-900 border-blue-500 shadow-md'
                          : 'bg-zinc-950/60 border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/40'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-mono text-[11px] font-semibold text-blue-400">{c.case_number}</span>
                        <Badge variant={c.status === 'OPEN' ? 'critical' : c.status === 'RESOLVED' ? 'success' : 'warning'}>
                          {c.status}
                        </Badge>
                      </div>
                      <h4 className="font-medium text-white text-xs line-clamp-1">{c.title}</h4>
                      <div className="flex items-center justify-between text-[11px] text-zinc-400 mt-2 font-mono">
                        <span>{c.lead_investigator}</span>
                        <span>{c.findings_count} Pinned Items</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Area: Selected Case Workspace */}
          <div className="lg:col-span-8 space-y-4">
            {selectedCase ? (
              <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-4">
                {/* Case Header */}
                <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b border-zinc-800">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-blue-400 bg-blue-950/50 border border-blue-800 px-2 py-0.5 rounded">
                        {selectedCase.case_number}
                      </span>
                      <h2 className="text-base font-semibold text-white">{selectedCase.title}</h2>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-zinc-400 mt-1">
                      <span>Lead: <strong className="text-zinc-200">{selectedCase.lead_investigator}</strong></span>
                      <span>•</span>
                      <span>Created: {new Date(selectedCase.created_at).toLocaleString()}</span>
                    </div>
                  </div>

                  {/* Actions & Status Dropdown */}
                  <div className="flex items-center gap-2">
                    <select
                      value={selectedCase.status}
                      onChange={(e) => handleUpdateCaseStatus(e.target.value)}
                      className="bg-zinc-900 border border-zinc-700 text-white text-xs rounded px-2.5 py-1 font-semibold"
                    >
                      <option value="OPEN">OPEN</option>
                      <option value="UNDER_INVESTIGATION">UNDER INVESTIGATION</option>
                      <option value="RESOLVED">RESOLVED</option>
                      <option value="CLOSED">CLOSED</option>
                    </select>

                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleExportCase(selectedCase.id)}
                      icon={<FileText className="w-3.5 h-3.5" />}
                    >
                      Export Dossier
                    </Button>
                  </div>
                </div>

                {/* Working Hypothesis & Notes Box */}
                <div className="bg-zinc-900/60 border border-zinc-800 rounded p-3 space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-zinc-300">
                    <span className="uppercase tracking-wider">Investigator Hypothesis & Working Theory</span>
                    <span className="text-[11px] text-zinc-500 font-mono">Live Editable</span>
                  </div>
                  <textarea
                    defaultValue={selectedCase.hypothesis || ''}
                    onBlur={(e) => handleUpdateCaseHypothesis(e.target.value)}
                    placeholder="Enter investigative hypothesis, suspect profile, and case summary notes..."
                    rows={2}
                    className="w-full bg-black border border-zinc-800 focus:border-blue-500 rounded p-2 text-xs text-zinc-200 focus:outline-none"
                  />
                </div>

                {/* Multi-Camera Chronological Trajectory Sequence */}
                {caseTimeline && caseTimeline.camera_sequence.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider block">
                      Reconstructed Multi-Camera Trajectory
                    </span>
                    <div className="flex flex-wrap items-center gap-2">
                      {caseTimeline.camera_sequence.map((seq, idx) => (
                        <React.Fragment key={seq.camera_id}>
                          <div className="bg-zinc-900 border border-zinc-700 px-3 py-1.5 rounded-md text-xs flex items-center gap-2">
                            <CameraIcon className="w-3.5 h-3.5 text-blue-400" />
                            <span className="font-medium text-white">{seq.camera_name}</span>
                            <span className="text-[10px] font-mono text-zinc-400 bg-zinc-800 px-1.5 py-0.5 rounded">
                              {seq.sightings_count} sights
                            </span>
                          </div>
                          {idx < caseTimeline.camera_sequence.length - 1 && (
                            <ChevronRight className="w-4 h-4 text-zinc-600" />
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                )}

                {/* Pinned Findings Gallery & Timeline */}
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-white uppercase tracking-wider">
                      Pinned Findings & Evidence ({selectedCase.findings?.length || 0})
                    </span>
                  </div>

                  {(!selectedCase.findings || selectedCase.findings.length === 0) ? (
                    <div className="p-8 bg-zinc-900/30 border border-zinc-800 rounded text-center text-zinc-500 text-xs">
                      No findings pinned to this case yet. Search for detections, incidents, or plates and click "Pin to Dossier".
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {selectedCase.findings.map((f) => (
                        <div
                          key={f.id}
                          className="bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 rounded p-3 flex items-start justify-between gap-3 text-xs"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <Badge variant="neutral">{f.item_type}</Badge>
                              <strong className="text-white">{f.title}</strong>
                              <span className="text-[11px] font-mono text-zinc-400">
                                {f.timestamp ? new Date(f.timestamp).toLocaleString() : ''}
                              </span>
                            </div>
                            <p className="text-zinc-400 text-xs">{f.notes}</p>
                          </div>

                          <button
                            onClick={() => handleRemoveFinding(f.id)}
                            className="text-zinc-500 hover:text-red-400 p-1"
                            title="Remove finding"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-zinc-950 border border-zinc-800 rounded-md p-16 text-center text-zinc-500 text-xs">
                Select an investigation case on the left or create a new dossier.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL: CREATE NEW INVESTIGATION CASE                     */}
      {/* ======================================================== */}
      {showCreateCaseModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleCreateCase} className="bg-zinc-950 border border-zinc-800 rounded-lg max-w-lg w-full p-5 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <FolderLock className="w-4 h-4 text-amber-400" />
                <h3 className="font-semibold text-white text-sm">Create Investigation Case Dossier</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateCaseModal(false)}
                className="text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-zinc-400 mb-1">Case Title *</label>
                <input
                  type="text"
                  required
                  value={newCaseTitle}
                  onChange={(e) => setNewCaseTitle(e.target.value)}
                  placeholder="e.g. North Gate Perimeter Intrusion"
                  className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white focus:outline-none focus:border-white"
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Priority Level</label>
                <select
                  value={newCasePriority}
                  onChange={(e) => setNewCasePriority(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white focus:outline-none focus:border-white"
                >
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Lead Investigator</label>
                <input
                  type="text"
                  value={newCaseInvestigator}
                  onChange={(e) => setNewCaseInvestigator(e.target.value)}
                  className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white focus:outline-none focus:border-white"
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Initial Hypothesis / Objective</label>
                <textarea
                  rows={2}
                  value={newCaseHypothesis}
                  onChange={(e) => setNewCaseHypothesis(e.target.value)}
                  placeholder="Working theory regarding suspect or vehicle movement..."
                  className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white focus:outline-none focus:border-white"
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={newCaseTags}
                  onChange={(e) => setNewCaseTags(e.target.value)}
                  placeholder="night_ops, suspect_car, perimeter"
                  className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white font-mono focus:outline-none focus:border-white"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-zinc-800">
              <Button variant="secondary" size="sm" type="button" onClick={() => setShowCreateCaseModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit">
                Initialize Case
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL: PIN FINDING TO CASE DOSSIER                       */}
      {/* ======================================================== */}
      {showPinModal && pinTargetItem && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handlePinItemToCase} className="bg-zinc-950 border border-zinc-800 rounded-lg max-w-md w-full p-5 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <FolderLock className="w-4 h-4 text-amber-400" />
                <h3 className="font-semibold text-white text-sm">Pin Finding to Case Dossier</h3>
              </div>
              <button type="button" onClick={() => setShowPinModal(false)} className="text-zinc-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="p-3 bg-zinc-900/60 rounded border border-zinc-800 space-y-1">
              <div className="text-white font-medium">{pinTargetItem.result_type}: {pinTargetItem.object_class || 'Observation'}</div>
              <div className="text-[11px] text-zinc-400 font-mono">
                Sensor: {pinTargetItem.camera_name} • {new Date(pinTargetItem.timestamp).toLocaleString()}
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-zinc-400 mb-1">Select Case Dossier *</label>
                {cases.length === 0 ? (
                  <div className="text-red-400 text-xs">
                    No cases available. Please create a case first.
                  </div>
                ) : (
                  <select
                    required
                    value={pinTargetCaseId}
                    onChange={(e) => setPinTargetCaseId(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white focus:outline-none focus:border-white"
                  >
                    {cases.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.case_number}: {c.title}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Investigator Finding Notes</label>
                <textarea
                  rows={3}
                  value={pinNotes}
                  onChange={(e) => setPinNotes(e.target.value)}
                  placeholder="Add context on why this detection / incident is relevant to the suspect..."
                  className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white focus:outline-none focus:border-white"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-zinc-800">
              <Button variant="secondary" size="sm" type="button" onClick={() => setShowPinModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit" disabled={cases.length === 0}>
                Pin Finding
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL: EXPORT DOSSIER BRIEFING REPORT PREVIEW            */}
      {/* ======================================================== */}
      {showExportModal && exportReportData && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg max-w-4xl w-full h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/50">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-400" />
                <h3 className="font-semibold text-white text-sm">
                  Investigation Dossier Briefing: {exportReportData.case.case_number}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    const printWin = window.open('', '_blank');
                    if (printWin) {
                      printWin.document.write(exportReportData.html_report);
                      printWin.document.close();
                      printWin.print();
                    }
                  }}
                  icon={<Printer className="w-3.5 h-3.5" />}
                >
                  Print / Save PDF
                </Button>
                <button
                  onClick={() => setShowExportModal(false)}
                  className="text-zinc-400 hover:text-white px-2 py-1"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-hidden p-2 bg-zinc-900">
              <iframe
                title="Investigation Dossier Report"
                srcDoc={exportReportData.html_report}
                className="w-full h-full border-0 rounded bg-black"
              />
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL: FORENSIC VIDEO PLAYBACK                           */}
      {/* ======================================================== */}
      {previewItem && previewItem.linked_recording && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-md max-w-2xl w-full p-4 space-y-3 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <div className="flex items-center gap-2">
                <Film className="w-4 h-4 text-white" />
                <span className="font-semibold text-white text-xs uppercase tracking-wider">
                  Forensic Playback: {previewItem.camera_name} ({previewItem.result_type})
                </span>
              </div>
              <button
                onClick={() => setPreviewItem(null)}
                className="text-zinc-400 hover:text-white text-xs px-2 py-1"
              >
                ✕ Close
              </button>
            </div>

            <div className="bg-black border border-zinc-800 rounded overflow-hidden aspect-video flex items-center justify-center relative">
              <video
                src={nvrApi.getSegmentStreamUrl(previewItem.linked_recording.id)}
                controls
                autoPlay
                className="w-full h-full object-contain"
              />
            </div>

            <div className="flex items-center justify-between text-xs text-zinc-400 font-mono pt-1">
              <div>
                Timestamp: <span className="text-white">{new Date(previewItem.timestamp).toLocaleString()}</span>
              </div>
              <a
                href={nvrApi.getSegmentDownloadUrl(previewItem.linked_recording.id)}
                download
                className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 border border-zinc-700 hover:border-zinc-500 rounded text-white text-xs font-medium"
              >
                <Download className="w-3.5 h-3.5" />
                Download MP4 Segment
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
