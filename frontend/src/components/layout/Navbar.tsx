import React, { useState, useEffect } from 'react';
import { Shield, Volume2, VolumeX, RefreshCw, AlertCircle, LogOut, User, Trash2 } from 'lucide-react';

interface NavbarProps {
  activeThreatCount: number;
  onResetDemo: () => void;
  audioEnabled: boolean;
  onToggleAudio: () => void;
  currentUser?: string;
  currentRole?: string;
  onLogout?: () => void;
  onOpenPurgeModal?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeThreatCount,
  onResetDemo,
  audioEnabled,
  onToggleAudio,
  currentUser,
  currentRole,
  onLogout,
  onOpenPurgeModal,
}) => {
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setCurrentTime(now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-13 bg-[#09090b] border-b border-[#27272a] px-4 flex items-center justify-between select-none z-30 shrink-0">
      {/* Platform Title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-white/10 border border-white/20 flex items-center justify-center text-white">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold tracking-wide text-sm text-white">ARC VISION</span>
              <span className="text-[11px] text-zinc-400 font-medium hidden sm:inline">
                Surveillance Operations Platform
              </span>
            </div>
          </div>
        </div>

        {/* Sector Tag */}
        <div className="hidden md:flex items-center gap-2 pl-3 border-l border-[#27272a] text-xs text-zinc-400">
          <span>Sector 4 &bull; Border Surveillance Grid</span>
        </div>
      </div>

      {/* Critical Alert Indicator */}
      <div className="flex items-center gap-3">
        {activeThreatCount > 0 ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-600 text-white text-xs font-medium">
            <AlertCircle className="w-3.5 h-3.5 text-white shrink-0" />
            <span>{activeThreatCount} Active {activeThreatCount === 1 ? 'Incident' : 'Incidents'}</span>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-zinc-400">
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
            <span>Perimeter Clear</span>
          </div>
        )}

        {/* Clock */}
        <div className="text-xs font-mono text-zinc-300 tabular-nums px-2 hidden lg:block">
          {currentTime}
        </div>

        {/* Audio Alert Toggle */}
        <button
          onClick={onToggleAudio}
          title={audioEnabled ? "Mute audio alarms" : "Unmute audio alarms"}
          className={`p-1.5 rounded border text-xs flex items-center justify-center transition-colors ${
            audioEnabled
              ? 'bg-[#18181b] border-[#27272a] text-white hover:bg-zinc-800'
              : 'bg-transparent border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          {audioEnabled ? <Volume2 className="w-3.5 h-3.5 text-white" /> : <VolumeX className="w-3.5 h-3.5" />}
        </button>

        {/* Purge / Remove All Tracked Objects */}
        {onOpenPurgeModal && (
          <button
            onClick={onOpenPurgeModal}
            title="Purge / Remove All Tracked Objects"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-950/40 hover:bg-red-900/60 border border-red-800/80 hover:border-red-600 text-red-300 hover:text-white text-xs font-semibold transition-all shadow-sm cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5 text-red-400" />
            <span className="hidden sm:inline">Purge Tracks</span>
          </button>
        )}

        {/* Logged-in user */}
        {currentUser && (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#18181b] border border-[#27272a]">
            <User className="w-3 h-3 text-zinc-400" />
            <span className="text-xs text-zinc-200 font-medium">{currentUser}</span>
            {currentRole && (
              <span className="text-[10px] text-zinc-400 uppercase tracking-wide font-mono">{currentRole}</span>
            )}
          </div>
        )}

        {/* Sign Out */}
        {onLogout && (
          <button
            onClick={onLogout}
            title="Sign out"
            className="p-1.5 rounded bg-[#18181b] hover:bg-zinc-800 border border-[#27272a] hover:border-zinc-500 text-zinc-400 hover:text-white transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </header>
  );
};
