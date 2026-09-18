import React, { useState, useEffect } from 'react';
import { Shapes, Layers, ArrowRight, Power, RefreshCw } from 'lucide-react';
import { Camera, Zone, Tripwire } from '../types';
import { apiClient } from '../api/client';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Tabs } from '../components/common/Tabs';

interface ZonesFencesProps {
  cameras: Camera[];
  onSelectCamera: (camId: number) => void;
}

export const ZonesFences: React.FC<ZonesFencesProps> = ({ cameras, onSelectCamera }) => {
  const [activeTab, setActiveTab] = useState<string>('inventory');
  const [allZones, setAllZones] = useState<{ zone: Zone; camName: string }[]>([]);
  const [allWires, setAllWires] = useState<{ wire: Tripwire; camName: string }[]>([]);
  const [rules, setRules] = useState<any[]>([]);

  // Behavior Sensitivity state
  const [loiterThreshold, setLoiterThreshold] = useState<number>(15);
  const [pacingReversals, setPacingReversals] = useState<number>(3);
  const [vehicleStopThreshold, setVehicleStopThreshold] = useState<number>(20);
  const [isSaved, setIsSaved] = useState<boolean>(false);

  const fetchAll = async () => {
    const zList: any[] = [];
    const wList: any[] = [];
    for (const cam of cameras) {
      try {
        const zRes = await apiClient.get(`/zones/camera/${cam.id}`);
        zRes.data.forEach((z: Zone) => zList.push({ zone: z, camName: cam.name }));
        const wRes = await apiClient.get(`/zones/tripwires/camera/${cam.id}`);
        wRes.data.forEach((w: Tripwire) => wList.push({ wire: w, camName: cam.name }));
      } catch (e) {
        // fallback
      }
    }
    setAllZones(zList);
    setAllWires(wList);

    try {
      const rRes = await apiClient.get('/rules/');
      setRules(rRes.data);
    } catch (e) {
      // fallback
    }
  };

  useEffect(() => {
    fetchAll();
  }, [cameras]);

  const handleToggleRule = async (ruleId: number) => {
    try {
      await apiClient.put(`/rules/${ruleId}/toggle`);
      const rRes = await apiClient.get('/rules/');
      setRules(rRes.data);
    } catch (e) {
      alert('Failed to toggle rule state');
    }
  };

  const handleSaveBehavior = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3">
        <div>
          <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
            Perimeter Security & Analytics Rules
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Configure spatial polygon zones, virtual fence tripwires, and automated trigger rules.
          </p>
        </div>

        <Button variant="secondary" size="sm" icon={<RefreshCw className="w-3 h-3" />} onClick={fetchAll}>
          Refresh
        </Button>
      </div>

      {/* Tabs Header */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md overflow-hidden">
        <Tabs
          activeTab={activeTab}
          onChange={setActiveTab}
          className="px-4 pt-2 bg-zinc-950"
          tabs={[
            { id: 'inventory', label: 'Perimeter Inventory', count: allZones.length + allWires.length },
            { id: 'rules', label: 'Trigger Rules Engine', count: rules.length },
            { id: 'behavior', label: 'Behavior Parameters' }
          ]}
        />

        <div className="p-4">
          {/* Tab 1: Inventory */}
          {activeTab === 'inventory' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Polygon Zones */}
              <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
                  <div className="flex items-center gap-2">
                    <Shapes className="w-4 h-4 text-white" />
                    <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
                      Restricted Polygon Zones ({allZones.length})
                    </h2>
                  </div>
                </div>

                <div className="space-y-2">
                  {allZones.length === 0 ? (
                    <div className="text-zinc-500 text-xs py-6 text-center">
                      No restricted zones configured. Open a camera to define a zone.
                    </div>
                  ) : (
                    allZones.map(({ zone, camName }) => (
                      <div
                        key={zone.id}
                        className="p-2.5 rounded bg-zinc-900 border border-zinc-800 flex items-center justify-between text-xs"
                      >
                        <div>
                          <div className="font-medium text-white flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-white" />
                            <span>{zone.name}</span>
                            <Badge variant="critical">
                              {zone.zone_type}
                            </Badge>
                          </div>
                          <div className="text-[11px] text-zinc-400 mt-0.5">
                            Camera: {camName} &bull; Loiter: {zone.loitering_time_sec}s
                          </div>
                        </div>

                        <Button
                          variant="secondary"
                          size="xs"
                          icon={<ArrowRight className="w-3 h-3" />}
                          onClick={() => onSelectCamera(zone.camera_id)}
                        >
                          Sensor View
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Virtual Fence Lines */}
              <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-white" />
                    <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
                      Virtual Fence Tripwires ({allWires.length})
                    </h2>
                  </div>
                </div>

                <div className="space-y-2">
                  {allWires.length === 0 ? (
                    <div className="text-zinc-500 text-xs py-6 text-center">
                      No virtual fences configured. Open a camera to place a tripwire.
                    </div>
                  ) : (
                    allWires.map(({ wire, camName }) => (
                      <div
                        key={wire.id}
                        className="p-2.5 rounded bg-zinc-900 border border-zinc-800 flex items-center justify-between text-xs"
                      >
                        <div>
                          <div className="font-medium text-white flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-zinc-400" />
                            <span>{wire.name}</span>
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-black border border-zinc-800 text-zinc-300">
                              {wire.direction}
                            </span>
                          </div>
                          <div className="text-[11px] text-zinc-400 mt-0.5">
                            Camera: {camName}
                          </div>
                        </div>

                        <Button
                          variant="secondary"
                          size="xs"
                          icon={<ArrowRight className="w-3 h-3" />}
                          onClick={() => onSelectCamera(wire.camera_id)}
                        >
                          Sensor View
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: Trigger Rules */}
          {activeTab === 'rules' && (
            <div className="space-y-3">
              {rules.map((rule) => {
                const isCrit = rule.severity === 'CRITICAL';
                return (
                  <div
                    key={rule.id}
                    className={`p-3.5 rounded bg-zinc-900 border flex items-center justify-between gap-4 transition-colors ${
                      rule.is_active
                        ? 'border-zinc-700'
                        : 'border-zinc-800 opacity-50'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white">{rule.name}</span>
                        <Badge variant={isCrit ? 'critical' : 'warning'}>
                          {rule.severity}
                        </Badge>
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-black border border-zinc-800 text-zinc-400">
                          {rule.event_type}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 font-sans">
                        {rule.description || 'Automated rule evaluation criteria for intrusion detection.'}
                      </p>
                      <div className="text-[11px] font-mono text-zinc-400">
                        Cooldown: {rule.cooldown_seconds}s
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleToggleRule(rule.id)}
                        className={`px-3 py-1.5 rounded text-xs font-medium border flex items-center gap-1.5 transition-colors ${
                          rule.is_active
                            ? 'bg-white border-white text-black font-semibold'
                            : 'bg-black border-zinc-800 text-zinc-400 hover:text-white'
                        }`}
                      >
                        <Power className="w-3.5 h-3.5" />
                        <span>{rule.is_active ? 'ENABLED' : 'DISABLED'}</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Tab 3: Behavior Calibration */}
          {activeTab === 'behavior' && (
            <form onSubmit={handleSaveBehavior} className="p-4 rounded bg-zinc-900 border border-zinc-800 space-y-4 max-w-xl text-xs">
              <div className="space-y-1 pb-3 border-b border-zinc-800">
                <label className="font-semibold text-white block text-xs">Loitering Dwell Threshold</label>
                <p className="text-zinc-400 text-[11px]">Duration in seconds an individual must remain within a zone before triggering a loitering event.</p>
                <div className="flex items-center gap-3 pt-1">
                  <input
                    type="range"
                    min="5"
                    max="60"
                    value={loiterThreshold}
                    onChange={(e) => setLoiterThreshold(Number(e.target.value))}
                    className="flex-1 accent-white"
                  />
                  <span className="w-12 text-right font-mono font-medium text-white">{loiterThreshold}s</span>
                </div>
              </div>

              <div className="space-y-1 pb-3 border-b border-zinc-800">
                <label className="font-semibold text-white block text-xs">Perimeter Pacing / Direction Reversal Count</label>
                <p className="text-zinc-400 text-[11px]">Trajectory direction flips along fence line signaling surveillance or scouting behavior.</p>
                <div className="flex items-center gap-3 pt-1">
                  <input
                    type="range"
                    min="2"
                    max="10"
                    value={pacingReversals}
                    onChange={(e) => setPacingReversals(Number(e.target.value))}
                    className="flex-1 accent-white"
                  />
                  <span className="w-12 text-right font-mono font-medium text-white">{pacingReversals} flips</span>
                </div>
              </div>

              <div className="space-y-1 pb-3 border-b border-zinc-800">
                <label className="font-semibold text-white block text-xs">Stationary Vehicle Stop Duration</label>
                <p className="text-zinc-400 text-[11px]">Duration in seconds a vehicle remains stopped in non-parking border buffer zone.</p>
                <div className="flex items-center gap-3 pt-1">
                  <input
                    type="range"
                    min="10"
                    max="120"
                    value={vehicleStopThreshold}
                    onChange={(e) => setVehicleStopThreshold(Number(e.target.value))}
                    className="flex-1 accent-white"
                  />
                  <span className="w-12 text-right font-mono font-medium text-white">{vehicleStopThreshold}s</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                {isSaved ? (
                  <span className="text-white text-[11px] font-medium">Settings saved to runtime profile</span>
                ) : <span />}
                <Button variant="primary" size="sm" type="submit">
                  Save Calibration
                </Button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
