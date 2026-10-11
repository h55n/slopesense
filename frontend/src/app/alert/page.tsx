'use client';

import { Suspense } from 'react';
import AlertDetailPage from '../alerts/[id]/page';

// Static entry point (/alert?id=...) so the detail page works on hosts where
// dynamic routes are not resolved.
export default function AlertPage() {
  return (
    <Suspense fallback={null}>
      <AlertDetailPage />
    </Suspense>
  );
}
