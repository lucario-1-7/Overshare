/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // MICROCRAFT arcade palette (PLAN §4.1)
        ink: '#0b0f17',
        panel: '#11161f',
        panel2: '#0e1320',
        line: '#21262d',
        muted: '#8b949e',
        fg: '#e6edf3',
        neon: '#7ee787',
        cyan: '#79c0ff',
        danger: '#ff7b72',
        amber: '#f0b72f',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        neon: '0 0 0 1px rgba(126,231,135,0.35), 0 0 24px -8px rgba(126,231,135,0.45)',
        panel: '0 1px 0 rgba(255,255,255,0.03), 0 8px 24px -16px rgba(0,0,0,0.8)',
      },
      keyframes: {
        grow: { '0%': { width: '0%' }, '100%': { width: 'var(--w)' } },
        fadein: { '0%': { opacity: 0, transform: 'translateY(6px)' }, '100%': { opacity: 1, transform: 'none' } },
      },
      animation: {
        grow: 'grow 0.8s cubic-bezier(.22,1,.36,1) forwards',
        fadein: 'fadein 0.4s ease forwards',
      },
    },
  },
  plugins: [],
}
