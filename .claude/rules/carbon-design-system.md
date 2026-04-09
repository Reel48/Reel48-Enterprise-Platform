---
globs: "**/components/**,**/styles/**,**/*.scss,**/layout/**,**/ui/**,**/features/**"
---

# Rule: Carbon Design System
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This rule activates when Claude Code is working on React components,      ║
# ║  styling files, or layout files. It enforces the IBM Carbon design system  ║
# ║  conventions: component selection, import patterns, styling boundaries,    ║
# ║  icon usage, and the Carbon/Tailwind coexistence model.                    ║
# ║                                                                            ║
# ║  WHY THIS RULE?                                                            ║
# ║                                                                            ║
# ║  IBM Carbon is the primary design system for Reel48+ (see ADR-008).        ║
# ║  Every UI component, variant, and interaction pattern should use Carbon    ║
# ║  first. Tailwind is retained solely as a layout utility layer. Without     ║
# ║  explicit enforcement, Claude Code may recreate Carbon components in       ║
# ║  Tailwind, use incorrect import paths, mix styling approaches, or          ║
# ║  introduce bundle-bloating import patterns. This rule prevents all of      ║
# ║  these mistakes at the point where components are being written.           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Activates for: **/components/**, **/styles/**, **/*.scss, **/layout/**, **/ui/**, **/features/**

## Component Selection: Carbon First

If Carbon has a component for the UI element, use it. Do NOT recreate it in
Tailwind or build a custom implementation.

**Carbon provides (use these, not custom versions):**
- Buttons, links, icon buttons → `Button`, `IconButton`
- Text inputs, number inputs, text areas → `TextInput`, `NumberInput`, `TextArea`
- Selects, dropdowns, combo boxes → `Dropdown`, `ComboBox`, `MultiSelect`, `FilterableMultiSelect`
- Modals, dialogs → `Modal`, `ComposedModal`
- Data tables with sorting/filtering/pagination → `DataTable` + sub-components
- Tabs → `Tabs`, `TabList`, `Tab`, `TabPanels`, `TabPanel`
- Notifications → `InlineNotification`, `ToastNotification`, `ActionableNotification`
- Tags, badges → `Tag`
- Breadcrumbs → `Breadcrumb`, `BreadcrumbItem`
- Loading states → `Loading`, `InlineLoading`
- Pagination → `Pagination`
- Navigation → `SideNav`, `Header`, `HeaderNavigation`
- Layout grid → `Grid`, `Column`
- Theming → `Theme`
- Toggles, checkboxes, radio buttons → `Toggle`, `Checkbox`, `RadioButton`, `RadioButtonGroup`
- Date pickers → `DatePicker`, `DatePickerInput`
- Search → `Search`
- File uploader → `FileUploader`
- Progress indicators → `ProgressIndicator`, `ProgressStep`
- Structured lists → `StructuredListWrapper`, `StructuredListBody`, `StructuredListRow`, `StructuredListCell`
- Overflow menus → `OverflowMenu`, `OverflowMenuItem`
- Tooltips → `Tooltip`, `DefinitionTooltip`
- Accordions → `Accordion`, `AccordionItem`

**When to build custom (`src/components/ui/`):**
Only for Reel48+-specific composite components that COMBINE multiple Carbon
primitives with domain logic. Examples: `TenantBadge`, `EmptyState`, `PageHeader`,
`StatusIndicator`. These are compositions, not replacements.

## Import Patterns (Tree-Shaking)

### Components
Always use **named imports** directly from `@carbon/react`:

```typescript
// ✅ CORRECT — named imports, tree-shakeable
import { Button, TextInput, DataTable, Modal } from '@carbon/react';

// ❌ WRONG — wildcard import pulls entire library into bundle
import * as Carbon from '@carbon/react';

// ❌ WRONG — default import
import Carbon from '@carbon/react';

// ❌ WRONG — deep path imports (fragile, may break across versions)
import Button from '@carbon/react/es/components/Button';
```

### Icons
Icons are re-exported from `@carbon/react`. Use named imports:

```typescript
// ✅ CORRECT — named import from @carbon/react
import { Add, TrashCan, Edit, ChevronDown, Search } from '@carbon/react/icons';

// ✅ ALSO CORRECT — from the icons package directly
import { Add, TrashCan } from '@carbon/icons-react';

// ❌ WRONG — importing the entire icon set
import * as Icons from '@carbon/icons-react';
```

**Icon sizing:** Use the `size` prop. Available sizes: `16` (default), `20`, `24`, `32`.

```typescript
// ✅ CORRECT
<Add size={20} />

// ❌ WRONG — don't size icons with CSS/Tailwind
<Add className="w-5 h-5" />
```

## Styling Boundaries: Carbon vs Tailwind

### Carbon Handles (do NOT use Tailwind for these):
- **Component appearance** — colors, borders, shadows, font styles within components
- **Component variants** — use props: `kind`, `size`, `type`, `disabled`
- **Component states** — hover, focus, active, invalid, warn, disabled
- **Page-level grid** — `<Grid>` and `<Column>` for the main column layout of a page
- **Theming** — brand colors, token overrides via `src/styles/carbon-theme.scss`

### Tailwind Handles (use for these only):
- **Layout between components** — `flex`, `grid`, `gap-*`, `items-center`, `justify-between`
- **Spacing between components** — `mt-4`, `mb-8`, `px-6`, `py-4`
- **Responsive fine-tuning** — `sm:`, `md:`, `lg:` breakpoints for adjustments within a Column
- **Custom layout patterns** — Arranging cards in a grid, spacing form fields, aligning buttons

### The Grid Decision Rule
- **Carbon `<Grid>` + `<Column>`:** For the outermost page structure — defining how the page
  splits into columns at different breakpoints (e.g., 2-column admin layout, 3-column dashboard).
- **Tailwind `flex` / `grid` / `gap`:** For arranging items WITHIN a Carbon `<Column>` —
  laying out cards, spacing form fields, aligning action buttons.
- **Rule of thumb:** If you're defining the top-level column breakpoints of a page, use Carbon Grid.
  If you're arranging content inside a content area, use Tailwind.

### What NOT to Do
```typescript
// ❌ WRONG — Tailwind overriding Carbon component internals
<Button className="bg-blue-500 text-white rounded-lg">Submit</Button>

// ✅ CORRECT — Carbon props for variants
<Button kind="primary">Submit</Button>

// ❌ WRONG — Tailwind for component variants
<button className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700">Submit</button>

// ✅ CORRECT — Carbon component with Tailwind for layout context only
<div className="flex gap-4 justify-end mt-6">
  <Button kind="secondary">Cancel</Button>
  <Button kind="primary">Submit</Button>
</div>
```

## CSS Load Order

Carbon's styles MUST load BEFORE Tailwind's directives. If Tailwind's Preflight
(base CSS reset) loads after Carbon, it can override Carbon component styles and
break their appearance (e.g., button resets, heading sizes, list styles).

### Import Order in Global Stylesheet
```scss
// 1. Carbon theme and styles FIRST
@use '../styles/carbon-theme';

// 2. Tailwind directives AFTER Carbon
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### If Preflight Conflicts Occur
If Tailwind's Preflight causes visual issues with Carbon components:
1. **Preferred:** Use Tailwind's `@layer` ordering to ensure Carbon styles take priority
2. **Fallback:** Disable Preflight (`corePlugins: { preflight: false }` in `tailwind.config.ts`)
   and manually include only the resets that don't conflict with Carbon

## SCSS and Theming

### Carbon v11 Token Names (IMPORTANT)
Reel48+ uses `@carbon/react` v1.x, which is **Carbon v11**. Use v11 token names only.
The v11 naming convention follows `[element]-[role]-[order]-[state]`.

| v10 Name (DO NOT USE) | v11 Name (USE THIS) | Notes |
|------------------------|---------------------|-------|
| `$interactive-01` | `$background-brand` | Primary brand color |
| `$interactive-04` | `$interactive` | Main interactive token |
| `$ui-background` | `$background` | Page background |
| `$text-01` | `$text-primary` | |
| `$text-02` | `$text-secondary` | |
| `$text-03` | `$text-placeholder` | |
| `$text-04` | `$text-inverse` | |
| `$text-05` | `$text-helper` | |
| `$ui-01` | `$layer-01` | First layer surface |
| `$ui-02` | `$layer-02` | Second layer surface |
| `$ui-03` | `$border-subtle-01` | Subtle border/divider |
| `$ui-04` | `$border-strong-01` | Strong border |
| `$ui-05` | `$border-inverse` | |
| `$icon-01` | `$icon-primary` | |
| `$icon-02` | `$icon-secondary` | |
| `$icon-03` | `$icon-on-color` | |
| `$link-01` | `$link-primary` | |
| `$link-02` | `$link-secondary` | |
| `$support-01` | `$support-error` | |
| `$support-02` | `$support-success` | |
| `$support-03` | `$support-warning` | |
| `$support-04` | `$support-info` | |
| `$inverse-01` | `$text-inverse` | |
| `$inverse-02` | `$background-inverse` | |
| `$overlay-01` | `$overlay` | |
| `$visited-link` | `$link-visited` | |
| `$hover-row` | `$layer-hover-01` | Layer-dependent (`-01`, `-02`, `-03`) |
| `$field-01` | `$field-01` | Unchanged (layering model) |
| `$field-02` | `$field-02` | Unchanged (layering model) |
| `$focus` | `$focus` | Unchanged |

### Sass Module System
Carbon v11 uses the **Dart Sass `@use` module system**, NOT `@import`.
Theme customization uses the `$fallback` and `$theme` parameters (NOT `map-merge`):

```scss
// ✅ CORRECT — Sass @use with $fallback for theme customization
// These are the ACTUAL Reel48+ values from src/styles/carbon-theme.scss
@use '@carbon/react/scss/themes';
@use '@carbon/react/scss/theme' with (
  $fallback: themes.$g10,
  $theme: (
    background-brand: #292c2f,    // Reel48 charcoal brand
    background-inverse: #292c2f,
    interactive: #0a6b6b,         // Teal primary (replaces IBM blue #0f62fe)
    link-primary: #0a6b6b,
    focus: #0a6b6b,
    support-info: #0d8a8a,        // Brand-aligned teal for info
  )
);

// Load Carbon styles (granular imports preferred for smaller bundles)
@use '@carbon/react/scss/reset';
@use '@carbon/react/scss/grid';
@use '@carbon/react/scss/layer';
// Or load everything at once:
@use '@carbon/react';

// ❌ WRONG — map-merge is not the Carbon v11 way
@use 'sass:map';
$custom: map.merge(themes.$g10, (background: #fff));

// ❌ WRONG — deprecated @import syntax
@import '@carbon/react/scss/themes';

// ❌ WRONG — tilde prefix is a webpack legacy pattern
@import '~@carbon/react/scss/globals/scss/styles';
```

**Critical ordering rule:** `@use '@carbon/react/scss/theme' with (...)` MUST appear
BEFORE `@use '@carbon/react'`. Sass modules can only be configured once, at the
first `@use` — if Carbon loads the theme module internally before your `with ()`
clause runs, the customization is silently ignored.

### Reel48+ Color System Quick Reference

# --- ADDED 2026-04-07 — Color scheme finalized ---
# Reason: The color scheme is defined in carbon-theme.scss but this rule file is
#   the primary reference when Claude Code is writing components. Having key values
#   here prevents round-trips to the theme file for common decisions.
# Impact: Claude Code picks the right colors on first attempt during component work.

The full color system lives in `src/styles/carbon-theme.scss` (single source of truth).
Key values for quick reference during component work:

| Role | Hex | CSS Variable / Carbon Token |
|------|-----|-----------------------------|
| Brand (header, sidebar) | `#292c2f` | `--cds-background-brand` |
| Primary interactive | `#0a6b6b` | `--cds-interactive` |
| Interactive hover | `#0d8a8a` | `--r48-teal-600` |
| Interactive on dark | `#3db8b8` | `--r48-teal-400` |
| Sidebar hover | `#353a3f` | `--r48-charcoal-800` |
| Selected row tint | `#e0f5f5` | `--r48-teal-50` |
| Info notifications | `#0d8a8a` | `--cds-support-info` |

**Accent palette** (for badges, charts, categories — use via Tailwind `accent-*` classes):
`amethyst` `azure` `evergreen` `garnet` `coral` `oxblood` `navy` `rose` `saffron` `midnight-teal`

**Layout pattern for dark brand zones:**
```tsx
// Sidebar/header: wrap in g100 Theme for dark Carbon tokens
<Theme theme="g100">
  <SideNav style={{ backgroundColor: '#292c2f' }} />
</Theme>

// Content area: default g10 theme
<Theme theme="g10">
  <main>{children}</main>
</Theme>
```

## Next.js App Router: `'use client'` Directive

Carbon React components are **client components** — they use state, event handlers,
and browser APIs internally. In Next.js App Router:

- Any component file that **imports from `@carbon/react`** must include
  `'use client'` at the top of the file.
- The root **layout** file that imports the global SCSS does NOT need `'use client'`
  (SCSS imports are processed at build time, not runtime).
- Server components can render client components as children, so you don't need
  `'use client'` on every parent — just on the component that directly imports Carbon.

```typescript
// ✅ CORRECT — 'use client' because this file imports Carbon components
'use client';

import { Button, TextInput } from '@carbon/react';

export function LoginForm() {
  return (
    <form>
      <TextInput id="email" labelText="Email" />
      <Button kind="primary" type="submit">Sign in</Button>
    </form>
  );
}
```

## CSS Class Prefix

Carbon v11 uses the `cds--` class prefix (e.g., `cds--btn`, `cds--g10`).
The older `bx--` prefix was Carbon v10. Do not reference `bx--` classes in
custom styles or selectors.

## Carbon Icon Typing

# --- ADDED 2026-04-07 after Module 1 Phase 6 ---
# Reason: Using `React.ComponentType<{ size?: number }>` for icon props causes TS
#   errors because Carbon icons accept `size` as `string | number`. The correct type
#   is `CarbonIconType` from the icons package.
# Impact: Icon-accepting component props compile without workarounds.

When a component prop accepts a Carbon icon, use the `CarbonIconType` type:
```typescript
import type { CarbonIconType } from '@carbon/icons-react/lib/CarbonIcon';

interface NavItem {
  label: string;
  icon: CarbonIconType;
}
```

## Carbon Header `style` Prop

# --- ADDED 2026-04-07 after Module 1 Phase 6 ---
# Reason: Carbon's `<Header>` component does not accept a `style` prop (TypeScript
#   error). Use `className` with Tailwind utilities instead.
# Impact: Prevents TS errors when customizing the header background.

The Carbon `<Header>` component does **not** accept a `style` prop. To set the
brand background color, use a Tailwind class: `className="bg-charcoal-900"`.

## Carbon DataTable `getHeaderProps` / `getRowProps` Key Destructuring

# --- ADDED 2026-04-09 after Module 8 Phase 4 ---
# Reason: Carbon's `getHeaderProps({ header })` and `getRowProps({ row })` return objects
#   that include a `key` property. Spreading these onto a JSX element while also providing
#   an explicit `key` causes a TS error: "'key' is specified more than once". Removing the
#   explicit `key` then causes an ESLint `react/jsx-key` error.
# Impact: All future DataTable usage avoids the duplicate-key TS/ESLint conflict.

When using Carbon's `DataTable` render props, **destructure `key` out of the spread**
to satisfy both TypeScript and ESLint:

```typescript
{tableHeaders.map((header) => {
  const { key, ...headerProps } = getHeaderProps({ header, isSortable: false });
  return (
    <TableHeader key={String(key)} {...headerProps}>
      {header.header}
    </TableHeader>
  );
})}

{tableRows.map((row) => {
  const { key: rowKey, ...rowProps } = getRowProps({ row });
  return (
    <TableRow key={String(rowKey)} {...rowProps}>
      {row.cells.map((cell) => (
        <TableCell key={cell.id}>{cell.value}</TableCell>
      ))}
    </TableRow>
  );
})}
```

## Common Mistakes to Avoid
- ❌ Creating `Button.tsx`, `Input.tsx`, `Modal.tsx`, `DataTable.tsx` wrappers in `src/components/ui/`
- ❌ Using `cva` or `clsx` for component variants (use Carbon props: `kind`, `size`, `type`)
- ❌ Using Tailwind classes to style Carbon component internals (`className="text-red-500"` on a `<TextInput>`)
- ❌ Using Carbon v10 token names (`$interactive-01`, `$ui-background`)
- ❌ Using `@import` instead of `@use` for Carbon SCSS imports
- ❌ Importing icons with wildcard (`import * as Icons from '@carbon/icons-react'`)
- ❌ Sizing icons with Tailwind classes instead of the `size` prop
- ❌ Using arbitrary Tailwind color values (`text-[#3B82F6]`) when a Carbon theme token exists
- ❌ Loading Tailwind directives before Carbon styles (causes Preflight conflicts)
- ❌ Using `dark:` Tailwind variants (dark mode is out of scope for initial launch)
- ❌ Using Tailwind grid for page-level column layout (use Carbon `<Grid>` + `<Column>`)
- ❌ Using `node-sass` instead of `sass` (Dart Sass required for `@use` module syntax)
- ❌ Using `style` prop on Carbon `<Header>` (not supported — use `className`)
- ❌ Using `React.ComponentType<{ size?: number }>` for icon props (use `CarbonIconType`)
