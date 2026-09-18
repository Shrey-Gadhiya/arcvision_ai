import React, { useState } from 'react';
import { Incident } from '../types';
import { Badge } from '../components/common/Badge';

interface TimelineProps {
  incidents: Incident[];
  onSelectIncident: (inc: Incident) => void;
}

export const Timeline: React.FC<TimelineProps> = ({ incidents, onSelectIncident }) => {
  const [selectedHour, setSelectedHour] = useState<number | null>(null);

  const hours = Array.from({ length: 24 }, (_, i) => i);

  const filteredIncidents = selectedHour === null
    ? incidents
    : incidents.filter(i => new Date(i.detected_at).getHours() === selectedHour);

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Header */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
          Operational Threat Timeline
        </h1>
        <p className="text-xs text-zinc-400 mt-0.5">
          Chronological sequence of security incidents, breach correlation patterns, and hourly activity density.
        </p>
      </div>

      {/* 24-Hour Threat Activity Density Scrubber */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-3">
        <div className="flex items-center justify-between text-xs text-zinc-300">
          <span className="font-semibold uppercase tracking-wider text-[11px]">24-Hour Activity Density</span>
          <div className="flex items-center gap-2">
            {selectedHour !== null && (
              <button
                onClick={() => setSelectedHour(null)}
                className="text-xs text-zinc-400 hover:text-white hover:underline"
              >
                Clear Hour Filter
              </button>
            )}
            <span className="text-[11px] font-mono text-zinc-400">
              {selectedHour !== null ? `Filtered: ${selectedHour}:00 - ${selectedHour}:59` : 'All 24 Hours'}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-12 md:grid-cols-24 gap-1">
          {hours.map((h) => {
            const count = incidents.filter(i => new Date(i.detected_at).getHours() === h).length;
            const hasCrit = incidents.some(i => new Date(i.detected_at).getHours() === h && i.severity === 'CRITICAL');
            const isSelected = selectedHour === h;

            return (
              <button
                key={h}
                onClick={() => setSelectedHour(selectedHour === h ? null : h)}
                className={`p-1 rounded border text-center transition-colors flex flex-col items-center select-none ${
                  isSelected
                    ? 'border-white bg-zinc-800 text-white'
                    : 'border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white'
                }`}
              >
                <div className="text-[9px] font-mono text-zinc-400">{h}h</div>
                <div className="w-full h-8 rounded-sm my-1 flex items-end justify-center bg-black overflow-hidden">
                  <div
                    className={`w-full ${hasCrit ? 'bg-white' : count > 0 ? 'bg-zinc-400' : 'bg-transparent'}`}
                    style={{ height: `${Math.min(100, count * 35 + (count > 0 ? 15 : 0))}%` }}
                  />
                </div>
                <div className={`text-[10px] font-mono font-medium ${count > 0 ? 'text-white' : 'text-zinc-600'}`}>
                  {count}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Chronological Event Stream */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
          <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
            Chronological Events Dossier ({filteredIncidents.length})
          </h2>
          <span className="text-xs font-mono text-zinc-400">Time-Ordered Sequence</span>
        </div>

        <div className="relative border-l border-zinc-700 ml-3.5 space-y-3.5 py-1">
          {filteredIncidents.length === 0 ? (
            <div className="pl-6 text-xs text-zinc-500">
              No events recorded for this timeframe.
            </div>
          ) : (
            filteredIncidents.map((inc) => {
              const isCrit = inc.severity === 'CRITICAL';
              return (
                <div
                  key={inc.id}
                  onClick={() => onSelectIncident(inc)}
                  className="relative pl-6 cursor-pointer group"
                >
                  {/* Timeline node */}
                  <div
                    className={`absolute -left-2 top-2.5 w-4 h-4 rounded-full border flex items-center justify-center ${
                      isCrit
                        ? 'bg-white border-white text-black font-bold'
                        : 'bg-zinc-900 border-zinc-600 text-zinc-300'
                    }`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-current" />
                  </div>

                  <div className="p-3 rounded bg-zinc-900 border border-zinc-800 group-hover:border-zinc-600 transition-colors text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant={isCrit ? 'critical' : 'warning'}>
                          {inc.severity}
                        </Badge>
                        <span className="font-semibold text-white">{inc.title}</span>
                        <span className="text-[11px] font-mono text-zinc-400">{inc.incident_code}</span>
                      </div>
                      <span className="font-mono text-zinc-400 text-[11px]">
                        {new Date(inc.detected_at).toLocaleTimeString()}
                      </span>
                    </div>

                    <p className="text-xs text-zinc-300 font-sans leading-normal">
                      {inc.summary}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-zinc-400 pt-0.5 font-sans">
                      <span>{inc.location_name}</span>
                      <div className="flex items-center gap-2 font-mono">
                        <span>Threat Score: {inc.threat_score}/100</span>
                        <span className="text-white group-hover:underline">View Dossier &rarr;</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
