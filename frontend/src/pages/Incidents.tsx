import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { Incident } from '../types';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

interface IncidentsProps {
  incidents: Incident[];
  onSelectIncident: (inc: Incident) => void;
  onTriageIncident: (incId: number, status: string) => void;
}

export const Incidents: React.FC<IncidentsProps> = ({
  incidents,
  onSelectIncident,
  onTriageIncident
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filtered = incidents.filter((inc) => {
    if (statusFilter !== 'ALL' && inc.status !== statusFilter) return false;
    if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        inc.incident_code.toLowerCase().includes(q) ||
        inc.title.toLowerCase().includes(q) ||
        inc.location_name.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Header & Filter Controls */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
              Incident Management & Triage
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              Correlated security intrusions, perimeter breaches, and suspicious activity logs.
            </p>
          </div>

          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-zinc-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search code, title, location..."
              className="bg-black border border-zinc-800 rounded pl-8 pr-3 py-1.5 text-xs text-white placeholder-zinc-600 w-64 focus:outline-none focus:border-white"
            />
          </div>
        </div>

        {/* Filter Strip */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-zinc-800">
          <div className="flex flex-wrap gap-1">
            {['ALL', 'DETECTED', 'TRIAGED', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'CLOSED'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded text-xs transition-colors border ${
                  statusFilter === st
                    ? 'bg-white text-black border-white font-semibold'
                    : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700'
                }`}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 text-xs">
            <span className="text-zinc-400 mr-1">Severity:</span>
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-2 py-0.5 rounded text-[11px] border transition-colors ${
                  severityFilter === sev
                    ? 'bg-zinc-800 border-zinc-600 text-white font-semibold'
                    : 'border-transparent text-zinc-400 hover:text-white'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Dense Incidents Table */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase tracking-wider">
              <tr>
                <th className="p-3">SEVERITY</th>
                <th className="p-3">INCIDENT</th>
                <th className="p-3">LOCATION</th>
                <th className="p-3">DETECTED AT</th>
                <th className="p-3">THREAT SCORE</th>
                <th className="p-3">STATUS</th>
                <th className="p-3 text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/80 text-zinc-300">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-zinc-400 text-xs">
                    No incidents match your selected filters.
                  </td>
                </tr>
              ) : (
                filtered.map((inc) => (
                  <tr
                    key={inc.id}
                    className="hover:bg-zinc-900/50 cursor-pointer transition-colors"
                    onClick={() => onSelectIncident(inc)}
                  >
                    <td className="p-3">
                      <Badge
                        variant={
                          inc.severity === 'CRITICAL'
                            ? 'critical'
                            : inc.severity === 'HIGH'
                            ? 'warning'
                            : 'neutral'
                        }
                      >
                        {inc.severity}
                      </Badge>
                    </td>
                    <td className="p-3">
                      <div className="font-medium text-white">{inc.title}</div>
                      <div className="text-[11px] font-mono text-zinc-400">{inc.incident_code}</div>
                    </td>
                    <td className="p-3 text-zinc-300">
                      {inc.location_name}
                    </td>
                    <td className="p-3 font-mono text-zinc-400 text-[11px]">
                      {new Date(inc.detected_at).toLocaleString()}
                    </td>
                    <td className="p-3 font-mono font-medium">
                      <span className={inc.threat_score >= 80 ? 'text-white font-bold' : 'text-zinc-300'}>
                        {inc.threat_score} / 100
                      </span>
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-zinc-900 border border-zinc-800 text-zinc-300">
                        {inc.status}
                      </span>
                    </td>
                    <td className="p-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        {inc.status === 'NEW' && (
                          <Button
                            variant="secondary"
                            size="xs"
                            onClick={() => onTriageIncident(inc.id, 'ACKNOWLEDGED')}
                          >
                            Acknowledge
                          </Button>
                        )}
                        {inc.status === 'ACKNOWLEDGED' && (
                          <Button
                            variant="secondary"
                            size="xs"
                            onClick={() => onTriageIncident(inc.id, 'INVESTIGATING')}
                          >
                            Investigate
                          </Button>
                        )}
                        {inc.status !== 'RESOLVED' && (
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => onTriageIncident(inc.id, 'RESOLVED')}
                            className="text-zinc-400 hover:text-white"
                          >
                            Resolve
                          </Button>
                        )}
                        <Button
                          variant="secondary"
                          size="xs"
                          onClick={() => onSelectIncident(inc)}
                        >
                          Dossier
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
