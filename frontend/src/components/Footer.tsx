import Link from 'next/link';
import Logo from '@/components/Logo';

const REPO = 'https://github.com/h55n/slopesense';
const COLUMNS = [
  {
    title: 'Platform',
    links: [
      { href: '/', label: 'Dashboard' },
      { href: '/districts', label: 'Districts' },
      { href: '/status', label: 'System status' },
      { href: '/register', label: 'Register for alerts' },
    ],
  },
  {
    title: 'Developers',
    links: [
      { href: '/api-docs', label: 'API reference' },
      { href: '/developers', label: 'Developer guide' },
      { href: REPO, label: 'GitHub', external: true },
      { href: `${REPO}/blob/master/ARCHITECTURE.md`, label: 'Architecture', external: true },
    ],
  },
  {
    title: 'Project',
    links: [
      { href: `${REPO}/blob/master/docs/DATA_SOURCES.md`, label: 'Data sources', external: true },
      { href: `${REPO}/blob/master/CHANGELOG.md`, label: 'Changelog', external: true },
      { href: `${REPO}/blob/master/CONTRIBUTING.md`, label: 'Contributing', external: true },
      { href: `${REPO}/blob/master/LICENSE`, label: 'Apache 2.0 license', external: true },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="relative mt-24 overflow-hidden">
      <p className="mx-auto max-w-3xl px-5 text-center text-sm text-ink/70">Research prototype. FPI is a model-generated index, not a calibrated landslide probability or an official government warning. Follow local authorities for safety decisions.</p>
      <div className="relative z-10 mx-auto max-w-[1280px] px-5 pt-4 sm:px-8 sm:pt-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="display text-[38px] sm:text-[52px]">
            A day&apos;s notice for <em>every slope.</em>
          </h2>
          <p className="mx-auto mt-4 max-w-md text-[16px] text-ink/60">
            Research prototype exploring free satellite and weather data for block-level landslide risk. No validated risk scores or warnings are issued.
          </p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Link href="/register" className="btn btn-primary">Register for alerts</Link>
            <Link href="/api-docs" className="btn btn-ghost">Read the API docs</Link>
          </div>
        </div>
      </div>

      {/* painted valley */}
      <div
        className="pointer-events-none relative -mt-6 h-[240px] w-full bg-cover bg-[position:60%_bottom] sm:h-[420px] lg:h-[480px]"
        aria-hidden="true"
        style={{
          backgroundImage: "url('/art2/footer.webp')",
          WebkitMaskImage: 'linear-gradient(180deg, transparent 0%, #000 30%)',
          maskImage: 'linear-gradient(180deg, transparent 0%, #000 30%)',
        }}
      />

      <div className="relative z-10 bg-forest-deep text-paper">
        <div className="mx-auto grid max-w-[1280px] gap-12 px-5 pb-12 pt-14 sm:px-8 lg:grid-cols-[1.2fr_2fr]">
          <div className="max-w-sm">
            <div className="flex items-center gap-2.5">
              <Logo size={30} />
              <span className="font-serif text-[24px] leading-none">SlopeSense</span>
            </div>
            <p className="mt-4 text-[14px] leading-relaxed text-paper/60">
              Landslide risk intelligence for India. Open source under Apache 2.0.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
            {COLUMNS.map((col) => (
              <div key={col.title}>
                <h3 className="font-sans text-[11px] font-semibold uppercase tracking-[0.16em] text-paper/45">{col.title}</h3>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((l) => (
                    <li key={l.label}>
                      {'external' in l && l.external ? (
                        <a href={l.href} target="_blank" rel="noopener noreferrer" className="text-[14px] text-paper/75 transition-colors hover:text-paper">
                          {l.label}
                        </a>
                      ) : (
                        <Link href={l.href} className="text-[14px] text-paper/75 transition-colors hover:text-paper">
                          {l.label}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <div className="border-t border-paper/10">
          <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-3 px-5 py-5 text-[13px] text-paper/50 sm:px-8">
            <span>&copy; 2026 SlopeSense. Built to give districts a day&apos;s notice.</span>
            <span className="flex gap-5">
              <a href={REPO} target="_blank" rel="noopener noreferrer" className="hover:text-paper">Source</a>
              <Link href="/api-docs" className="hover:text-paper">API</Link>
              <Link href="/status" className="hover:text-paper">Status</Link>
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
