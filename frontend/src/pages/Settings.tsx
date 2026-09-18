import React from 'react';
import { Lock, Users, CheckCircle2 } from 'lucide-react';
import { Badge } from '../components/common/Badge';

export const Settings: React.FC = () => {
  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Header */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
          Platform Security & RBAC Configuration
        </h1>
        <p className="text-xs text-zinc-400 mt-0.5">
          Role-Based Access Control clearance tiers, credential policies, and defense infrastructure parameters.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Role-Based Access Control (RBAC) */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-3 text-xs">
          <div className="flex items-center gap-2 pb-2 border-b border-zinc-800">
            <Users className="w-4 h-4 text-white" />
            <h2 className="font-semibold text-white uppercase tracking-wider">
              RBAC Clearance Tiers
            </h2>
          </div>

          <div className="space-y-2">
            {[
              { role: 'ADMIN', desc: 'Full root access, sensor commissioning, rule modifications, and user account creation.' },
              { role: 'COMMANDER', desc: 'Mission control oversight, incident escalation, and dispatch authority.' },
              { role: 'OPERATOR', desc: 'Real-time monitoring, incident acknowledgment, and active surveillance triage.' },
              { role: 'INVESTIGATOR', desc: 'Forensic telemetry queries, evidence export, and hash verification.' },
              { role: 'AUDITOR', desc: 'Read-only compliance audit trail inspection and chain-of-custody verification.' },
            ].map((r) => (
              <div key={r.role} className="p-2.5 rounded bg-zinc-900 border border-zinc-800 space-y-1">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-white">{r.role}</span>
                  <Badge variant="success">Active Tier</Badge>
                </div>
                <div className="text-[11px] text-zinc-400 font-sans">{r.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Security & System Controls */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-3 text-xs">
          <div className="flex items-center gap-2 pb-2 border-b border-zinc-800">
            <Lock className="w-4 h-4 text-white" />
            <h2 className="font-semibold text-white uppercase tracking-wider">
              Security Architecture Controls
            </h2>
          </div>

          <div className="space-y-2.5">
            <div className="p-3 rounded bg-zinc-900 border border-zinc-800 space-y-1">
              <div className="font-medium text-white flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                <span>Forensic SHA-256 Chain of Custody</span>
              </div>
              <p className="text-[11px] text-zinc-400 font-sans">
                All video clips and snapshots are hashed at capture time to guarantee evidence cannot be modified in storage.
              </p>
            </div>

            <div className="p-3 rounded bg-zinc-900 border border-zinc-800 space-y-1">
              <div className="font-medium text-white flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                <span>Fault-Isolated Camera Workers</span>
              </div>
              <p className="text-[11px] text-zinc-400 font-sans">
                Individual camera dropouts, network glitches, or RTSP timeouts do not degrade adjacent camera feeds.
              </p>
            </div>

            <div className="p-3 rounded bg-zinc-900 border border-zinc-800 space-y-1">
              <div className="font-medium text-white flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                <span>Local Air-Gapped Operation</span>
              </div>
              <p className="text-[11px] text-zinc-400 font-sans">
                Inference runs 100% on-premises on local CPU/GPU hardware without requiring external cloud connectivity.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
