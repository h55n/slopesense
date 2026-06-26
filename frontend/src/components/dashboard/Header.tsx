'use client';

import { useLiveWebSocket } from '@/lib/hooks';
import { formatDistanceToNow } from 'date-fns';

interface HeaderProps {
  lastRun: string | null;
  stats: { total: number; emergency: number; warning: number; watch: number };
}

export function Header({ lastRun, stats }: HeaderProps) {
  const { isConnected } = useLiveWebSocket();

  return (
    <header className="flex items-center justify-between px-4 h-14 border-b border-slope-border bg-slope-surface flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span className="text-xl">🏔</span>
          <span className="font-semibold text-white tracking-tight">SlopeSense</span>
          <span className="text-xs font-mono text-slate-500 bg-slope-card px-1.5 py-0.5 rounded ml-1">v0.1</span>
        </div>
        <div className="h-4 w-px bg-slope-border" />
        <span className="text-xs text-slate-400">Landslide Risk Intelligence · India</span>
      </div>

      {/* Centre stats */}
      <div className="flex items-center gap-4 text-xs">
        {stats.emergency > 0 && (
          <div className="flex items-center gap-1.5 text-purple-400">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            <span className="font-medium">{stats.emergency} Emergency</span>
          </div>
        )}
        {stats.warning > 0 && (
          <div className="flex items-center gap-1.5 text-red-400">
            <span className="w-2 h-2 rounded-full bg-red-400" />
            <span className="font-medium">{stats.warning} Warning</span>
          </div>
        )}
        {stats.watch > 0 && (
          <div className="flex items-center gap-1.5 text-amber-400">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="font-medium">{stats.watch} Watch</span>
          </div>
        )}
        {stats.total === 0 && (
          <span className="text-emerald-400 font-medium">No active alerts</span>
        )}
      </div>

      {/* Right: status */}
      <div className="flex items-center gap-4 text-xs text-slate-400">
        {lastRun && (
          <span>
            Last run{' '}
            <span className="text-slate-300">
              {formatDistanceToNow(new Date(lastRun), { addSuffix: true })}
            </span>
          </span>
        )}
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-slate-600'}`}
          />
          <span className={isConnected ? 'text-emerald-400' : 'text-slate-500'}>
            {isConnected ? 'Live' : 'Polling'}
          </span>
        </div>
        <a
          href="/docs"
          target="_blank"
          className="text-slate-500 hover:text-slate-300 transition-colors"
        >
          API Docs →
        </a>
      </div>
    </header>
  );
}
