import type { Metadata } from 'next';
import Script from 'next/script';
import Navigation from '@/components/Navigation';
import Footer from '@/components/Footer';
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
    <html lang="en">
      <head>
      </head>
      <body className="bg-paper text-ink antialiased">
        <Navigation />
        {children}
        <Footer />
        <Script src="/_vercel/insights/script.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
