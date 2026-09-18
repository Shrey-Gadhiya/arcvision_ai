import React from 'react';
import { Volume2, VolumeX, AlertTriangle, Trash2 } from 'lucide-react';

interface AlertsHubProps {
  alerts: any[];
  onClearAlerts: () => void;
  audioEnabled: boolean;
  onToggleAudio: () => void;
  onSelectIncident: (inc: any) => void;
}

export const AlertsHub: React.FC<AlertsHubProps> = ({
  alerts,
  onClearAlerts,
  audioEnabled,
  onToggleAudio,
  onSelectIncident
}) => {
  return (
    <div className="p-4 space-y-4 font-mono">
      <div className="p-3 rounded bg-zinc-950 border border-zinc-800 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">REAL-TIME TACTICAL ALERTS HUB</h2>
          <p className="text-xs text-zinc-400">High-priority operational audio chimes, push alerts, and perimeter intrusion warnings</p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={onToggleAudio}
            className={`px-3 py-1.5 rounded text-xs flex items-center space-x-1.5 border ${
              audioEnabled
                ? 'bg-white text-black border-white font-semibold'
                : 'bg-zinc-900 border-zinc-800 text-zinc-400'
            }`}
          >
            {audioEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
            <span>{audioEnabled ? 'AUDIO ALARMS ON' : 'MUTED'}</span>
          </button>
          <button
            onClick={onClearAlerts}
            className="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 flex items-center space-x-1.5"
          >
            <Trash2 className="w-3.5 h-3.5 text-zinc-400 hover:text-white" />
            <span>DISMISS ALL</span>
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {alerts.length === 0 ? (
          <div className="text-center py-16 text-zinc-500 text-xs bg-zinc-950 rounded border border-zinc-800">
            ALL SECTORS SECURE. NO ACTIVE WARNINGS IN DISPATCH QUEUE.
          </div>
        ) : (
          alerts.map((alert, idx) => {
            const isCrit = alert.severity === 'CRITICAL';
            return (
              <div
                key={idx}
                onClick={() => alert.incident && onSelectIncident(alert.incident)}
                className={`p-3 rounded border flex items-center justify-between text-xs cursor-pointer transition-all ${
                  isCrit
                    ? 'bg-zinc-900 border-white text-white shadow-[0_0_10px_rgba(255,255,255,0.15)]'
                    : 'bg-zinc-950 border-zinc-800 text-zinc-200 hover:border-zinc-600'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-full ${isCrit ? 'bg-white text-black font-bold' : 'bg-zinc-800 text-white'}`}>
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="font-bold text-sm text-white flex items-center space-x-2">
                      <span>{alert.title}</span>
                      <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-black border border-current">
                        {alert.severity}
                      </span>
                    </div>
                    <div className="text-[11px] text-zinc-400">{alert.message}</div>
                  </div>
                </div>

                <div className="text-right text-[10px] text-zinc-400">
                  <div>{new Date(alert.timestamp).toLocaleTimeString()}</div>
                  <div className="text-white font-bold mt-0.5">VIEW DOSSIER →</div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
