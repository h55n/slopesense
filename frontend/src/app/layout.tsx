import type { Metadata } from 'next';
import Navigation from '@/components/Navigation';
import './globals.css';

export const metadata: Metadata = {
  title: 'SlopeSense — Landslide Risk Intelligence Platform',
  description:
    "India's operational landslide risk intelligence platform. Block-level FPI scoring, live alerts, CAP v1.2 feed, and 6-event retrospective validation.",
  keywords: ['landslide', 'risk', 'India', 'NDMA', 'disaster management', 'early warning', 'FPI', 'SlopeSense'],
  openGraph: {
    title: 'SlopeSense — Landslide Risk Intelligence Platform',
    description:
      'Block-level landslide risk intelligence for India. Live alerts, retrospective validation, and multilingual WhatsApp dispatch.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;0,14..32,800;1,14..32,400&family=PT+Serif:wght@400;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-slope-bg text-white antialiased">
        <Navigation />
        {children}
      </body>
    </html>
  );
}
