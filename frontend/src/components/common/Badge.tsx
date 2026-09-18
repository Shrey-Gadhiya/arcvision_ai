import React from 'react';

export interface BadgeProps {
  variant?: 'critical' | 'warning' | 'success' | 'info' | 'neutral';
  size?: 'sm' | 'md';
  children: React.ReactNode;
  dot?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  size = 'sm',
  children,
  dot = false,
  className = ''
}) => {
  const variantStyles = {
    critical: 'bg-zinc-900 text-white border-zinc-600 font-semibold',
    warning: 'bg-zinc-900 text-zinc-200 border-zinc-700',
    success: 'bg-zinc-900 text-zinc-100 border-zinc-600',
    info: 'bg-zinc-900 text-zinc-300 border-zinc-700',
    neutral: 'bg-zinc-900/60 text-zinc-400 border-zinc-800'
  };

  const dotColors = {
    critical: 'bg-white',
    warning: 'bg-zinc-300',
    success: 'bg-zinc-100',
    info: 'bg-zinc-400',
    neutral: 'bg-zinc-500'
  };

  const sizeStyles = {
    sm: 'text-[11px] px-1.5 py-0.5',
    md: 'text-xs px-2 py-0.5'
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium border rounded ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  );
};
