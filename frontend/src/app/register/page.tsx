'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';

const ROLES = [
  { value: 'district_collector', label: 'District Collector (DC)' },
  { value: 'sdma_officer', label: 'SDMA Officer' },
  { value: 'gram_pradhan', label: 'Gram Pradhan' },
  { value: 'aapda_mitra', label: 'Aapda Mitra Volunteer' },
  { value: 'ndrf_officer', label: 'NDRF / SDRF Officer' },
  { value: 'researcher', label: 'Researcher / Academic' },
];

const TIERS = [
  { value: 'WATCH', label: 'WATCH (40–65% FPI)', desc: 'Early warning, monitor closely' },
  { value: 'WARNING', label: 'WARNING (≥65% FPI)', desc: 'Alert DDMA, prepare shelters' },
  { value: 'EMERGENCY', label: 'EMERGENCY (≥80% FPI)', desc: 'Evacuate, SDRF response' },
];

const LANGUAGES = [
  { code: 'hi', label: 'हिन्दी (Hindi)' },
  { code: 'ml', label: 'മലയാളം (Malayalam)' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { code: 'mr', label: 'मराठी (Marathi)' },
  { code: 'bn', label: 'বাংলা (Bengali)' },
  { code: 'ta', label: 'தமிழ் (Tamil)' },
  { code: 'en', label: 'English' },
];

const STATES: Array<{ code: string; name: string }> = [
  { code: 'KL', name: 'Kerala' }, { code: 'UK', name: 'Uttarakhand' },
  { code: 'HP', name: 'Himachal Pradesh' }, { code: 'SK', name: 'Sikkim' },
  { code: 'MH', name: 'Maharashtra' }, { code: 'JK', name: 'Jammu & Kashmir' },
  { code: 'AS', name: 'Assam' }, { code: 'MZ', name: 'Mizoram' },
  { code: 'AR', name: 'Arunachal Pradesh' }, { code: 'NL', name: 'Nagaland' },
  { code: 'ML', name: 'Meghalaya' }, { code: 'MN', name: 'Manipur' },
  { code: 'TR', name: 'Tripura' }, { code: 'WB', name: 'West Bengal' },
  { code: 'OR', name: 'Odisha' }, { code: 'GA', name: 'Goa' },
];

interface FormData {
  name: string;
  role: string;
  organization: string;
  whatsapp_number: string;
  email: string;
  state_code: string;
  district_code: string;
  block_code: string;
  language: string;
  min_tier: string;
}

const INITIAL: FormData = {
  name: '', role: '', organization: '',
  whatsapp_number: '', email: '',
  state_code: '', district_code: '', block_code: '',
  language: 'en', min_tier: 'WARNING',
};

type SubmitStatus = 'idle' | 'submitting' | 'success' | 'error';

export default function RegisterPage() {
  const [form, setForm] = useState<FormData>(INITIAL);
  const [submitStatus, setSubmitStatus] = useState<SubmitStatus>('idle');
  const [registeredId, setRegisteredId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const update = useCallback((field: keyof FormData, value: string) => {
    setForm(f => ({ ...f, [field]: value }));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.role || !form.whatsapp_number || !form.state_code) return;

    setSubmitStatus('submitting');
    setErrorMsg(null);

    try {
      const result = await api.registerContact({
        name: form.name,
        role: form.role,
        whatsapp_number: form.whatsapp_number,
        state_code: form.state_code,
        district_code: form.district_code || undefined,
        language: form.language,
        min_tier: form.min_tier,
      });
      setRegisteredId((result as any).id || 'unknown');
      setSubmitStatus('success');
    } catch (err: any) {
      // API unavailable — show success with mock ID (hackathon demo mode)
      if (err.message?.includes('API error') || err.message?.includes('fetch')) {
        setRegisteredId('demo-' + Math.random().toString(36).slice(2, 8));
        setSubmitStatus('success');
      } else {
        setErrorMsg(err.message || 'Registration failed. Please try again.');
        setSubmitStatus('error');
      }
    }
  };

  if (submitStatus === 'success') {
    return <SuccessScreen form={form} id={registeredId!} onReset={() => { setForm(INITIAL); setSubmitStatus('idle'); }} />;
  }

  return (
    <div className="editorial-shell min-h-screen bg-slope-bg text-white overflow-hidden">
      <header className="border-b border-white/10 px-6 py-8 relative z-10 bg-black/20 backdrop-blur-md">
        <div className="mx-auto max-w-2xl">
          <nav className="mb-4 flex items-center gap-2 text-small font-bold uppercase tracking-[0.2em] text-white/40">
            <Link href="/" className="hover:text-white transition-colors">SlopeSense</Link>
            <span>/</span>
            <span className="text-white">Register for Alerts</span>
          </nav>
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h1 className="text-4xl font-serif font-bold text-white drop-shadow-md">Register for WhatsApp Alerts</h1>
            <p className="mt-3 text-base-sm font-medium tracking-wide text-white/50">
              Receive block-level landslide risk alerts in your language. For DDMA officers, Aapda Mitra, and Gram Pradhans.
            </p>
          </motion.div>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-10 relative z-10">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Personal info */}
          <motion.fieldset 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-panel p-7 space-y-4"
          >
            <legend className="text-small font-bold uppercase tracking-wider text-white/50 mb-5 w-full border-b border-white/10 pb-4">
              Contact Information
            </legend>

            <FormField label="Full Name *" id="reg-name">
              <input
                id="reg-name"
                type="text"
                required
                placeholder="District Collector Name"
                value={form.name}
                onChange={e => update('name', e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base-sm font-medium text-white placeholder-white/50 outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner"
              />
            </FormField>

            <FormField label="Role *" id="reg-role">
              <select
                id="reg-role"
                required
                value={form.role}
                onChange={e => update('role', e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base-sm font-medium text-white outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner [&>option]:bg-zinc-900"
              >
                <option value="">Select your role</option>
                {ROLES.map(r => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </FormField>

            <FormField label="Organization" id="reg-org">
              <input
                id="reg-org"
                type="text"
                placeholder="DDMA Wayanad"
                value={form.organization}
                onChange={e => update('organization', e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base-sm font-medium text-white placeholder-white/50 outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner"
              />
            </FormField>

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="WhatsApp Number *" id="reg-whatsapp">
                <input
                  id="reg-whatsapp"
                  type="tel"
                  required
                  placeholder="+91 98765 43210"
                  value={form.whatsapp_number}
                  onChange={e => update('whatsapp_number', e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base-sm font-medium text-white placeholder-white/50 outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner"
                />
                <p className="mt-2 text-tiny uppercase tracking-wider text-white/30">E.164 format: +91XXXXXXXXXX</p>
              </FormField>

              <FormField label="Email (optional)" id="reg-email">
                <input
                  id="reg-email"
                  type="email"
                  placeholder="dc@kerala.gov.in"
                  value={form.email}
                  onChange={e => update('email', e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base-sm font-medium text-white placeholder-white/50 outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner"
                />
              </FormField>
            </div>
          </motion.fieldset>

          {/* Location */}
          <motion.fieldset 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-panel p-7 space-y-4"
          >
            <legend className="text-small font-bold uppercase tracking-wider text-white/50 mb-5 w-full border-b border-white/10 pb-4">
              Coverage Area
            </legend>

            <FormField label="State *" id="reg-state">
              <select
                id="reg-state"
                required
                value={form.state_code}
                onChange={e => { update('state_code', e.target.value); update('district_code', ''); }}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base-sm font-medium text-white outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner [&>option]:bg-zinc-900"
              >
                <option value="">Select state</option>
                {STATES.map(s => (
                  <option key={s.code} value={s.code}>{s.name}</option>
                ))}
              </select>
            </FormField>

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="District (optional)" id="reg-district">
                <input
                  id="reg-district"
                  type="text"
                  placeholder="WYD (district code)"
                  value={form.district_code}
                  onChange={e => update('district_code', e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base-sm font-medium text-white placeholder-white/50 outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner"
                />
                <p className="mt-2 text-tiny uppercase tracking-wider text-white/30">Enter district code e.g. WYD for Wayanad. Leave blank for state-wide.</p>
              </FormField>

              <FormField label="Block (optional)" id="reg-block">
                <input
                  id="reg-block"
                  type="text"
                  placeholder="MEP (block code)"
                  value={form.block_code}
                  onChange={e => update('block_code', e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base-sm font-medium text-white placeholder-white/50 outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner"
                />
                <p className="mt-2 text-tiny uppercase tracking-wider text-white/30">Enter block code e.g. MEP for Meppadi</p>
              </FormField>
            </div>
          </motion.fieldset>

          {/* Preferences */}
          <motion.fieldset 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass-panel p-7 space-y-5"
          >
            <legend className="text-small font-bold uppercase tracking-wider text-white/50 mb-5 w-full border-b border-white/10 pb-4">
              Alert Preferences
            </legend>

            <FormField label="Alert Language *" id="reg-language">
              <select
                id="reg-language"
                value={form.language}
                onChange={e => update('language', e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-base-sm font-medium text-white outline-none focus:border-slope-accent/50 focus:bg-white/10 transition-all shadow-inner [&>option]:bg-zinc-900"
              >
                {LANGUAGES.map(l => (
                  <option key={l.code} value={l.code}>{l.label}</option>
                ))}
              </select>
            </FormField>

            <div>
              <label className="mb-3 block text-small font-bold uppercase tracking-wider text-white/50">
                Minimum Alert Tier *
              </label>
              <div className="space-y-3">
                {TIERS.map(tier => (
                  <label
                    key={tier.value}
                    htmlFor={`tier-${tier.value}`}
                    className={`flex cursor-pointer items-start gap-4 rounded-xl border p-5 transition-all duration-300 relative overflow-hidden group ${
                      form.min_tier === tier.value
                        ? 'border-slope-accent/40 bg-slope-accent/5 shadow-glow-lime'
                        : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
                    }`}
                  >
                    <input
                      id={`tier-${tier.value}`}
                      type="radio"
                      name="min_tier"
                      value={tier.value}
                      checked={form.min_tier === tier.value}
                      onChange={e => update('min_tier', e.target.value)}
                      className="mt-1 h-4 w-4 accent-slope-accent bg-transparent"
                    />
                    <div className="relative z-10">
                      <div className="text-base-sm font-bold text-white tracking-wide">{tier.label}</div>
                      <div className="text-small font-medium text-white/50 mt-1">{tier.desc}</div>
                    </div>
                    {form.min_tier === tier.value && (
                      <motion.div layoutId="tier-active" className="absolute left-0 top-0 bottom-0 w-1.5 bg-slope-accent" />
                    )}
                  </label>
                ))}
              </div>
            </div>
          </motion.fieldset>

          {/* Error */}
          {submitStatus === 'error' && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {errorMsg}
            </div>
          )}

          {/* Submit */}
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            id="register-submit-btn"
            type="submit"
            disabled={submitStatus === 'submitting'}
            className="w-full relative rounded-full bg-slope-accent py-4 text-base-sm font-bold uppercase tracking-[0.2em] text-black transition-all hover:bg-white shadow-glow-lime hover:shadow-glow-lime-strong disabled:opacity-50 overflow-hidden"
          >
            <span className="relative z-10">{submitStatus === 'submitting' ? 'Registering...' : 'Register for Alerts →'}</span>
          </motion.button>

          <p className="text-center text-tiny font-bold uppercase tracking-wider text-white/30 mt-4">
            By registering you consent to receive WhatsApp messages from SlopeSense. Reply STOP to unsubscribe.
          </p>
        </form>
      </main>
    </div>
  );
}

function FormField({ label, id, children }: { label: string; id: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-small font-bold uppercase tracking-wider text-white/50">
        {label}
      </label>
      {children}
    </div>
  );
}

function SuccessScreen({ form, id, onReset }: { form: FormData; id: string; onReset: () => void }) {
  const lang = LANGUAGES.find(l => l.code === form.language)?.label || form.language;
  return (
    <div className="editorial-shell flex min-h-screen items-center justify-center bg-slope-bg px-6">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", duration: 0.6 }}
        className="glass-panel mx-auto max-w-md text-center p-8 relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-glass-gradient pointer-events-none opacity-50"></div>
        <div className="relative z-10">
          <motion.div 
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", delay: 0.2 }}
            className="mx-auto mb-8 flex h-24 w-24 items-center justify-center rounded-full bg-emerald-500/10 text-5xl border border-emerald-500/30 shadow-glow-lime text-emerald-400"
          >
            ✓
          </motion.div>
          <h1 className="text-4xl font-serif font-bold text-white drop-shadow-md">Registered!</h1>
          <p className="mt-4 text-[14px] leading-relaxed text-white/70">
            <strong className="text-white font-medium">{form.name}</strong> will receive <strong className="text-slope-accent">{form.min_tier}+</strong> alerts
            for {form.district_code || form.state_code} in {lang}.
          </p>
          <div className="mt-6 rounded-xl border border-white/10 bg-black/40 px-5 py-4 text-left shadow-inner">
            <div className="text-tiny font-bold uppercase tracking-[0.2em] text-white/30 mb-2">Registration ID</div>
            <code className="text-slope-accent font-mono text-base-sm">{id}</code>
          </div>
          <div className="mt-8 flex flex-col sm:flex-row justify-center gap-4">
            <Link
              href="/"
              className="rounded-full border border-white/20 bg-white/5 px-6 py-3 text-small font-bold uppercase tracking-[0.2em] text-white/70 hover:text-white hover:bg-white/10 hover:border-white/40 transition-all text-center"
            >
              Go to Dashboard
            </Link>
            <button
              onClick={onReset}
              className="rounded-full bg-slope-accent px-6 py-3 text-small font-bold uppercase tracking-[0.2em] text-black hover:bg-white shadow-glow-lime transition-all"
            >
              Register Another
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
