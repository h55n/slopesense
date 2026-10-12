/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontSize: {
        'micro': ['12px', { lineHeight: '16px' }],
        'tiny':  ['12px', { lineHeight: '16px' }],
        'small': ['12px', { lineHeight: '16px' }],
        'base-sm': ['13px', { lineHeight: '20px' }],
      },
      letterSpacing: {
        'loose': '0.15em',
        'looser': '0.2em',
        'widest': '0.24em',
        'mega': '0.28em',
      },
      colors: {
        // Light editorial palette. The legacy `white` / `black` / grey / status scales are
        // remapped so older utility classes (text-white/50, border-white/10, bg-black/20 ...)
        // resolve to ink-on-paper instead of light-on-dark.
        white: '#1d2a21',
        black: '#f4f1e8',
        paper: { DEFAULT: '#f4f1e8', 2: '#ece7d8', 3: '#e3ddca', card: '#fbf9f3' },
        ink:   { DEFAULT: '#1d2a21', soft: '#4a574d', mute: '#7b867c' },
        forest: { DEFAULT: '#2f4a37', deep: '#1f3326', mid: '#3f6148', sage: '#9db39f', mist: '#dfe8dc' },
        sky:   { band: '#dde7e9', deep: '#c6d8dc' },
        saffron: { DEFAULT: '#e0a13a', deep: '#b8730f', soft: '#f6e3bb' },
        slope: {
          bg:      '#f4f1e8',
          surface: '#fbf9f3',
          panel:   'rgba(29, 42, 33, 0.03)',
          card:    '#fbf9f3',
          border:  'rgba(29, 42, 33, 0.10)',
          accent:  '#b8730f',
          accent2: '#9c5f0b',
          muted:   'rgba(29,42,33,0.55)',
          ink:     '#1d2a21',
        },
        slate: { 100: '#1d2a21', 200: '#2c3a30', 300: '#3d4a40', 400: '#5b675e', 500: '#6f7a71', 600: '#a9b0a2', 700: '#cfcdbc', 800: '#e3ddca', 900: '#ece7d8', 950: '#f4f1e8' },
        zinc:  { 500: '#6f7a71', 600: '#a9b0a2', 700: '#cfcdbc', 800: '#e3ddca', 900: '#ece7d8' },
        emerald: { 300: '#3a8a5a', 400: '#2f7a4d', 500: '#2f7a4d', 800: '#bcd6c2', 950: '#e1ecdd' },
        red:     { 300: '#b73a28', 400: '#bd3f2a', 500: '#bd3f2a', 800: '#e4b3a6', 950: '#f4dcd3' },
        amber:   { 300: '#a8680f', 400: '#b06f12', 500: '#c98516', 600: '#c98516', 800: '#e5cb93', 950: '#f4e7c6' },
        blue:    { 400: '#3b7aa3', 500: '#3b7aa3', 600: '#3b7aa3', 950: '#dbe7ee' },
        lime:    { 300: '#2f4a37', 400: '#2f4a37' },
        orange:  { 400: '#c25a1b' },
        normal:     { DEFAULT: '#3f8a58', bg: 'rgba(63, 138, 88, 0.10)' },
        watch:      { DEFAULT: '#d9962b', bg: 'rgba(217, 150, 43, 0.12)' },
        warning:    { DEFAULT: '#d4541f', bg: 'rgba(212, 84, 31, 0.10)' },
        emergency:  { DEFAULT: '#a3211b', bg: 'rgba(163, 33, 27, 0.10)' },
        monitoring: { DEFAULT: '#7b867c', bg: 'rgba(123, 134, 124, 0.10)' },
      },
      fontFamily: {
        sans:  ['"Inter"', 'system-ui', 'sans-serif'],
        serif: ['"Newsreader"', 'Georgia', 'serif'],
        mono:  ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial':  'radial-gradient(var(--tw-gradient-stops))',
        'glass-gradient':   'linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%)',
        'lime-gradient':    'linear-gradient(135deg, rgba(244,201,93, 0.12) 0%, rgba(244,201,93, 0.03) 100%)',
        'hero-gradient':    'radial-gradient(ellipse 80% 40% at 50% -10%, rgba(244,201,93,0.07), transparent)',
      },
      boxShadow: {
        'glass':                 '0 1px 2px rgba(29,42,33,0.05), 0 8px 24px rgba(29,42,33,0.06)',
        'glass-lg':              '0 2px 4px rgba(29,42,33,0.05), 0 20px 48px rgba(29,42,33,0.10)',
        'glow-lime':             'none',
        'glow-lime-strong':      '0 6px 18px rgba(47,74,55,0.22)',
        'glow-lime-xl':          '0 10px 30px rgba(47,74,55,0.2)',
        'tier-emergency':        '0 0 0 3px rgba(163,33,27,0.10)',
        'tier-warning':          '0 0 0 3px rgba(212,84,31,0.10)',
        'tier-watch':            '0 0 0 3px rgba(217,150,43,0.12)',
        'inner-glow':            'none',
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
          '0%, 100%': { opacity: '1', boxShadow: '0 0 0 0 rgba(244,201,93,0.4)' },
          '50%':      { opacity: '0.6', boxShadow: '0 0 0 6px rgba(244,201,93,0)' },
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
          '0%, 100%': { boxShadow: '0 0 12px rgba(244,201,93,0.1)' },
          '50%':      { boxShadow: '0 0 28px rgba(244,201,93,0.25)' },
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
