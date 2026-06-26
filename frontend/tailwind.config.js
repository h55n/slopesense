/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        slope: {
          bg:      '#080809',
          surface: '#ffffff',
          panel:   'rgba(255, 255, 255, 0.03)',
          card:    '#111114',
          border:  'rgba(255, 255, 255, 0.07)',
          accent:  '#c5ff4a',
          accent2: '#a8f038',
          muted:   'rgba(255,255,255,0.45)',
          ink:     '#ffffff',
        },
        normal:     { DEFAULT: '#10b981', bg: 'rgba(16, 185, 129, 0.08)' },
        watch:      { DEFAULT: '#f59e0b', bg: 'rgba(245, 158, 11, 0.08)' },
        warning:    { DEFAULT: '#ef4444', bg: 'rgba(239, 68, 68, 0.08)' },
        emergency:  { DEFAULT: '#c5ff4a', bg: 'rgba(197, 255, 74, 0.08)' },
        monitoring: { DEFAULT: '#71717a', bg: 'rgba(113, 113, 122, 0.08)' },
      },
      fontFamily: {
        sans:  ['"Inter"', 'system-ui', 'sans-serif'],
        serif: ['"PT Serif"', 'Georgia', 'serif'],
        mono:  ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial':  'radial-gradient(var(--tw-gradient-stops))',
        'glass-gradient':   'linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%)',
        'lime-gradient':    'linear-gradient(135deg, rgba(197, 255, 74, 0.12) 0%, rgba(197, 255, 74, 0.03) 100%)',
        'hero-gradient':    'radial-gradient(ellipse 80% 40% at 50% -10%, rgba(197,255,74,0.07), transparent)',
      },
      boxShadow: {
        'glass':                 '0 4px 24px 0 rgba(0, 0, 0, 0.4)',
        'glass-lg':              '0 8px 48px 0 rgba(0, 0, 0, 0.5)',
        'glow-lime':             '0 0 16px 0 rgba(197, 255, 74, 0.12)',
        'glow-lime-strong':      '0 0 28px 0 rgba(197, 255, 74, 0.25)',
        'glow-lime-xl':          '0 0 48px 0 rgba(197, 255, 74, 0.18)',
        'tier-emergency':        '0 0 20px rgba(197,255,74,0.2)',
        'tier-warning':          '0 0 20px rgba(239,68,68,0.15)',
        'tier-watch':            '0 0 20px rgba(245,158,11,0.12)',
        'inner-glow':            'inset 0 1px 0 rgba(255,255,255,0.06)',
      },
      animation: {
        'float':            'float 6s ease-in-out infinite',
        'pulse-lime':       'pulse-lime 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-slow':       'pulse 3s ease-in-out infinite',
        'slide-up':         'slide-up 0.6s ease-out forwards',
        'draw-line':        'draw-line 1s ease-out forwards',
        'glow-breathe':     'glow-breathe 3s ease-in-out infinite',
        'scan-line':        'scan-line 3s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-8px)' },
        },
        'pulse-lime': {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 0 0 rgba(197,255,74,0.4)' },
          '50%':      { opacity: '0.6', boxShadow: '0 0 0 6px rgba(197,255,74,0)' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'draw-line': {
          from: { strokeDashoffset: '100%' },
          to:   { strokeDashoffset: '0%' },
        },
        'glow-breathe': {
          '0%, 100%': { boxShadow: '0 0 12px rgba(197,255,74,0.1)' },
          '50%':      { boxShadow: '0 0 28px rgba(197,255,74,0.25)' },
        },
        'scan-line': {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(400%)' },
        },
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
    },
  },
  plugins: [],
};
