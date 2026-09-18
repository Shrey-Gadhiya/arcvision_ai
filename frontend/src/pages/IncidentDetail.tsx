import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  Lock,
  Download,
  Send,
  UserCheck,
  ShieldAlert,
  ChevronRight,
  Activity,
  History
} from 'lucide-react';
import { Incident, Evidence, IncidentStatus } from '../types';
import { apiClient, API_BASE_URL } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

interface IncidentDetailProps {
  incident: Incident;
  onBack: () => void;
  onRefresh: () => void;
}

const LIFECYCLE_STEPS: IncidentStatus[] = ['DETECTED', 'TRIAGED', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'CLOSED'];

export const IncidentDetail: React.FC<IncidentDetailProps> = ({ incident, onBack, onRefresh }) => {
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [newNote, setNewNote] = useState<string>('');
  const [assigneeName, setAssigneeName] = useState<string>(incident.assigned_to || '');
  const [isAssigning, setIsAssigning] = useState<boolean>(false);
  const [transitioningStatus, setTransitioningStatus] = useState<string | null>(null);
  const [resolutionReason, setResolutionReason] = useState<string>('');
  const [verificationResults, setVerificationResults] = useState<Record<number, any>>({});
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  const fetchEvidence = async () => {
    try {
      const res = await apiClient.get(`/evidence/?incident_id=${incident.id}`);
      setEvidenceList(res.data);
    } catch (e) {
      // fallback
    }
  };

  useEffect(() => {
    fetchEvidence();
    setAssigneeName(incident.assigned_to || '');
  }, [incident.id]);

  const handleTransition = async (targetStatus: IncidentStatus) => {
    setTransitioningStatus(targetStatus);
    try {
      await apiClient.post(`/incidents/${incident.id}/transition`, {
        target_status: targetStatus,
        reason: resolutionReason || undefined,
        note: `Transitioned to ${targetStatus}`
      });
      setResolutionReason('');
      onRefresh();
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'State transition rejected';
      alert(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setTransitioningStatus(null);
    }
  };

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assigneeName.trim()) return;
    setIsAssigning(true);
    try {
      await apiClient.post(`/incidents/${incident.id}/assign`, {
        assigned_to: assigneeName.trim()
      });
      onRefresh();
    } catch (e) {
      alert('Failed to assign operator');
    } finally {
      setIsAssigning(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    try {
      await apiClient.post(`/incidents/${incident.id}/notes`, { note: newNote });
      setNewNote('');
      onRefresh();
    } catch (e) {
      alert('Failed to save operator note');
    }
  };

  const handleVerifyEvidence = async (evidenceId: number) => {
    setIsVerifying(true);
    try {
      const res = await apiClient.post(`/evidence/${evidenceId}/verify`);
      setVerificationResults(prev => ({ ...prev, [evidenceId]: res.data }));
    } catch (e) {
      alert('Evidence hash verification failed or file unreachable');
    } finally {
      setIsVerifying(false);
    }
  };

  const notes = incident.operator_notes_json ? JSON.parse(incident.operator_notes_json) : [];
  const history = incident.transition_history_json ? JSON.parse(incident.transition_history_json) : [];

  // Determine available target transitions
  const getAvailableTransitions = (): IncidentStatus[] => {
    switch (incident.status) {
      case 'DETECTED':
      case 'NEW':
        return ['TRIAGED', 'ACKNOWLEDGED', 'CLOSED'];
      case 'TRIAGED':
        return ['ACKNOWLEDGED', 'INVESTIGATING', 'CLOSED'];
      case 'ACKNOWLEDGED':
        return ['INVESTIGATING', 'RESOLVED', 'CLOSED'];
      case 'INVESTIGATING':
        return ['RESOLVED', 'CLOSED'];
      case 'RESOLVED':
        return ['CLOSED', 'INVESTIGATING'];
      case 'CLOSED':
      case 'FALSE_POSITIVE':
        return ['INVESTIGATING'];
      default:
        return ['TRIAGED', 'ACKNOWLEDGED'];
    }
  };

  const availableTransitions = getAvailableTransitions();

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#09090b] border border-[#27272a] rounded-md px-4 py-3">
        <div className="flex items-center gap-3">
          <Button variant="secondary" size="xs" icon={<ArrowLeft className="w-3.5 h-3.5" />} onClick={onBack}>
            Back to Incidents
          </Button>

          <div className="h-5 w-px bg-[#27272a] hidden sm:block" />

          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-zinc-400">{incident.incident_code}</span>
              <h1 className="text-sm font-semibold text-white">{incident.title}</h1>
              <Badge variant={incident.severity === 'CRITICAL' ? 'critical' : 'warning'}>
                {incident.severity}
              </Badge>
              <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#18181b] border border-[#27272a] text-white">
                {incident.status}
              </span>
            </div>
            <div className="text-xs text-zinc-400 mt-0.5 font-sans">
              Detected {new Date(incident.detected_at).toLocaleString()} &bull; {incident.location_name}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {incident.assigned_to && (
            <div className="text-right text-xs">
              <span className="text-zinc-400 block text-[10px]">Assigned Operator</span>
              <span className="font-mono font-semibold text-white">{incident.assigned_to}</span>
            </div>
          )}
          <div className="text-right text-xs">
            <span className="text-zinc-400 block text-[10px]">Threat Score</span>
            <span className="font-mono font-semibold text-white">{incident.threat_score} / 100</span>
          </div>
        </div>
      </div>

      {/* Lifecycle Pipeline Progress Bar */}
      <div className="bg-[#09090b] border border-[#27272a] rounded-md p-3">
        <div className="flex items-center justify-between text-[11px] font-mono mb-2">
          <span className="text-zinc-400 uppercase tracking-wider">Incident Lifecycle State Machine</span>
          <span className="text-white font-semibold">{incident.status}</span>
        </div>
        <div className="grid grid-cols-6 gap-1.5">
          {LIFECYCLE_STEPS.map((step, idx) => {
            const isCurrent = incident.status === step;
            const currentIdx = LIFECYCLE_STEPS.indexOf(incident.status as IncidentStatus);
            const isPast = currentIdx >= 0 && idx <= currentIdx;
            return (
              <div
                key={step}
                className={`py-1.5 px-2 rounded text-center text-[10px] font-semibold tracking-wider transition-colors border ${
                  isCurrent
                    ? 'bg-white text-black border-white shadow-sm'
                    : isPast
                    ? 'bg-[#18181b] text-zinc-200 border-[#27272a]'
                    : 'bg-[#09090b] text-zinc-600 border-[#1f1f23]'
                }`}
              >
                {step}
              </div>
            );
          })}
        </div>

        {/* Transition Action Controls */}
        <div className="mt-3 pt-3 border-t border-[#27272a] flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-400">Available Actions:</span>
            {availableTransitions.map((tStatus) => (
              <Button
                key={tStatus}
                variant={tStatus === 'RESOLVED' || tStatus === 'CLOSED' ? 'primary' : 'secondary'}
                size="xs"
                disabled={transitioningStatus !== null}
                onClick={() => handleTransition(tStatus)}
              >
                {transitioningStatus === tStatus ? 'Processing...' : `Mark as ${tStatus}`}
              </Button>
            ))}
          </div>

          {/* Quick Assign Form */}
          <form onSubmit={handleAssign} className="flex items-center gap-1.5">
            <input
              type="text"
              value={assigneeName}
              onChange={(e) => setAssigneeName(e.target.value)}
              placeholder="Assign operator..."
              className="bg-black border border-[#27272a] rounded px-2.5 py-1 text-xs text-white placeholder-zinc-600 w-40 focus:outline-none focus:border-white"
            />
            <Button variant="secondary" size="xs" type="submit" disabled={isAssigning} icon={<UserCheck className="w-3 h-3" />}>
              Assign
            </Button>
          </form>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left 7 Cols: Incident Summary & Evidence Media */}
        <div className="lg:col-span-7 space-y-4">
          {/* Incident Summary Dossier Card */}
          <div className="bg-[#09090b] border border-[#27272a] rounded-md p-4 space-y-3">
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
              Incident Summary & Context
            </h2>
            <p className="text-xs text-zinc-300 leading-relaxed font-sans">
              {incident.summary}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[#27272a] text-xs">
              <div>
                <span className="text-[11px] text-zinc-400 block">Incident Type</span>
                <span className="font-mono text-zinc-200">{incident.incident_type}</span>
              </div>
              <div>
                <span className="text-[11px] text-zinc-400 block">Camera ID</span>
                <span className="font-mono text-zinc-200">Cam #{incident.camera_id}</span>
              </div>
              <div>
                <span className="text-[11px] text-zinc-400 block">Track Reference</span>
                <span className="font-mono text-zinc-200">Track #{incident.track_id || 'N/A'}</span>
              </div>
              <div>
                <span className="text-[11px] text-zinc-400 block">Correlated Events</span>
                <span className="font-mono text-zinc-200">{incident.correlated_event_ids || '1 event'}</span>
              </div>
            </div>
          </div>

          {/* Tamper-Evident Evidence Vault */}
          <div className="bg-[#09090b] border border-[#27272a] rounded-md p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-zinc-400" />
                <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Secured Evidence Artifacts
                </h2>
              </div>
              <span className="text-[11px] font-mono text-zinc-400">
                SHA-256 Chain of Custody
              </span>
            </div>

            {evidenceList.length === 0 ? (
              <div className="p-6 text-center text-xs text-zinc-400 bg-[#121215] rounded border border-[#27272a]">
                No forensic files linked to this incident.
              </div>
            ) : (
              <div className="space-y-3">
                {evidenceList.map((ev) => {
                  const verified = verificationResults[ev.id];
                  const isVideo = ev.file_type === 'CLIP';
                  return (
                    <div
                      key={ev.id}
                      className="p-3 bg-[#121215] border border-[#27272a] rounded space-y-2.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-black border border-[#27272a] text-zinc-300">
                            {ev.file_type}
                          </span>
                          <span className="text-xs font-medium text-white">{ev.file_path.split('/').pop()}</span>
                        </div>
                        <span className="text-[11px] font-mono text-zinc-400">
                          {Math.round(ev.file_size_bytes / 1024)} KB
                        </span>
                      </div>

                      {/* Media Preview */}
                      <div className="bg-black rounded overflow-hidden flex items-center justify-center max-h-[300px] border border-[#27272a]">
                        {isVideo ? (
                          <video
                            controls
                            src={`${API_BASE_URL}${ev.file_path}`}
                            className="w-full max-h-[280px] object-contain"
                          />
                        ) : (
                          <img
                            src={`${API_BASE_URL}${ev.file_path}`}
                            alt="Evidence Snapshot"
                            className="w-full max-h-[280px] object-contain"
                          />
                        )}
                      </div>

                      {/* Integrity Hash */}
                      <div className="pt-2 border-t border-[#27272a] flex flex-wrap items-center justify-between gap-2 text-[11px]">
                        <div className="font-mono text-zinc-400 truncate max-w-[320px]" title={ev.sha256_hash}>
                          <span className="text-zinc-500">SHA-256: </span>
                          {ev.sha256_hash}
                        </div>

                        <div className="flex items-center gap-2">
                          {verified ? (
                            <span className="text-white flex items-center gap-1 font-mono text-[10px]">
                              <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                              VERIFIED UNTAMPERED
                            </span>
                          ) : (
                            <Button
                              variant="secondary"
                              size="xs"
                              disabled={isVerifying}
                              onClick={() => handleVerifyEvidence(ev.id)}
                            >
                              Verify Hash
                            </Button>
                          )}
                          <a
                            href={`${API_BASE_URL}${ev.file_path}`}
                            download
                            className="p-1 rounded text-zinc-400 hover:text-white"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right 5 Cols: Operator Notes & Audit Trail */}
        <div className="lg:col-span-5 space-y-4">
          {/* Operator Triage Log */}
          <div className="bg-[#09090b] border border-[#27272a] rounded-md p-4 space-y-3">
            <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
              Operator Log & Triage Notes
            </h2>

            <form onSubmit={handleAddNote} className="space-y-2">
              <textarea
                rows={3}
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="Enter investigation observations, action taken, or patrol dispatch notes..."
                className="w-full bg-black border border-[#27272a] rounded p-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-white resize-none font-sans"
              />
              <div className="flex justify-end">
                <Button variant="primary" size="xs" type="submit" icon={<Send className="w-3 h-3" />}>
                  Append Log Note
                </Button>
              </div>
            </form>

            <div className="space-y-2 pt-2 border-t border-[#27272a] max-h-[260px] overflow-y-auto">
              {notes.length === 0 ? (
                <div className="text-xs text-zinc-500 text-center py-4">
                  No notes recorded yet.
                </div>
              ) : (
                notes.map((n: any, idx: number) => (
                  <div key={idx} className="p-2.5 rounded bg-[#121215] border border-[#27272a] text-xs space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-zinc-400">
                      <span className="font-medium text-white">{n.user || 'Operator'}</span>
                      <span className="font-mono">{new Date(n.timestamp || Date.now()).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-zinc-300 font-sans">{n.text || n.note}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Incident State Transition History */}
          <div className="bg-[#09090b] border border-[#27272a] rounded-md p-4 space-y-3">
            <div className="flex items-center gap-2">
              <History className="w-3.5 h-3.5 text-zinc-400" />
              <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
                State Transition Audit History
              </h2>
            </div>
            <div className="space-y-2.5 border-l-2 border-[#27272a] pl-3 text-xs ml-1 font-sans max-h-[220px] overflow-y-auto">
              <div className="space-y-0.5">
                <div className="text-[11px] font-mono text-zinc-400">
                  {new Date(incident.detected_at).toLocaleString()}
                </div>
                <div className="font-medium text-white">Incident Initialized [DETECTED]</div>
                <div className="text-zinc-500 text-[11px]">By automated spatial analytics rules engine</div>
              </div>

              {history.map((h: any, idx: number) => (
                <div key={idx} className="space-y-0.5">
                  <div className="text-[11px] font-mono text-zinc-400">
                    {new Date(h.timestamp).toLocaleString()}
                  </div>
                  <div className="font-medium text-white">
                    {h.from_status} &rarr; {h.to_status}
                  </div>
                  <div className="text-zinc-400 text-[11px]">
                    By <span className="text-white font-mono">{h.user}</span> {h.reason ? `(${h.reason})` : ''}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
