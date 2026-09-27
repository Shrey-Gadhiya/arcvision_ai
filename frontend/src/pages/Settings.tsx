import React, { useState } from 'react';
import {
  Lock, Users, CheckCircle2, Shield, Plane, AlertTriangle,
  Navigation, Car, ScanFace, Eye, Sliders, Save
} from 'lucide-react';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const Settings: React.FC = () => {
  const [globalSettings, setGlobalSettings] = useState({
    drone_detection_global: true,
    face_concealment_global: true,
    one_way_lane_global: true,
    weapon_detection_global: true,
    people_counting_global: true,
    anpr_global: true,
    face_recognition_global: true,
    cross_camera_reid_global: true,
    min_detection_confidence: 0.35,
    face_match_threshold: 0.60,
    drone_radar_range_meters: 150,
    loitering_alert_sec: 15
  });

  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="p-4 space-y-4 max-w-full">
      {/* Header */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-sm font-semibold text-white uppercase tracking-wider">
            Global AI Threat Matrix & Defense Infrastructure Configuration
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Full-spectrum customization for aerial drones, face concealment, one-way lane violations, biometrics, weapons, and RBAC tiers.
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          icon={<Save className="w-3.5 h-3.5" />}
          onClick={handleSave}
        >
          {savedSuccess ? 'Saved Globally!' : 'Save Global Settings'}
        </Button>
      </div>

      {/* Global AI Perception Matrix */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-md p-4 space-y-4 text-xs">
        <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-white" />
            <h2 className="font-semibold text-white uppercase tracking-wider">
              Global AI Perception & Threat Detection Matrix
            </h2>
          </div>
          <Badge variant="success">All Detectors Online</Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            {
              key: 'drone_detection_global',
              title: 'SkyShield Drone & UAV Radar',
              desc: 'Neural optical trajectory & altitude classifier for low-altitude drones and quadcopters.',
              icon: Plane
            },
            {
              key: 'face_concealment_global',
              title: 'Facial Concealment & Masking Alerts',
              desc: 'Flags individuals obscuring identity via balaclavas, ski masks, bandanas, or deep hoods.',
              icon: AlertTriangle
            },
            {
              key: 'one_way_lane_global',
              title: 'One-Way Lane & Wrong-Way Driving',
              desc: 'Detects vehicles travelling against authorized traffic vector on perimeter roads and checkposts.',
              icon: Navigation
            },
            {
              key: 'weapon_detection_global',
              title: 'Firearms & Bladed Weapons',
              desc: 'Neural classification of handguns, rifles, knives, and suspicious unattended baggage.',
              icon: Shield
            },
            {
              key: 'people_counting_global',
              title: 'Bidirectional People & Vehicle Counting',
              desc: 'Line-crossing entry/exit counters with persistent live occupancy HUD overlay.',
              icon: Users
            },
            {
              key: 'anpr_global',
              title: 'Automated ANPR License Plates',
              desc: 'Real-time vehicle license plate OCR, formatting normalization, and hotlist matching.',
              icon: Car
            },
            {
              key: 'face_recognition_global',
              title: 'YuNet + SFace Biometric Watchlist',
              desc: '128-D facial feature embeddings with instant Wanted/Watchlist criminal alerts.',
              icon: ScanFace
            },
            {
              key: 'cross_camera_reid_global',
              title: 'Cross-Camera Re-ID & Journey Map',
              desc: 'Fuses multi-camera sensor observations to track global target paths across outposts.',
              icon: Eye
            }
          ].map((item) => {
            const Icon = item.icon;
            const isEnabled = (globalSettings as any)[item.key];
            return (
              <div
                key={item.key}
                onClick={() =>
                  setGlobalSettings({ ...globalSettings, [item.key]: !isEnabled })
                }
                className={`p-3 rounded border flex flex-col justify-between cursor-pointer transition-colors ${
                  isEnabled ? 'bg-zinc-900 border-zinc-700' : 'bg-black border-zinc-800 opacity-60'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Icon className={`w-4 h-4 ${isEnabled ? 'text-white' : 'text-zinc-500'}`} />
                    <input
                      type="checkbox"
                      checked={isEnabled}
                      onChange={() => {}}
                      className="w-3.5 h-3.5 rounded text-white bg-black border-zinc-700 accent-white cursor-pointer"
                    />
                  </div>
                  <div className={`font-semibold text-xs ${isEnabled ? 'text-white' : 'text-zinc-400'}`}>
                    {item.title}
                  </div>
                  <p className="text-[11px] text-zinc-400 font-sans mt-1 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Global Sensitivity Tuning Sliders */}
        <div className="pt-3 border-t border-zinc-800 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <div className="flex justify-between text-zinc-300 font-medium mb-1">
              <span>Detection Confidence Threshold</span>
              <span className="font-mono text-white">{Math.round(globalSettings.min_detection_confidence * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.90"
              step="0.05"
              value={globalSettings.min_detection_confidence}
              onChange={(e) => setGlobalSettings({ ...globalSettings, min_detection_confidence: parseFloat(e.target.value) })}
              className="w-full accent-white"
            />
            <span className="text-[10px] text-zinc-500">Minimum threshold to register object detection</span>
          </div>

          <div>
            <div className="flex justify-between text-zinc-300 font-medium mb-1">
              <span>Face Watchlist Match Threshold</span>
              <span className="font-mono text-white">{Math.round(globalSettings.face_match_threshold * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.40"
              max="0.95"
              step="0.05"
              value={globalSettings.face_match_threshold}
              onChange={(e) => setGlobalSettings({ ...globalSettings, face_match_threshold: parseFloat(e.target.value) })}
              className="w-full accent-white"
            />
            <span className="text-[10px] text-zinc-500">Cosine similarity for wanted suspect triggers</span>
          </div>

          <div>
            <div className="flex justify-between text-zinc-300 font-medium mb-1">
              <span>SkyShield UAV Radar Range</span>
              <span className="font-mono text-white">{globalSettings.drone_radar_range_meters}m</span>
            </div>
            <input
              type="range"
              min="50"
              max="500"
              step="25"
              value={globalSettings.drone_radar_range_meters}
              onChange={(e) => setGlobalSettings({ ...globalSettings, drone_radar_range_meters: parseInt(e.target.value) })}
              className="w-full accent-white"
            />
            <span className="text-[10px] text-zinc-500">Aerial threat radar sphere boundary</span>
          </div>

          <div>
            <div className="flex justify-between text-zinc-300 font-medium mb-1">
              <span>Loitering / Unattended Dwell</span>
              <span className="font-mono text-white">{globalSettings.loitering_alert_sec}s</span>
            </div>
            <input
              type="range"
              min="5"
              max="60"
              step="5"
              value={globalSettings.loitering_alert_sec}
              onChange={(e) => setGlobalSettings({ ...globalSettings, loitering_alert_sec: parseInt(e.target.value) })}
              className="w-full accent-white"
            />
            <span className="text-[10px] text-zinc-500">Dwell duration before alert dispatch</span>
          </div>
        </div>
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
