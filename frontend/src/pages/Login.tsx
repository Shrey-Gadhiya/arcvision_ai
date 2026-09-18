import React, { useState } from 'react';
import { Shield, Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-react';
import { apiClient } from '../api/client';

interface LoginProps {
  onLogin: (token: string, username: string, role: string) => void;
}

export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await apiClient.post('/auth/login', { username, password });
      const { access_token, role } = res.data;
      localStorage.setItem('arc_token', access_token);
      localStorage.setItem('arc_user', username);
      localStorage.setItem('arc_role', role);
      onLogin(access_token, username, role);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#000000] flex items-center justify-center p-4">
      {/* Background grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(#ffffff 1px, transparent 1px), linear-gradient(90deg, #ffffff 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative w-full max-w-sm">
        {/* Logo / Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-zinc-900 border border-zinc-700 mb-4 shadow-sm">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-xl font-semibold text-white tracking-wide">ARC VISION</h1>
          <p className="text-xs text-zinc-500 mt-1 uppercase tracking-widest">
            Tactical Surveillance Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-[#0c0c0e] border border-zinc-800 rounded-xl p-6 shadow-2xl">
          <p className="text-xs text-zinc-400 mb-5 text-center">
            Authenticate to access the operations console
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5 uppercase tracking-wide">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-[#18181b] border border-zinc-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-white focus:ring-1 focus:ring-white/30 transition-colors"
                placeholder="Enter username"
                autoComplete="username"
                autoFocus
                required
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5 uppercase tracking-wide">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#18181b] border border-zinc-700 rounded-lg px-3 py-2.5 pr-10 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-white focus:ring-1 focus:ring-white/30 transition-colors"
                  placeholder="Enter password"
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

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-600 rounded-lg px-3 py-2.5">
                <AlertCircle className="w-4 h-4 text-zinc-200 shrink-0" />
                <p className="text-xs text-zinc-200">{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full bg-white hover:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-600 disabled:cursor-not-allowed text-black text-sm font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 mt-2 shadow-sm"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-black" />
                  Authenticating…
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Hint */}
          <div className="mt-5 pt-4 border-t border-zinc-800">
            <p className="text-xs text-zinc-500 text-center">
              Default: <span className="text-zinc-300 font-mono">admin</span> /{' '}
              <span className="text-zinc-300 font-mono">admin123</span>
            </p>
          </div>
        </div>

        <p className="text-center text-xs text-zinc-600 mt-6">
          SIH26187 · Border Surveillance Intelligence System
        </p>
      </div>
    </div>
  );
};
