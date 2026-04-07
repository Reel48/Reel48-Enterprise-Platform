# ADR-008: IBM Carbon as the Primary Design System
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  This ADR documents the decision to adopt IBM Carbon Design System as      ║
# ║  the primary UI component library for the Reel48+ frontend. This affects   ║
# ║  component architecture, styling approach, dependency management, and      ║
# ║  the relationship between Carbon and Tailwind CSS.                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

## Status
Accepted

## Date
2026-04-06

## Context
Reel48+ is an enterprise apparel management platform serving companies with
100-10,000+ employees. The frontend is approximately 70% dense admin tooling
(data tables, approval workflows, invoicing, user management) and 30%
consumer-like experience (catalog browsing, ordering).

The frontend needs a component library that provides:

1. Enterprise-grade data tables with sorting, filtering, pagination, and batch
   actions (for order management, invoice lists, user management)
2. Comprehensive form components (for profiles, product management, approvals)
3. Consistent design tokens and theming (for brand customization per deployment)
4. Accessibility compliance out of the box (WCAG 2.1 AA — enterprise clients
   often require this contractually)
5. A mature, well-documented component set that reduces custom UI development

The harness originally specified Tailwind CSS as the sole styling approach with
custom UI primitives (Button, Input, Modal, DataTable) to be built in
`src/components/ui/`. Building and maintaining these custom primitives would
consume significant development time and produce components that lack the depth
of a dedicated design system (e.g., keyboard navigation, screen reader support,
complex data table interactions).

## Decision
Adopt **IBM Carbon Design System** (`@carbon/react`) as the primary component
library. Tailwind CSS is retained as a utility layer for layout and custom
spacing. The custom UI primitives directory (`src/components/ui/`) is repurposed
for Reel48+-specific composite components built from Carbon primitives.

**Package dependencies:**
- `@carbon/react` — Components, icons, and React bindings
- `@carbon/styles` — SCSS design tokens and theme customization
- `sass` — Build dependency for SCSS compilation

**Coexistence model:**
- Carbon provides all standard UI components (buttons, inputs, modals, tables,
  dropdowns, notifications, tabs, breadcrumbs, pagination, etc.)
- Carbon's variant system (props like `kind`, `size`, `type`) replaces cva/clsx
- Tailwind provides layout utilities (flex, grid, gap, padding, margin)
- Brand theming is done via Carbon SCSS variable overrides, not Tailwind config
- Tailwind's color tokens should be aligned with Carbon's theme tokens to
  prevent visual inconsistency

## Alternatives Considered

### shadcn/ui (Radix-based, Tailwind-native)
- **Pros:** Copy-paste model gives full control over component source; uses
  Tailwind natively (no styling conflict); growing community; excellent
  developer experience; lightweight
- **Cons:** Not a design system — it is a collection of unstyled primitives that
  require custom styling to form a cohesive design language; no built-in
  enterprise data table with sorting, filtering, batch actions, and pagination
  as a unified component; no design token system or theming infrastructure;
  each component must be individually maintained in the project
- **Why rejected:** shadcn/ui is excellent for startups and products that want
  maximum flexibility, but Reel48+ is an enterprise platform that needs a
  complete, pre-integrated component set with a consistent design language.
  Building enterprise-grade data tables and workflow patterns from Radix
  primitives would negate the time savings of using a library.

### Material UI (MUI)
- **Pros:** Largest React component library by npm downloads; comprehensive
  component set; strong theming system; large community
- **Cons:** Material Design aesthetic is recognizable and consumer-oriented,
  which may not suit an enterprise apparel context; theming to override the
  Material Design look requires significant effort; CSS-in-JS runtime overhead
  (Emotion); potential licensing considerations for premium components
  (DataGrid Pro)
- **Why rejected:** MUI's Material Design aesthetic makes the platform feel
  like a Google product rather than a premium enterprise apparel platform.
  The CSS-in-JS approach (Emotion) adds runtime overhead. Carbon's industrial
  design language is a better fit for B2B enterprise software.

### Fluent UI (Microsoft)
- **Pros:** Enterprise-focused design system; good accessibility; comprehensive
  component set; used in Microsoft 365 and Teams
- **Cons:** Strongly associated with Microsoft's design language; React
  components are in transition between v8 and v9 with some components not yet
  migrated; documentation quality varies; smaller community outside Microsoft
  ecosystem
- **Why rejected:** Fluent UI v9 is still stabilizing. The Microsoft visual
  identity is strong and may not be desirable for a standalone platform brand.
  Carbon's stable release cycle and neutral enterprise aesthetic are preferable.

### Headless UI (Tailwind Labs)
- **Pros:** Fully unstyled — maximum Tailwind integration; lightweight;
  accessible primitives
- **Cons:** Very limited component set (fewer than 10 patterns); no data
  tables, no form components, no notifications; everything beyond basic
  interaction patterns must be built from scratch
- **Why rejected:** An enterprise platform with data tables, multi-step forms,
  notification systems, and complex navigation needs far more than Headless UI
  provides. The development time to build the remaining components would be
  excessive.

## Consequences

### Positive
- Data tables, form components, and navigation patterns are available
  immediately without custom development
- WCAG 2.1 AA accessibility is built into every Carbon component
- Consistent design language across the entire platform from day one
- SCSS theming allows brand customization without forking components
- Carbon's variant system (props) eliminates the need for cva/clsx
- Carbon is actively maintained by IBM with a stable release cadence

### Negative
- SCSS dependency added (requires `sass` package and SCSS compilation in
  Next.js build pipeline)
- Two styling systems coexist (Carbon SCSS + Tailwind), increasing the
  learning curve for contributors unfamiliar with the hybrid approach
- Carbon's opinionated grid system may occasionally overlap with Tailwind's
  grid utilities — clear guidance is needed on when to use which
- Bundle size increase from Carbon components (mitigated by tree-shaking with
  direct named imports from `@carbon/react`)

### Risks
- **Carbon + Tailwind class conflicts:** Mitigated by the rule that Tailwind
  must never override Carbon component internals. Tailwind is used only for
  layout and spacing BETWEEN components, not within them.
- **Theme token drift:** If Tailwind config defines colors that differ from
  Carbon theme tokens, the UI will look inconsistent. Mitigated by aligning
  Tailwind's custom color tokens with Carbon's theme values in the config.
- **Developer confusion about which system to use:** Mitigated by clear
  harness guidance: "If Carbon has a component, use Carbon. If you need
  layout, use Tailwind."

## References
- IBM Carbon Design System: https://carbondesignsystem.com
- @carbon/react: https://react.carbondesignsystem.com
- Carbon Theming: https://carbondesignsystem.com/guidelines/themes/overview
- Carbon + Next.js setup: https://github.com/carbon-design-system/carbon/tree/main/examples/nextjs
