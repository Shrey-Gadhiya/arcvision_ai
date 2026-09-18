import React, { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { AuditLog } from '../types';
import { apiClient } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);

  const fetchLogs = async () => {
    try {
      const res = await apiClient.get('/audit/');
      setLogs(res.data);
    } catch (e) {
      // fallback
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <div>
          <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
            Operator Audit Trail
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Immutable log of user authentication, incident status changes, perimeter rule adjustments, and operator actions.
          </p>
        </div>

        <Button variant="secondary" size="sm" icon={<RefreshCw className="w-3 h-3" />} onClick={fetchLogs}>
          Refresh Audit Trail
        </Button>
      </div>

      {/* Audit Log Table */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800 font-semibold text-[11px] uppercase tracking-wider">
              <tr>
                <th className="p-3">TIMESTAMP</th>
                <th className="p-3">OPERATOR</th>
                <th className="p-3">ROLE</th>
                <th className="p-3">ACTION EVENT</th>
                <th className="p-3">TARGET RESOURCE</th>
                <th className="p-3 text-right">DETAILS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800 text-zinc-300">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-zinc-500 text-xs">
                    No operator audit events recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-zinc-900/50 transition-colors">
                    <td className="p-3 text-zinc-400 font-mono text-[11px]">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="p-3 font-medium text-white">{log.username}</td>
                    <td className="p-3">
                      <Badge variant="neutral">
                        {log.user_role}
                      </Badge>
                    </td>
                    <td className="p-3 font-mono text-white font-medium">
                      {log.action}
                    </td>
                    <td className="p-3 text-zinc-300 font-mono text-[11px]">
                      {log.resource_type} {log.resource_id ? `#${log.resource_id}` : ''}
                    </td>
                    <td className="p-3 text-right text-zinc-400 font-mono text-[11px] truncate max-w-xs" title={log.details_json}>
                      {log.details_json}
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
