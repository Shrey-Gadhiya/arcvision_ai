import React, { useState, useEffect } from 'react';
import {
  Power,
  RefreshCw,
  Plus,
  Trash2,
  Sliders,
  Cpu,
  Eye,
  ShieldAlert,
  Play,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight
} from 'lucide-react';
import { Rule, RuleEventType, RuleSeverity, AnalyticsStatus } from '../types';
import { apiClient } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Tabs } from '../components/common/Tabs';

export const RuleEngine: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('rules');
  const [rules, setRules] = useState<Rule[]>([]);
  const [analyticsStatus, setAnalyticsStatus] = useState<AnalyticsStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // New Rule Modal
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [ruleName, setRuleName] = useState<string>('');
  const [ruleDesc, setRuleDesc] = useState<string>('');
  const [eventType, setEventType] = useState<RuleEventType>('LOITERING');
  const [severity, setSeverity] = useState<RuleSeverity>('HIGH');
  const [cooldownSec, setCooldownSec] = useState<number>(30);
  const [targetClasses, setTargetClasses] = useState<string>('person, car');
  const [dwellThreshold, setDwellThreshold] = useState<number>(15);
  const [speedThreshold, setSpeedThreshold] = useState<number>(0.35);
  const [nightSchedule, setNightSchedule] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Simulation / Dry-run state
  const [simClass, setSimClass] = useState<string>('person');
  const [simDwell, setSimDwell] = useState<number>(18);
  const [simSpeed, setSimSpeed] = useState<number>(0.15);
  const [simPacing, setSimPacing] = useState<number>(0);
  const [simNight, setSimNight] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<any>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  const fetchCoreData = async () => {
    setLoading(true);
    try {
      const [rulesRes, statusRes] = await Promise.all([
        apiClient.get('/rules/'),
        apiClient.get('/analytics/status')
      ]);
      setRules(rulesRes.data || []);
      setAnalyticsStatus(statusRes.data || null);
    } catch (e) {
      console.error('Failed to fetch rules/analytics:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCoreData();
  }, []);

  const handleToggle = async (ruleId: number) => {
    try {
      await apiClient.put(`/rules/${ruleId}/toggle`);
      fetchCoreData();
    } catch (e) {
      alert('Failed to toggle rule');
    }
  };

  const handleDeleteRule = async (ruleId: number) => {
    if (!window.confirm('Are you sure you want to delete this behavior rule?')) return;
    try {
      await apiClient.delete(`/rules/${ruleId}`);
      fetchCoreData();
    } catch (e) {
      alert('Failed to delete rule');
    }
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleName.trim()) return;

    setIsSubmitting(true);
    try {
      const parsedClasses = targetClasses.split(',').map((c) => c.trim().toLowerCase()).filter(Boolean);
      const conditions: any = {
        target_classes: parsedClasses,
        min_confidence: 0.35
      };

      if (eventType === 'LOITERING' || eventType === 'STATIONARY_OBJECT' || eventType === 'STATIONARY_VEHICLE') {
        conditions.min_dwell_sec = dwellThreshold;
      }
      if (eventType === 'RAPID_MOVEMENT') {
        conditions.speed_threshold = speedThreshold;
      }

      const schedule: any = nightSchedule
        ? { always: false, start_time: '20:00', end_time: '06:00' }
        : { always: true };

      await apiClient.post('/rules/', {
        name: ruleName.trim(),
        description: ruleDesc.trim() || undefined,
        event_type: eventType,
        severity: severity,
        camera_ids_json: '[]',
        conditions_json: JSON.stringify(conditions),
        schedule_json: JSON.stringify(schedule),
        cooldown_seconds: cooldownSec
      });

      setShowCreateModal(false);
      setRuleName('');
      setRuleDesc('');
      fetchCoreData();
    } catch (e) {
      alert('Failed to create behavioral rule');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSimulating(true);
    try {
      const res = await apiClient.post('/analytics/dry-run', {
        camera_id: 1,
        class_name: simClass,
        confidence: 0.90,
        dwell_sec: simDwell,
        is_stationary: simDwell >= 10,
        pacing_count: simPacing,
        speed: simSpeed,
        active_zones: [{ id: 1, name: 'Border Sterile Buffer', zone_type: 'RESTRICTED', loitering_time_sec: 15 }],
        tripwire_breaches: [],
        is_night_mode: simNight
      });
      setSimResult(res.data);
    } catch (e) {
      alert('Simulation error');
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
              Intelligent Video Rules & Behavior Analytics
            </h1>
            <Badge variant="neutral">Phase H Operational</Badge>
          </div>
          <p className="text-xs text-zinc-400 mt-0.5">
            Automated loitering, wrong-way movement, crowd density, stationary objects, night schedules, and explainable multi-signal correlation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
            onClick={fetchCoreData}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={<Plus className="w-3.5 h-3.5" />}
            onClick={() => setShowCreateModal(true)}
          >
            Create Behavior Rule
          </Button>
        </div>
      </div>

      {/* Main Tabs Container */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-hidden">
        <Tabs
          activeTab={activeTab}
          onChange={setActiveTab}
          className="px-4 pt-2 bg-zinc-950"
          tabs={[
            { id: 'rules', label: 'Active Behavior Rules', count: rules.length },
            { id: 'analyzers', label: 'Modular Behavior Analyzers', count: analyticsStatus?.total_analyzers || 11 },
            { id: 'simulator', label: 'Rule Simulator & Dry-Run' }
          ]}
        />

        <div className="p-4">
          {/* TAB 1: ACTIVE BEHAVIOR RULES */}
          {activeTab === 'rules' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>Deterministic rules evaluated in real-time on active object trajectories.</span>
                <span>{rules.filter(r => r.is_active).length} of {rules.length} active</span>
              </div>

              <div className="space-y-2.5">
                {rules.map((rule) => {
                  const isCrit = rule.severity === 'CRITICAL';
                  const isHigh = rule.severity === 'HIGH';
                  let condObj: any = {};
                  try {
                    condObj = JSON.parse(rule.conditions_json);
                  } catch (e) {}

                  return (
                    <div
                      key={rule.id}
                      className={`p-3.5 rounded border transition-all ${
                        rule.is_active
                          ? 'bg-zinc-900/60 border-zinc-700'
                          : 'bg-zinc-950 border-zinc-800/80 opacity-60'
                      }`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <Badge variant={isCrit ? 'critical' : isHigh ? 'warning' : 'neutral'}>
                            {rule.severity}
                          </Badge>
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-xs font-semibold text-white">{rule.name}</h3>
                              <span className="font-mono text-[10px] text-zinc-400 bg-black px-1.5 py-0.5 rounded border border-zinc-800">
                                {rule.event_type}
                              </span>
                            </div>
                            {rule.description && (
                              <p className="text-[11px] text-zinc-400 mt-0.5">{rule.description}</p>
                            )}
                            <div className="flex items-center gap-3 text-[10px] text-zinc-500 font-mono mt-1">
                              {condObj.target_classes && (
                                <span>Classes: {condObj.target_classes.join(', ')}</span>
                              )}
                              {condObj.min_dwell_sec && (
                                <span>Dwell: &ge;{condObj.min_dwell_sec}s</span>
                              )}
                              <span>Cooldown: {rule.cooldown_seconds}s</span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <Button
                            variant={rule.is_active ? 'primary' : 'secondary'}
                            size="xs"
                            icon={<Power className="w-3 h-3" />}
                            onClick={() => handleToggle(rule.id)}
                          >
                            {rule.is_active ? 'Active' : 'Disabled'}
                          </Button>
                          <Button
                            variant="ghost"
                            size="xs"
                            icon={<Trash2 className="w-3 h-3 text-zinc-400 hover:text-white" />}
                            onClick={() => handleDeleteRule(rule.id)}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 2: MODULAR BEHAVIOR ANALYZERS */}
          {activeTab === 'analyzers' && (
            <div className="space-y-4 text-xs">
              <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md flex items-center justify-between text-zinc-300">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-white shrink-0" />
                  <span>
                    <strong>Zero-Duplicate Architecture:</strong> Behavior analyzers execute synchronously on cached trajectory kinematics without spawning redundant detection passes.
                  </span>
                </div>
                <Badge variant="success">Engine Ready</Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {analyticsStatus?.analyzers &&
                  Object.entries(analyticsStatus.analyzers).map(([key, a]: [string, any]) => (
                    <div key={key} className="bg-zinc-900/60 border border-zinc-800 rounded p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white text-xs">{a.name}</span>
                        <Badge variant="success">{a.status}</Badge>
                      </div>
                      <div className="text-[11px] font-mono text-zinc-400">
                        <div>Event: <span className="text-zinc-300">{a.event_type}</span></div>
                        <div>Evaluations: <span className="text-white">{a.total_evaluations}</span></div>
                        <div>Events Fired: <span className="text-white">{a.total_events_generated}</span></div>
                      </div>
                    </div>
                  ))}

                {/* ML Action Transformer Slot */}
                <div className="bg-zinc-900/30 border border-dashed border-zinc-800 rounded p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-zinc-400 text-xs">ML Action Recognition</span>
                    <Badge variant="neutral">NOT_CONFIGURED</Badge>
                  </div>
                  <p className="text-[11px] text-zinc-500">
                    Spatial-temporal video transformer placeholder for future deep pose/action classification.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: RULE SIMULATOR */}
          {activeTab === 'simulator' && (
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 text-xs">
              <form onSubmit={handleRunSimulation} className="md:col-span-6 bg-zinc-900 border border-zinc-800 rounded p-4 space-y-3.5">
                <h3 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-white" /> Kinematic Telemetry Test Input
                </h3>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-zinc-400 mb-1">Target Class</label>
                    <select
                      value={simClass}
                      onChange={(e) => setSimClass(e.target.value)}
                      className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white"
                    >
                      <option value="person">person</option>
                      <option value="car">car</option>
                      <option value="truck">truck</option>
                      <option value="backpack">backpack</option>
                      <option value="suitcase">suitcase</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-zinc-400 mb-1">Dwell Time: {simDwell}s</label>
                    <input
                      type="range"
                      min="2"
                      max="60"
                      value={simDwell}
                      onChange={(e) => setSimDwell(parseInt(e.target.value, 10))}
                      className="w-full accent-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-zinc-400 mb-1">Velocity: {simSpeed.toFixed(2)} u/s</label>
                    <input
                      type="range"
                      min="0.05"
                      max="0.80"
                      step="0.05"
                      value={simSpeed}
                      onChange={(e) => setSimSpeed(parseFloat(e.target.value))}
                      className="w-full accent-white"
                    />
                  </div>

                  <div>
                    <label className="block text-zinc-400 mb-1">Pacing Direction Reversals</label>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      value={simPacing}
                      onChange={(e) => setSimPacing(parseInt(e.target.value, 10))}
                      className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="checkbox"
                    id="simNight"
                    checked={simNight}
                    onChange={(e) => setSimNight(e.target.checked)}
                    className="accent-white"
                  />
                  <label htmlFor="simNight" className="text-zinc-300">Simulate Night Schedule Active</label>
                </div>

                <div className="pt-2">
                  <Button
                    variant="primary"
                    size="sm"
                    type="submit"
                    icon={<Play className="w-3.5 h-3.5" />}
                    disabled={isSimulating}
                  >
                    {isSimulating ? 'Evaluating...' : 'Run Kinematics Test'}
                  </Button>
                </div>
              </form>

              {/* Simulation Results Output */}
              <div className="md:col-span-6 bg-zinc-950 border border-zinc-800 rounded p-4 space-y-3 font-mono">
                <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Behavior Engine Evaluation Results
                </h3>

                {simResult ? (
                  <div className="space-y-2">
                    <div className="text-[11px] text-zinc-400">
                      Evaluated Track #{simResult.evaluated_track_id} &bull; Generated {simResult.events_count} Event(s)
                    </div>
                    {simResult.events.length === 0 ? (
                      <div className="p-4 rounded bg-zinc-900 text-zinc-500 text-xs">
                        No behavior thresholds exceeded for specified parameters.
                      </div>
                    ) : (
                      simResult.events.map((ev: any, idx: number) => (
                        <div key={idx} className="p-2.5 bg-zinc-900 border border-zinc-700 rounded space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-white text-xs">{ev.event_type}</span>
                            <Badge variant="warning">{ev.severity}</Badge>
                          </div>
                          <p className="text-[11px] text-zinc-300">{ev.details.summary}</p>
                        </div>
                      ))
                    )}
                  </div>
                ) : (
                  <p className="text-zinc-500 text-xs">
                    Adjust inputs and click "Run Kinematics Test" to verify behavior triggers.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* CREATE RULE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-950 border border-zinc-800 rounded-md max-w-lg w-full p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div>
                <h3 className="text-sm font-semibold text-white">Create Behavior Rule</h3>
                <p className="text-[11px] text-zinc-400 mt-0.5">Configure automated AI threat logic and response behavior.</p>
              </div>
              <button onClick={() => setShowCreateModal(false)} className="text-zinc-400 hover:text-white text-lg">×</button>
            </div>

            <form onSubmit={handleCreateRule} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Rule Name *</label>
                <input
                  type="text"
                  required
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  placeholder="e.g. Sterile Buffer Loitering Alert"
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Description / Tactical Guidance</label>
                <input
                  type="text"
                  value={ruleDesc}
                  onChange={(e) => setRuleDesc(e.target.value)}
                  placeholder="Flag stationary persons near security perimeter fence..."
                  className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-400 mb-1">Behavior Event Type</label>
                  <select
                    value={eventType}
                    onChange={(e) => setEventType(e.target.value as RuleEventType)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                  >
                    <option value="LOITERING">LOITERING</option>
                    <option value="ZONE_INTRUSION">ZONE_INTRUSION</option>
                    <option value="PERIMETER_BREACH">PERIMETER_BREACH</option>
                    <option value="VIRTUAL_FENCE_CROSSING">VIRTUAL_FENCE_CROSSING</option>
                    <option value="WRONG_WAY">WRONG_WAY</option>
                    <option value="STATIONARY_VEHICLE">STATIONARY_VEHICLE</option>
                    <option value="STATIONARY_OBJECT">STATIONARY_OBJECT</option>
                    <option value="RESTRICTED_ZONE_ACTIVITY">RESTRICTED_ZONE_ACTIVITY</option>
                    <option value="NIGHT_MOVEMENT">NIGHT_MOVEMENT</option>
                    <option value="CROWD_DENSITY">CROWD_DENSITY</option>
                    <option value="ABANDONED_OBJECT">ABANDONED_OBJECT</option>
                    <option value="REMOVED_OBJECT">REMOVED_OBJECT</option>
                    <option value="REPEATED_MOVEMENT">REPEATED_MOVEMENT</option>
                    <option value="RAPID_MOVEMENT">RAPID_MOVEMENT</option>
                    <option value="SUSPICIOUS_ROUTE">SUSPICIOUS_ROUTE</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-400 mb-1">Incident Severity</label>
                  <select
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value as RuleSeverity)}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-white"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-400 mb-1">Target Object Classes</label>
                  <input
                    type="text"
                    value={targetClasses}
                    onChange={(e) => setTargetClasses(e.target.value)}
                    placeholder="person, car, truck"
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono focus:outline-none focus:border-white"
                  />
                </div>

                <div>
                  <label className="block text-zinc-400 mb-1">Cooldown Duration</label>
                  <input
                    type="number"
                    min="5"
                    max="300"
                    value={cooldownSec}
                    onChange={(e) => setCooldownSec(parseInt(e.target.value, 10))}
                    className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono focus:outline-none focus:border-white"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="nightSched"
                  checked={nightSchedule}
                  onChange={(e) => setNightSchedule(e.target.checked)}
                  className="accent-white"
                />
                <label htmlFor="nightSched" className="text-zinc-300">Enforce Night-Time Schedule (20:00 - 06:00)</label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-zinc-800">
                <Button variant="ghost" size="sm" type="button" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Saving...' : 'Deploy Rule'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
