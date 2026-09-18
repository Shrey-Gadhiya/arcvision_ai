import React from 'react';
import {
  LayoutDashboard,
  Video,
  AlertTriangle,
  Camera,
  Shield,
  Car,
  UserCheck,
  Search,
  Clock,
  HardDrive,
  Activity,
  FileText,
  Settings as SettingsIcon,
  Eye,
  Film,
  Database,
  ChevronRight,
  Sliders,
  Cpu,
  Share2,
  MapPin
} from 'lucide-react';

export type PageId =
  | 'command'
  | 'live'
  | 'review'
  | 'tactical_map'
  | 'incidents'
  | 'cameras'
  | 'zones'
  | 'rules'
  | 'anpr'
  | 'face'
  | 'cross_camera'
  | 'investigation'
  | 'timeline'
  | 'evidence'
  | 'models'
  | 'storage'
  | 'health'
  | 'audit'
  | 'settings'
  | 'camera_detail';

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  count?: number;
  alert?: boolean;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  incidentCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  incidentCount
}) => {
  const navSections: NavSection[] = [
    {
      title: 'OPERATIONS',
      items: [
        { id: 'command', label: 'Command Center', icon: LayoutDashboard },
        { id: 'live', label: 'Live Grid', icon: Video },
        { id: 'review', label: 'Review Stream', icon: Eye },
        { id: 'tactical_map', label: 'Tactical Map', icon: MapPin },
        { id: 'incidents', label: 'Incidents', icon: AlertTriangle, count: incidentCount, alert: incidentCount > 0 },
      ]
    },
    {
      title: 'SURVEILLANCE & AI',
      items: [
        { id: 'cameras', label: 'Cameras', icon: Camera },
        { id: 'zones', label: 'Zones & Fences', icon: Shield },
        { id: 'rules', label: 'Behavior Rules', icon: Sliders },
        { id: 'anpr', label: 'ANPR', icon: Car },
        { id: 'face', label: 'Face Intelligence', icon: UserCheck },
        { id: 'cross_camera', label: 'Cross-Camera Re-ID', icon: Share2 },
        { id: 'models', label: 'AI Model Center', icon: Activity },
      ]
    },
    {
      title: 'INVESTIGATION',
      items: [
        { id: 'timeline', label: 'Playback Timeline', icon: Film },
        { id: 'investigation', label: 'Search', icon: Search },
        { id: 'evidence', label: 'Evidence', icon: HardDrive },
      ]
    },
    {
      title: 'SYSTEM',
      items: [
        { id: 'storage', label: 'Storage & Retention', icon: Database },
        { id: 'health', label: 'System Health', icon: Activity },
        { id: 'audit', label: 'Audit Trail', icon: FileText },
        { id: 'settings', label: 'Settings', icon: SettingsIcon },
      ]
    }
  ];

  return (
    <aside className="w-56 bg-[#09090b] border-r border-[#27272a] flex flex-col h-[calc(100vh-3.25rem)] select-none shrink-0">
      <div className="p-2.5 space-y-4 overflow-y-auto flex-1">
        {navSections.map((sec) => (
          <div key={sec.title} className="space-y-0.5">
            <div className="px-2 py-1 text-[10px] font-semibold tracking-wider text-zinc-500 uppercase">
              {sec.title}
            </div>
            <div className="space-y-0.5">
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentPage === item.id || (item.id === 'cameras' && currentPage === 'camera_detail');
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectPage(item.id as PageId)}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-zinc-900 text-white border border-zinc-700 shadow-sm'
                        : 'text-zinc-400 hover:text-white hover:bg-zinc-900/50'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-zinc-400'}`} />
                      <span className="truncate">{item.label}</span>
                    </div>

                    {item.count !== undefined && item.count > 0 && (
                      <span
                        className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-semibold ${
                          item.alert
                            ? 'bg-zinc-800 text-white border border-zinc-600'
                            : 'bg-zinc-800 text-zinc-300'
                        }`}
                      >
                        {item.count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Subtle Outpost Footer */}
      <div className="p-2.5 border-t border-[#27272a] bg-[#000000] text-[11px] text-zinc-400 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
          <span className="font-mono text-[10px] text-zinc-300">VMS ONLINE</span>
        </div>
        <span className="text-[10px] text-zinc-400 font-mono">v1.0</span>
      </div>
    </aside>
  );
};
