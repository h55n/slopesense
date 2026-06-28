'use client';

import { useState } from 'react';
import Link from 'next/link';

export default function DevelopersPage() {
  const [formData, setFormData] = useState({ name: '', email: '', organization: '' });
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/v1/apikeys/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate API key');
      }

      setApiKey(data.key);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col items-center py-16 px-4">
      <div className="max-w-2xl w-full">
        <div className="mb-8">
          <Link href="/api-docs" className="text-blue-400 hover:text-blue-300 flex items-center gap-2 mb-6">
            <span>&larr;</span> Back to API Docs
          </Link>
          <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400 mb-4">
            SlopeSense Developer Portal
          </h1>
          <p className="text-slate-400 text-lg">
            Generate an API key to programmatically access landslide risk data, historical FPI scores, and regional alerts.
          </p>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700 rounded-2xl p-8 shadow-2xl">
          {!apiKey ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Full Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  placeholder="Jane Doe"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Email Address</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  placeholder="jane@university.edu"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Organization (Optional)</label>
                <input
                  type="text"
                  value={formData.organization}
                  onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                  className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  placeholder="Research Institute"
                />
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-medium py-3 rounded-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Generating...' : 'Generate API Key'}
              </button>
            </form>
          ) : (
            <div className="space-y-6">
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-6 text-center">
                <h3 className="text-xl font-bold text-emerald-400 mb-2">API Key Generated!</h3>
                <p className="text-slate-300 text-sm mb-6">
                  Please copy this key and store it somewhere safe. For security reasons, <strong className="text-white">it will not be shown again</strong>.
                </p>

                <div className="flex items-center gap-2 bg-slate-900 p-2 rounded-lg border border-slate-700">
                  <code className="flex-1 text-left text-sm text-blue-300 px-3 overflow-x-auto whitespace-nowrap">
                    {apiKey}
                  </code>
                  <button
                    onClick={handleCopy}
                    className="shrink-0 bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-md transition-colors text-sm font-medium"
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => {
                    setApiKey(null);
                    setFormData({ name: '', email: '', organization: '' });
                  }}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 py-3 rounded-lg font-medium transition-colors"
                >
                  Generate Another
                </button>
                <Link
                  href="/api-docs"
                  className="flex-1 bg-blue-600 hover:bg-blue-500 text-white text-center py-3 rounded-lg font-medium transition-colors"
                >
                  Go to API Docs
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
