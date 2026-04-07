import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // =====================================================================
        // CARBON TOKEN BRIDGES
        // These map Tailwind color utilities to Carbon's CSS custom properties,
        // ensuring Tailwind utilities stay in sync with carbon-theme.scss.
        // Usage: bg-interactive, text-text-primary, border-border-subtle, etc.
        // =====================================================================
        'interactive': 'var(--cds-interactive)',
        'bg-page': 'var(--cds-background)',
        'bg-card': 'var(--cds-layer-01)',
        'bg-brand': 'var(--cds-background-brand)',
        'bg-inverse': 'var(--cds-background-inverse)',
        'text-primary': 'var(--cds-text-primary)',
        'text-secondary': 'var(--cds-text-secondary)',
        'text-inverse': 'var(--cds-text-inverse)',
        'border-subtle': 'var(--cds-border-subtle-01)',
        'border-strong': 'var(--cds-border-strong-01)',
        'support-error': 'var(--cds-support-error)',
        'support-success': 'var(--cds-support-success)',
        'support-warning': 'var(--cds-support-warning)',
        'support-info': 'var(--cds-support-info)',

        // =====================================================================
        // BRAND CHARCOAL SCALE
        // For custom dark surfaces, sidebar elements, and brand-colored UI
        // that falls outside Carbon's token system.
        // =====================================================================
        'charcoal': {
          900: 'var(--r48-charcoal-900)', // #292c2f — primary brand
          800: 'var(--r48-charcoal-800)', // #353a3f — sidebar hover
          700: 'var(--r48-charcoal-700)', // #4a5056 — muted text on dark
          500: 'var(--r48-charcoal-500)', // #6f7479 — disabled on dark
        },

        // =====================================================================
        // TEAL INTERACTIVE SCALE
        // For gradients, custom hover states, and tinted backgrounds beyond
        // what the Carbon interactive token provides.
        // =====================================================================
        'teal': {
          900: 'var(--r48-teal-900)', // #063c44 — pressed/active
          700: 'var(--r48-teal-700)', // #0a6b6b — primary interactive
          600: 'var(--r48-teal-600)', // #0d8a8a — hover
          400: 'var(--r48-teal-400)', // #3db8b8 — interactive on dark
          200: 'var(--r48-teal-200)', // #a8e0e0 — selected row highlight
          50:  'var(--r48-teal-50)',  // #e0f5f5 — subtle info wash
        },

        // =====================================================================
        // ACCENT PALETTE — Fashion-Inspired
        // For charts, status badges, category differentiation, and feature
        // highlights. References CSS custom properties from carbon-theme.scss.
        // Usage: bg-accent-amethyst, text-accent-garnet, border-accent-navy
        // =====================================================================
        'accent': {
          amethyst:       'var(--r48-accent-amethyst)',       // #6929c4 — premium, featured
          azure:          'var(--r48-accent-azure)',          // #1192e8 — active status
          evergreen:      'var(--r48-accent-evergreen)',      // #005d5d — approved variant
          garnet:         'var(--r48-accent-garnet)',         // #9f1853 — urgent, high-priority
          coral:          'var(--r48-accent-coral)',          // #fa4d56 — overdue
          oxblood:        'var(--r48-accent-oxblood)',        // #570408 — rejected, cancelled
          navy:           'var(--r48-accent-navy)',           // #002d9c — processing
          rose:           'var(--r48-accent-rose)',           // #ee538b — promotional, seasonal
          saffron:        'var(--r48-accent-saffron)',        // #b28600 — pending review
          'midnight-teal': 'var(--r48-accent-midnight-teal)', // #022b30 — deep brand accent
        },
      },
    },
  },
  plugins: [],
};

export default config;
