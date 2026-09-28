import React, { useState, useEffect } from 'react';
import { Eye, EyeOff, AlertCircle, Loader2, Lock, User, KeyRound, Clock, ShieldCheck } from 'lucide-react';
import { apiClient } from '../api/client';

interface LoginProps {
  onLogin: (token: string, username: string, role: string) => void;
}

const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 30;

export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [failedAttempts, setFailedAttempts] = useState<number>(0);
  const [lockoutRemaining, setLockoutRemaining] = useState<number>(0);

  // Check backend API connectivity
  useEffect(() => {
    let isMounted = true;
    apiClient
      .get('/health')
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

  // Lockout countdown timer
  useEffect(() => {
    if (lockoutRemaining <= 0) return;
    const timer = setInterval(() => {
      setLockoutRemaining((prev) => {
        if (prev <= 1) {
          setFailedAttempts(0);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [lockoutRemaining]);

  const performLogin = async (userToSubmit: string, passToSubmit: string) => {
    if (lockoutRemaining > 0) {
      setError(`Security lockout active. Please wait ${lockoutRemaining}s.`);
      return;
    }

    const cleanUser = userToSubmit.trim();
    const cleanPass = passToSubmit;

    if (!cleanUser || !cleanPass) {
      setError('Please enter your username and password.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const res = await apiClient.post('/auth/login', {
        username: cleanUser,
        password: cleanPass
      });

      const { access_token, role, username: authUser } = res.data;

      localStorage.setItem('arc_token', access_token);
      localStorage.setItem('arc_user', authUser || cleanUser);
      localStorage.setItem('arc_role', role);

      setFailedAttempts(0);
      setLockoutRemaining(0);

      onLogin(access_token, authUser || cleanUser, role);
    } catch (err: any) {
      const newAttempts = failedAttempts + 1;
      setFailedAttempts(newAttempts);

      if (newAttempts >= MAX_FAILED_ATTEMPTS) {
        setLockoutRemaining(LOCKOUT_SECONDS);
        setError(`Security Lockout Triggered: Too many failed attempts. Terminal locked for ${LOCKOUT_SECONDS}s.`);
      } else {
        const detail = err?.response?.data?.detail;
        const attemptsLeft = MAX_FAILED_ATTEMPTS - newAttempts;
        const msg = detail || 'Invalid credentials. Please verify your username and password.';
        setError(`${msg} (${attemptsLeft} attempt${attemptsLeft === 1 ? '' : 's'} remaining)`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await performLogin(username, password);
  };

  const isLockedOut = lockoutRemaining > 0;

  return (
    <div className="min-h-screen bg-[#050507] text-white flex items-center justify-center p-4 relative overflow-hidden font-sans">
      {/* Background Grid Pattern */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px)`,
          backgroundSize: '32px 32px',
        }}
      />

      {/* Subtle Ambient Radial Lighting */}
      <div className="absolute w-[500px] h-[500px] bg-zinc-800/10 blur-[140px] rounded-full pointer-events-none -top-40 -left-40" />
      <div className="absolute w-[450px] h-[450px] bg-zinc-900/15 blur-[120px] rounded-full pointer-events-none -bottom-40 -right-40" />

      <div className="relative w-full max-w-sm z-10 space-y-6">
        {/* Title without any logo */}
        <div className="text-center space-y-1">
          <h1 className="text-xl font-bold tracking-tight text-white">
            ARC VISION
          </h1>
          <p className="text-xs text-zinc-400 font-mono tracking-wider uppercase">
            Tactical Surveillance System
          </p>
        </div>

        {/* Security Login Card */}
        <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-6 shadow-2xl space-y-5 backdrop-blur-md">
          {/* Header Status */}
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Sign In
            </span>
            <div className="flex items-center gap-1.5 text-[11px] font-mono">
              <span
                className={`w-2 h-2 rounded-full ${
                  backendOnline === true
                    ? 'bg-emerald-400 animate-pulse'
                    : backendOnline === false
                    ? 'bg-red-400'
                    : 'bg-zinc-500'
                }`}
              />
              <span
                className={
                  backendOnline === true
                    ? 'text-emerald-400'
                    : backendOnline === false
                    ? 'text-red-400'
                    : 'text-zinc-400'
                }
              >
                {backendOnline === true ? 'System Online' : backendOnline === false ? 'Offline' : 'Connecting'}
              </span>
            </div>
          </div>

          {/* Lockout Warning */}
          {isLockedOut && (
            <div className="p-3 rounded-lg bg-red-950/60 border border-red-700 text-red-200 flex items-center gap-2.5 text-xs animate-pulse">
              <Clock className="w-4 h-4 text-red-400 shrink-0" />
              <div>
                <span className="font-bold">Security Lockout:</span> Too many failed attempts. Try again in{' '}
                <span className="font-mono font-bold text-white">{lockoutRemaining}s</span>.
              </div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} autoComplete="off" className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-[11px] font-medium text-zinc-400 mb-1.5 uppercase tracking-wider">
                Username
              </label>
              <div className="relative">
                <input
                  type="text"
                  name="arc_username_field"
                  autoComplete="off"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading || isLockedOut}
                  className="w-full bg-black/70 border border-zinc-700/80 rounded-lg pl-9 pr-3.5 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-400 transition-colors font-mono"
                  placeholder="Enter username"
                  required
                />
                <User className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
              </div>
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider">
                  Password
                </label>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="arc_password_field"
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading || isLockedOut}
                  className="w-full bg-black/70 border border-zinc-700/80 rounded-lg pl-9 pr-10 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-400 transition-colors font-mono"
                  placeholder="Enter password"
                  required
                />
                <KeyRound className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error Banner */}
            {error && !isLockedOut && (
              <div className="flex items-start gap-2 bg-red-950/40 border border-red-800/80 rounded-lg p-2.5 text-red-300">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div className="text-xs">
                  <p className="font-medium">{error}</p>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !username || !password || isLockedOut}
              className="w-full bg-white hover:bg-zinc-200 active:bg-zinc-300 disabled:bg-zinc-800 disabled:text-zinc-600 disabled:cursor-not-allowed text-black text-xs font-semibold py-2.5 rounded-lg transition-all flex items-center justify-center gap-2 shadow-md cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-black" />
                  Verifying Credentials…
                </>
              ) : isLockedOut ? (
                <>
                  <Clock className="w-3.5 h-3.5 text-zinc-500" />
                  Locked ({lockoutRemaining}s)
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5 text-black" />
                  Sign In
                </>
              )}
            </button>
          </form>
        </div>

        {/* Security Warning Notice */}
        <div className="text-center space-y-1 text-zinc-500">
          <p className="text-[11px] leading-relaxed">
            Authorized personnel only. All access attempts are recorded.
          </p>
        </div>
      </div>
    </div>
  );
};
