import Image from 'next/image';
import Link from 'next/link';

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
      { href: 'https://github.com/h55n/slopesense', label: 'GitHub', external: true },
      { href: 'https://github.com/h55n/slopesense/blob/main/ARCHITECTURE.md', label: 'Architecture', external: true },
    ],
  },
  {
    title: 'Project',
    links: [
      { href: 'https://github.com/h55n/slopesense/blob/main/docs/DATA_SOURCES.md', label: 'Data sources', external: true },
      { href: 'https://github.com/h55n/slopesense/blob/main/CHANGELOG.md', label: 'Changelog', external: true },
      { href: 'https://github.com/h55n/slopesense/blob/main/CONTRIBUTING.md', label: 'Contributing', external: true },
      { href: 'https://github.com/h55n/slopesense/blob/main/LICENSE', label: 'Apache 2.0 license', external: true },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="relative mt-24 overflow-hidden border-t border-white/5 bg-slope-bg">
      <div className="relative mx-auto max-w-[1600px] px-6 sm:px-8 lg:px-12">
        <div className="relative z-10 grid gap-12 pt-14 pb-72 sm:pb-80 lg:grid-cols-[1.2fr_2fr] lg:pb-[22rem]">
          <div className="max-w-md">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-[10px] border border-slope-accent/25 bg-slope-accent/10">
                <svg width="15" height="15" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path d="M7 1L13 12H1L7 1Z" stroke="#f4c95d" strokeWidth="1.5" strokeLinejoin="round" fill="rgba(244,201,93,0.08)" />
                  <path d="M7 5L9.5 10H4.5L7 5Z" fill="#f4c95d" opacity="0.6" />
                </svg>
              </div>
              <span className="font-serif text-2xl text-white">SlopeSense</span>
            </div>
            <p className="mt-4 text-base-sm leading-relaxed text-white/50">
              Landslide risk intelligence for India. Free satellite data fused into a block-level
              Failure Probability Index, delivered 24 to 48 hours before the slope moves.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
            {COLUMNS.map((col) => (
              <div key={col.title}>
                <h3 className="font-sans text-tiny font-semibold uppercase tracking-[0.24em] text-white/70">
                  {col.title}
                </h3>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((l) => (
                    <li key={l.label}>
                      {'external' in l && l.external ? (
                        <a
                          href={l.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-base-sm text-white/45 transition-colors hover:text-slope-accent"
                        >
                          {l.label}
                        </a>
                      ) : (
                        <Link href={l.href} className="text-base-sm text-white/45 transition-colors hover:text-slope-accent">
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
      </div>

      {/* Illustration band */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-[18rem] sm:h-[22rem] lg:h-[26rem]">
        <Image
          src="/art/footer.webp"
          alt=""
          fill
          sizes="100vw"
          className="object-cover object-bottom"
        />
        <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-slope-bg to-transparent" />
      </div>

      <div className="relative z-10 border-t border-black/20 bg-[#0b0b0c]/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-6 py-4 text-small text-white/50 sm:px-8 lg:px-12">
          <span>&copy; 2026 SlopeSense. Built to give districts a day&apos;s notice.</span>
          <span className="flex gap-5">
            <a href="https://github.com/h55n/slopesense" target="_blank" rel="noopener noreferrer" className="underline-offset-4 hover:text-white hover:underline">Source</a>
            <Link href="/api-docs" className="underline-offset-4 hover:text-white hover:underline">API</Link>
            <Link href="/status" className="underline-offset-4 hover:text-white hover:underline">Status</Link>
          </span>
        </div>
      </div>
    </footer>
  );
}
