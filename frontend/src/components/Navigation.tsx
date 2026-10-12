'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import { useState } from 'react';
import { useAlerts } from '@/lib/hooks';
import Wordmark from '@/components/Wordmark';

const NAV_LINKS = [
  { href: '/',          label: 'Dashboard' },
  { href: '/districts', label: 'Districts' },
  { href: '/status',    label: 'Status'    },
  { href: '/api-docs',  label: 'API'       },
  { href: '/developers', label: 'Developers' },
];

export default function Navigation() {
  const pathname = usePathname();
  const { stats, isSample } = useAlerts();
  const [menuOpen, setMenuOpen] = useState(false);
  const emergencyCount = isSample ? 0 : stats?.emergency ?? 0;

  const isActive = (href: string) => pathname === href || (href !== '/' && pathname?.startsWith(href));

  return (
    <nav
      className="sticky top-0 z-50 border-b border-ink/10 bg-paper/85 backdrop-blur-xl"
      aria-label="Global navigation"
    >
      <div className="mx-auto grid h-16 max-w-[1280px] grid-cols-[auto_1fr_auto] items-center gap-6 px-5 sm:px-8">
        <Link href="/" className="focus-ring flex min-h-[44px] items-center rounded-lg" aria-label="SlopeSense home">
          <Wordmark size={26} />
        </Link>

        <ul className="hidden items-center justify-center gap-1 md:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                aria-current={isActive(link.href) ? 'page' : undefined}
                className={`focus-ring block rounded-full px-3.5 py-2 text-[14px] transition-colors ${
                  isActive(link.href) ? 'bg-forest/10 font-medium text-forest' : 'text-ink/60 hover:text-ink'
                }`}
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="flex items-center justify-end gap-3">
          {emergencyCount > 0 && (
            <span className="hidden items-center gap-2 rounded-full border border-red-400/30 bg-red-400/10 px-3 py-1.5 text-[12px] font-medium text-red-400 lg:flex">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" />
              {emergencyCount} emergency
            </span>
          )}
          <Link href="/register" className="btn btn-primary hidden h-10 px-5 text-[13px] sm:inline-flex">
            Get alerts
          </Link>
          <button
            className="focus-ring flex h-10 w-10 items-center justify-center rounded-full border border-ink/15 text-ink md:hidden"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden border-t border-ink/10 bg-paper md:hidden"
          >
            <div className="flex flex-col gap-1 px-5 py-4">
              {[...NAV_LINKS, { href: '/register', label: 'Get alerts' }].map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className={`rounded-xl px-4 py-3 text-[15px] ${
                    isActive(link.href) ? 'bg-forest/10 font-medium text-forest' : 'text-ink/70'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
