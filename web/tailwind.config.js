/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: 'var(--color-surface)',
        'surface-hover': 'var(--color-surface-hover)',
        'surface-active': 'var(--color-surface-active)',
        'surface-elevated': 'var(--color-surface-elevated)',
        border: 'var(--color-border)',
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted': 'var(--color-text-muted)',
        accent: 'var(--color-accent)',
        'accent-hover': 'var(--color-accent-hover)',
        'accent-soft': 'var(--color-accent-soft)',
        'bubble-incoming': 'var(--color-bubble-incoming)',
        'bubble-outgoing': 'var(--color-bubble-outgoing)',
        danger: 'var(--color-danger)',
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
      },
      fontFamily: {
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(2, 8, 23, 0.05), 0 1px 1px rgba(2, 8, 23, 0.03)',
        'card-hover': '0 8px 24px rgba(2, 8, 23, 0.10), 0 2px 6px rgba(2, 8, 23, 0.06)',
        popover: '0 12px 32px rgba(2, 8, 23, 0.16), 0 4px 12px rgba(2, 8, 23, 0.08)',
        glow: '0 8px 24px rgba(79, 70, 229, 0.18)',
      },
      borderRadius: {
        bubble: '16px',
      },
      transitionTimingFunction: {
        gentle: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-8px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        pageIn: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        panelIn: {
          '0%': { opacity: '0', transform: 'translateY(10px) scale(0.996)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        itemIn: {
          '0%': { opacity: '0', transform: 'translateY(5px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        messageIn: {
          '0%': { opacity: '0', transform: 'translateY(8px) scale(0.995)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        toolbarIn: {
          '0%': { opacity: '0', transform: 'translateY(6px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        menuIn: {
          '0%': { opacity: '0', transform: 'translateY(-4px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        blobDrift: {
          '0%': { transform: 'translate3d(0, 0, 0) scale(1)' },
          '50%': { transform: 'translate3d(5vw, 4vh, 0) scale(1.12)' },
          '100%': { transform: 'translate3d(8vw, 6vh, 0) scale(1.04)' },
        },
        blobDriftAlt: {
          '0%': { transform: 'translate3d(0, 0, 0) scale(1.06)' },
          '50%': { transform: 'translate3d(-5vw, 5vh, 0) scale(1)' },
          '100%': { transform: 'translate3d(-3vw, 8vh, 0) scale(1.18)' },
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-in-out',
        'slide-in': 'slideIn 0.2s ease-out',
        'page-in': 'pageIn 0.45s cubic-bezier(0.22, 1, 0.36, 1) both',
        'panel-in': 'panelIn 0.5s cubic-bezier(0.22, 1, 0.36, 1) both',
        'item-in': 'itemIn 0.35s cubic-bezier(0.22, 1, 0.36, 1) both',
      },
    },
  },
  plugins: [],
}