import React, { useState, useEffect } from 'react';
import { Shield, Eye, EyeOff, AlertCircle, Loader2, CheckCircle2, UserCheck, KeyRound, Radio } from 'lucide-react';
import { apiClient, API_BASE_URL } from '../api/client';

interface LoginProps {
  onLogin: (token: string, username: string, role: string) => void;
}

interface DemoAccount {
  label: string;
  role: string;
  username: string;
  password: string;
  badgeColor: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  { label: 'Administrator', role: 'ADMIN', username: 'admin', password: 'admin123', badgeColor: 'bg-red-950/60 text-red-400 border-red-800/60' },
  { label: 'Sector Commander', role: 'COMMANDER', username: 'commander', password: 'command123', badgeColor: 'bg-amber-950/60 text-amber-400 border-amber-800/60' },
  { label: 'Surveillance Operator', role: 'OPERATOR', username: 'operator', password: 'operator123', badgeColor: 'bg-blue-950/60 text-blue-400 border-blue-800/60' },
  { label: 'Forensic Investigator', role: 'INVESTIGATOR', username: 'investigator', password: 'investigate123', badgeColor: 'bg-purple-950/60 text-purple-400 border-purple-800/60' },
];

export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    // Check backend API connectivity
    let isMounted = true;
    apiClient.get('/health')
      .then(() => {
        if (isMounted) setBackendOnline(true);
      })
      .catch(() => {
        if (isMounted) setBackendOnline(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const performLogin = async (userToSubmit: string, passToSubmit: string) => {
    setError('');
    setLoading(true);
    try {
      const res = await apiClient.post('/auth/login', {
        username: userToSubmit.trim(),
        password: passToSubmit.trim()
      });
      const { access_token, role, username: authUser } = res.data;
      localStorage.setItem('arc_token', access_token);
      localStorage.setItem('arc_user', authUser || userToSubmit);
      localStorage.setItem('arc_role', role);
      onLogin(access_token, authUser || userToSubmit, role);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = detail || (err.code === 'ECONNABORTED' ? 'Connection timed out. Checking backend...' : 'Authentication failed. Please check username & password.');
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await performLogin(username, password);
  };

  const handleQuickLogin = async (acc: DemoAccount) => {
    setUsername(acc.username);
    setPassword(acc.password);
    await performLogin(acc.username, acc.password);
  };

  return (
    <div className="min-h-screen bg-[#050507] text-white flex items-center justify-center p-4 relative overflow-hidden font-sans">
      {/* Background grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px)`,
          backgroundSize: '32px 32px',
        }}
      />
      
      {/* Subtle glowing radial gradient */}
      <div className="absolute w-[600px] h-[600px] bg-blue-600/10 blur-[140px] rounded-full pointer-events-none -top-40 -left-40" />
      <div className="absolute w-[500px] h-[500px] bg-emerald-600/5 blur-[120px] rounded-full pointer-events-none -bottom-40 -right-40" />

      <div className="relative w-full max-w-md z-10">
        {/* Logo / Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-zinc-900/90 border border-zinc-700/80 mb-3.5 shadow-xl backdrop-blur-md">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center justify-center gap-2">
            ARC VISION
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-700/80 text-emerald-400">
              v2.1 LIVE
            </span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1 uppercase tracking-widest font-mono">
            Tactical Border Surveillance AI
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-zinc-900/80 border border-zinc-800/90 backdrop-blur-xl rounded-2xl p-6 shadow-2xl space-y-5">
          <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Operator Authentication
            </span>
            <div className="flex items-center gap-1.5 text-[11px] font-mono">
              <span className={`w-2 h-2 rounded-full ${backendOnline === true ? 'bg-emerald-400 animate-pulse' : backendOnline === false ? 'bg-amber-400' : 'bg-zinc-500'}`} />
              <span className={backendOnline === true ? 'text-emerald-400' : backendOnline === false ? 'text-amber-400' : 'text-zinc-400'}>
                {backendOnline === true ? 'API Connected' : backendOnline === false ? 'Connecting...' : 'Checking'}
              </span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-[11px] font-medium text-zinc-400 mb-1.5 uppercase tracking-wider">
                Tactical Call-sign / Username
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-black/60 border border-zinc-700/80 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-white focus:ring-1 focus:ring-white/30 transition-all font-mono"
                  placeholder="e.g. admin"
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-[11px] font-medium text-zinc-400 mb-1.5 uppercase tracking-wider">
                Security Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-black/60 border border-zinc-700/80 rounded-xl px-3.5 py-2.5 pr-10 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-white focus:ring-1 focus:ring-white/30 transition-all font-mono"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error Banner */}
            {error && (
              <div className="flex items-start gap-2.5 bg-red-950/40 border border-red-800/80 rounded-xl p-3 text-red-300">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <p className="font-semibold">{error}</p>
                  <p className="text-[11px] text-red-400/80">Click any role below to auto-fill verified credentials.</p>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full bg-white hover:bg-zinc-200 active:bg-zinc-300 disabled:bg-zinc-800 disabled:text-zinc-600 disabled:cursor-not-allowed text-black text-sm font-semibold py-2.5 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-black" />
                  Authenticating Call-sign…
                </>
              ) : (
                <>
                  <KeyRound className="w-4 h-4 text-black" />
                  Authorize & Access Console
                </>
              )}
            </button>
          </form>

          {/* Quick 1-Click Role Login Selector */}
          <div className="pt-4 border-t border-zinc-800/80 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-zinc-400">
                ⚡ 1-Click Role Access
              </span>
              <span className="text-[10px] text-zinc-500 font-mono">Pre-Configured RBAC</span>
            </div>
            
            <div className="grid grid-cols-2 gap-2">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.username}
                  type="button"
                  onClick={() => handleQuickLogin(acc)}
                  disabled={loading}
                  className="flex flex-col items-start p-2.5 rounded-xl bg-black/40 hover:bg-zinc-800/70 border border-zinc-800 hover:border-zinc-600 transition-all text-left group"
                >
                  <div className="flex items-center justify-between w-full mb-1">
                    <span className="text-xs font-semibold text-zinc-200 group-hover:text-white">
                      {acc.label}
                    </span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${acc.badgeColor}`}>
                      {acc.role}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500 group-hover:text-zinc-400">
                    {acc.username} / {acc.password}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-6 space-y-1">
          <p className="text-[11px] font-mono text-zinc-500">
            SIH26187 · AI-Based Video Analytics Platform for Border Surveillance
          </p>
          <p className="text-[10px] text-zinc-600">
            Ministry of Home Affairs · Sashastra Seema Bal (SSB)
          </p>
        </div>
      </div>
    </div>
  );
};

