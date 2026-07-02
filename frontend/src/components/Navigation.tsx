'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAlerts } from '@/lib/hooks';
import { useState } from 'react';

const NAV_LINKS = [
  { href: '/',           label: 'Dashboard' },
  { href: '/districts',  label: 'Districts' },
  { href: '/status',     label: 'Status'    },
  { href: '/register',   label: 'Register'  },
  { href: '/api-docs',   label: 'API Docs'  },
];

export default function Navigation() {
  const pathname   = usePathname();
  const { stats }  = useAlerts();
  const [menuOpen, setMenuOpen] = useState(false);

  const emergencyCount = stats?.emergency ?? 0;
  const hasAlerts      = emergencyCount > 0;

  return (
    <nav
      className="sticky top-0 z-50 border-b border-white/5 backdrop-blur-2xl transition-colors duration-300"
      style={{ background: 'rgba(8,8,9,0.85)' }}
      aria-label="Global navigation"
    >
      <div className="mx-auto flex max-w-[1600px] items-center justify-between px-6 py-3.5 sm:px-8 lg:px-12">

        {/* ── Logo ── */}
        <Link
          href="/"
          className="group flex items-center gap-3 transition-opacity hover:opacity-90 focus-ring rounded-lg"
        >
          {/* Icon */}
          <div className="relative flex h-7 w-7 items-center justify-center rounded-[9px] border border-slope-accent/25 bg-slope-accent/8 shadow-glow-lime transition-colors duration-300 group-hover:border-slope-accent/40 group-hover:shadow-glow-lime-strong">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M7 1L13 12H1L7 1Z" stroke="#c5ff4a" strokeWidth="1.5" strokeLinejoin="round" fill="rgba(197,255,74,0.08)" />
              <path d="M7 5L9.5 10H4.5L7 5Z" fill="#c5ff4a" opacity="0.6" />
            </svg>
            {hasAlerts && (
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75 animate-ping" />
                <span className="relative inline-flex h-3 w-3 rounded-full bg-red-500" />
              </span>
            )}
          </div>

          {/* Name */}
          <span className="text-base-sm font-semibold tracking-tight text-white/90 transition-colors group-hover:text-white">
            SlopeSense
          </span>

          {/* Badge */}
          <span className="hidden rounded-md border border-white/8 bg-white/4 px-1.5 py-0.5 text-micro font-bold uppercase tracking-widest text-white/35 sm:block">
            v0.1
          </span>
        </Link>

        {/* ── Desktop links ── */}
        <ul className="hidden items-center gap-1 sm:flex">
          {NAV_LINKS.map(link => {
            const isActive =
              pathname === link.href ||
              (link.href !== '/' && pathname?.startsWith(link.href));
            return (
              <li key={link.href} className="relative">
                <Link
                  href={link.href}
                  className={`relative z-10 block rounded-lg px-4 py-2 text-small font-semibold tracking-wide transition-colors duration-200 focus-ring ${
                    isActive
                      ? 'text-slope-bg'
                      : 'text-white/50 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {link.label}
                </Link>
                {isActive && (
                  <motion.div
                    layoutId="nav-active"
                    className="absolute inset-0 z-0 rounded-lg bg-slope-accent shadow-glow-lime"
                    transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                  />
                )}
              </li>
            );
          })}
        </ul>

        {/* ── Right side: alert badge + mobile menu ── */}
        <div className="flex items-center gap-3">
          {/* Live alert count */}
          {hasAlerts && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="hidden items-center gap-2 rounded-full border border-red-500/25 bg-red-500/8 px-3 py-1.5 sm:flex"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-red-400 animate-pulse" />
              <span className="text-tiny font-bold uppercase tracking-widest text-red-400">
                {emergencyCount} Emergency
              </span>
            </motion.div>
          )}

          {/* Mobile hamburger */}
          <button
            className="flex items-center gap-1 rounded-lg border border-white/12 bg-white/4 hover:bg-white/8 hover:text-white hover:border-white/25 px-3 py-2 sm:hidden focus-ring transition-colors"
            onClick={() => setMenuOpen(v => !v)}
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
          >
            <span className="text-small font-semibold text-white/70">Menu</span>
          </button>
        </div>
      </div>

      {/* ── Mobile dropdown ── */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden border-t border-white/5 sm:hidden"
          >
            <div className="flex flex-col gap-1 px-6 py-4">
              {NAV_LINKS.map(link => {
                const isActive =
                  pathname === link.href ||
                  (link.href !== '/' && pathname?.startsWith(link.href));
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMenuOpen(false)}
                    className={`rounded-lg px-4 py-2.5 text-base-sm font-semibold tracking-wide transition-colors focus-ring ${
                      isActive
                        ? 'bg-slope-accent text-slope-bg shadow-glow-lime'
                        : 'text-white/50 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
