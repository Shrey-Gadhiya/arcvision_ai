import React, { useState, useEffect } from 'react';
import { Navbar } from './components/layout/Navbar';
import { Sidebar, PageId } from './components/layout/Sidebar';
import { Login } from './pages/Login';
import { CommandCenter } from './pages/CommandCenter';
import { LiveGrid } from './pages/LiveGrid';
import { Cameras } from './pages/Cameras';
import { CameraDetail } from './pages/CameraDetail';
import { Incidents } from './pages/Incidents';
import { IncidentDetail } from './pages/IncidentDetail';
import { Investigation } from './pages/Investigation';
import { Timeline } from './pages/Timeline';
import { PlaybackTimeline } from './pages/PlaybackTimeline';
import { ReviewStream } from './pages/ReviewStream';
import { StorageTelemetryPage } from './pages/StorageTelemetryPage';
import { ANPRIntelligence } from './pages/ANPRIntelligence';
import { FaceIntelligence } from './pages/FaceIntelligence';
import { CrossCameraIntelligence } from './pages/CrossCameraIntelligence';
import { ZonesFences } from './pages/ZonesFences';
import { EvidenceLocker } from './pages/EvidenceLocker';
import { RuleEngine } from './pages/RuleEngine';
import { AIModelCenter } from './pages/AIModelCenter';
import { SystemHealth } from './pages/SystemHealth';
import { AuditLogs } from './pages/AuditLogs';
import { Settings } from './pages/Settings';
import { TacticalMap } from './pages/TacticalMap';
import { PurgeTrackedModal } from './components/common/PurgeTrackedModal';

import { Camera, Incident } from './types';
import { apiClient, wsManager } from './api/client';

export const App: React.FC = () => {
  const [isVerifyingAuth, setIsVerifyingAuth] = useState<boolean>(true);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<string>('');
  const [currentRole, setCurrentRole] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<PageId>('command');
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<number>(1);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [audioEnabled, setAudioEnabled] = useState<boolean>(true);
  const [isPurgeModalOpen, setIsPurgeModalOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Authenticate & verify token integrity with backend on startup
  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('arc_token');
      if (!token) {
        setIsAuthenticated(false);
        setIsVerifyingAuth(false);
        return;
      }

      try {
        const res = await apiClient.get('/auth/me');
        setIsAuthenticated(true);
        setCurrentUser(res.data.username);
        setCurrentRole(res.data.role);
        localStorage.setItem('arc_user', res.data.username);
        localStorage.setItem('arc_role', res.data.role);
      } catch (err) {
        // Token invalid, expired, or tampered
        localStorage.removeItem('arc_token');
        localStorage.removeItem('arc_user');
        localStorage.removeItem('arc_role');
        setIsAuthenticated(false);
        setCurrentUser('');
        setCurrentRole('');
      } finally {
        setIsVerifyingAuth(false);
      }
    };

    verifyToken();
  }, []);

  const handleLogin = (token: string, username: string, role: string) => {
    setIsAuthenticated(true);
    setCurrentUser(username);
    setCurrentRole(role);
  };

  const handleLogout = async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      // Ignore network errors on session teardown
    }
    localStorage.removeItem('arc_token');
    localStorage.removeItem('arc_user');
    localStorage.removeItem('arc_role');
    setIsAuthenticated(false);
    setCurrentUser('');
    setCurrentRole('');
    setCameras([]);
    setIncidents([]);
  };

  // Play audio chime using Web Audio API (zero external asset dependency)
  const playTacticalAlertChime = (isCritical: boolean) => {
    if (!audioEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      osc.type = isCritical ? 'sawtooth' : 'sine';
      osc.frequency.setValueAtTime(isCritical ? 880 : 440, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(isCritical ? 1760 : 880, audioCtx.currentTime + 0.2);

      gain.gain.setValueAtTime(0.25, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);

      osc.connect(gain);
      gain.connect(audioCtx.destination);

      osc.start();
      osc.stop(audioCtx.currentTime + 0.35);
    } catch (e) {
      // Audio context may be blocked by browser until user gesture
    }
  };

  const fetchInitialData = async () => {
    if (!isAuthenticated) return;
    try {
      const camRes = await apiClient.get('/cameras/');
      setCameras(camRes.data);
      if (camRes.data.length > 0 && !selectedCameraId) {
        setSelectedCameraId(camRes.data[0].id);
      }

      const incRes = await apiClient.get('/incidents/');
      setIncidents(incRes.data);
    } catch (e: any) {
      if (e?.response?.status === 401) {
        handleLogout();
      }
    }
  };

  useEffect(() => {
    const handleAuthExpired = () => {
      handleLogout();
    };
    window.addEventListener('arc_auth_expired', handleAuthExpired);

    if (isAuthenticated) {
      fetchInitialData();
      wsManager.connect();
    }

    // Subscribe to real-time incident event
    const unsubIncident = wsManager.on('incident:new', (newInc: Incident) => {
      setIncidents((prev) => [newInc, ...prev]);
      const isCrit = newInc.severity === 'CRITICAL';
      playTacticalAlertChime(isCrit);
    });

    const unsubStatus = wsManager.on('incident:status_changed', (payload) => {
      setIncidents((prev) =>
        prev.map((i) =>
          i.id === payload.incident_id ? { ...i, status: payload.status } : i
        )
      );
    });

    // Subscribe to purge event from any console
    const unsubPurge = wsManager.on('tracked_objects:cleared', (payload: any) => {
      setToastMessage(`Tracked objects purged by ${payload?.purged_by || 'operator'}.`);
      fetchInitialData();
      setTimeout(() => setToastMessage(null), 4000);
    });

    return () => {
      window.removeEventListener('arc_auth_expired', handleAuthExpired);
      unsubIncident();
      unsubStatus();
      unsubPurge();
    };
  }, [isAuthenticated, audioEnabled]);

  const handleResetDemo = async () => {
    try {
      await apiClient.post('/demo/init-sih26187');
      await fetchInitialData();
      alert('Border surveillance environment reset successfully.');
    } catch (e) {
      alert('Failed to reset demo environment.');
    }
  };

  const handleTriageIncident = async (incId: number, newStatus: string) => {
    try {
      const res = await apiClient.post(`/incidents/${incId}/status`, {
        status: newStatus,
        note: `Status triage changed to ${newStatus}`
      });
      setIncidents((prev) => prev.map((i) => (i.id === incId ? res.data : i)));
      if (selectedIncident && selectedIncident.id === incId) {
        setSelectedIncident(res.data);
      }
    } catch (e) {
      alert('Triage update failed');
    }
  };

  const activeThreats = incidents.filter(
    (i) => i.severity === 'CRITICAL' && i.status !== 'RESOLVED'
  ).length;

  // Show security verification loader while validating token
  if (isVerifyingAuth) {
    return (
      <div className="min-h-screen bg-[#050507] text-white flex flex-col items-center justify-center p-4">
        <div className="w-9 h-9 border-2 border-white/20 border-t-white rounded-full animate-spin mb-4" />
        <p className="text-xs font-mono tracking-widest uppercase text-zinc-400">
          Verifying Tactical Clearance &amp; Token Validity…
        </p>
      </div>
    );
  }

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-[#000000] text-zinc-100 flex flex-col selection:bg-white selection:text-black font-sans relative">
      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="absolute top-14 right-4 z-50 bg-zinc-900 border border-emerald-500/80 text-emerald-300 px-4 py-2 rounded-xl text-xs shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-200">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Header */}
      <Navbar
        activeThreatCount={activeThreats}
        onResetDemo={handleResetDemo}
        audioEnabled={audioEnabled}
        onToggleAudio={() => setAudioEnabled(!audioEnabled)}
        currentUser={currentUser}
        currentRole={currentRole}
        onLogout={handleLogout}
        onOpenPurgeModal={() => setIsPurgeModalOpen(true)}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          currentPage={currentPage}
          onSelectPage={(p) => {
            setCurrentPage(p);
            if (p !== 'camera_detail' && p !== 'incidents') {
              // keep state
            }
          }}
          incidentCount={incidents.filter((i) => i.status === 'NEW').length}
        />

        {/* Main Operational View */}
        <main className="flex-1 overflow-y-auto bg-[#000000]">
          {currentPage === 'command' && (
            <CommandCenter
              cameras={cameras}
              incidents={incidents}
              onSelectCamera={(id) => {
                setSelectedCameraId(id);
                setCurrentPage('camera_detail');
              }}
              onSelectIncident={(inc) => {
                setSelectedIncident(inc);
                setCurrentPage('incidents');
              }}
              onTriageIncident={handleTriageIncident}
            />
          )}

          {currentPage === 'live' && (
            <LiveGrid
              cameras={cameras}
              onSelectCamera={(id) => {
                setSelectedCameraId(id);
                setCurrentPage('camera_detail');
              }}
              onOpenPurgeModal={() => setIsPurgeModalOpen(true)}
            />
          )}

          {currentPage === 'review' && (
            <ReviewStream
              cameras={cameras}
              onOpenTimelineAt={(camId, ts) => {
                setSelectedCameraId(camId);
                setCurrentPage('timeline');
              }}
            />
          )}

          {currentPage === 'cameras' && (
            <Cameras
              cameras={cameras}
              onRefresh={fetchInitialData}
              onSelectCamera={(id) => {
                setSelectedCameraId(id);
                setCurrentPage('camera_detail');
              }}
            />
          )}

          {currentPage === 'camera_detail' && (
            <CameraDetail
              cameraId={selectedCameraId}
              cameras={cameras}
              onBack={() => setCurrentPage('cameras')}
            />
          )}

          {currentPage === 'incidents' && (
            selectedIncident ? (
              <IncidentDetail
                incident={selectedIncident}
                onBack={() => setSelectedIncident(null)}
                onRefresh={fetchInitialData}
              />
            ) : (
              <Incidents
                incidents={incidents}
                onSelectIncident={(inc) => setSelectedIncident(inc)}
                onTriageIncident={handleTriageIncident}
              />
            )
          )}

          {currentPage === 'investigation' && (
            <Investigation
              cameras={cameras}
              onSelectIncident={(inc) => {
                setSelectedIncident(inc);
                setCurrentPage('incidents');
              }}
              onNavigateToMap={(camId) => {
                setSelectedCameraId(camId);
                setCurrentPage('tactical_map');
              }}
            />
          )}

          {currentPage === 'timeline' && (
            <PlaybackTimeline
              cameras={cameras}
              incidents={incidents}
              onSelectIncident={(inc) => {
                setSelectedIncident(inc);
                setCurrentPage('incidents');
              }}
            />
          )}

          {currentPage === 'storage' && <StorageTelemetryPage />}

          {currentPage === 'anpr' && <ANPRIntelligence />}

          {currentPage === 'face' && <FaceIntelligence />}

          {currentPage === 'cross_camera' && <CrossCameraIntelligence />}

          {currentPage === 'tactical_map' && (
            <TacticalMap
              cameras={cameras}
              incidents={incidents}
              onSelectCamera={(id) => {
                setSelectedCameraId(id);
                setCurrentPage('camera_detail');
              }}
              onSelectIncident={(inc) => {
                setSelectedIncident(inc);
                setCurrentPage('incidents');
              }}
            />
          )}

          {currentPage === 'zones' && (
            <ZonesFences
              cameras={cameras}
              onSelectCamera={(id) => {
                setSelectedCameraId(id);
                setCurrentPage('camera_detail');
              }}
            />
          )}

          {currentPage === 'rules' && <RuleEngine />}
          {currentPage === 'models' && <AIModelCenter />}

          {currentPage === 'evidence' && <EvidenceLocker />}

          {currentPage === 'health' && <SystemHealth />}

          {currentPage === 'audit' && <AuditLogs />}

          {currentPage === 'settings' && <Settings />}
        </main>
      </div>

      {/* Global Purge Tracked Objects Modal */}
      <PurgeTrackedModal
        isOpen={isPurgeModalOpen}
        onClose={() => setIsPurgeModalOpen(false)}
        cameras={cameras}
        onPurgeComplete={({ streamers_reset, deleted_snapshots }) => {
          fetchInitialData();
          setToastMessage(`Purge complete: ${streamers_reset} camera streamer(s) reset, ${deleted_snapshots} snapshot(s) deleted.`);
          setTimeout(() => setToastMessage(null), 5000);
        }}
      />
    </div>
  );
};

export default App;
