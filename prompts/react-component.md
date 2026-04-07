# Prompt Template: React Component
#
# Use this template when you need Claude Code to create a new React component
# that follows Reel48+ frontend conventions.

## Template

```
Create a React component for {COMPONENT_PURPOSE}.

### Component Details
- Name: {ComponentName}
- Location: src/components/{category}/{ComponentName}.tsx
- Type: {ui primitive | feature component | page component}

### Props
{List props with TypeScript types and whether they're required or optional}

### Behavior
{Describe what the component does, user interactions, state changes}

### Data Requirements
- API endpoint(s) used: {list endpoints}
- Use React Query for data fetching: {yes/no}
- Loading state: {describe}
- Error state: {describe}
- Empty state: {describe}

### Tenant Awareness
- Does this component need to check the user's role? {yes/no — describe}
- Does it show different content for different roles? {yes/no — describe}
- Does it need TenantContext? {yes/no}

### Styling
- Use Carbon components from `@carbon/react` for all standard UI elements
  (buttons, inputs, modals, tables, dropdowns, notifications)
- Use Carbon component props for variants (e.g., `kind="primary"`,
  `size="lg"`) — do NOT use cva/clsx
- Use Tailwind CSS for layout utilities (flex, grid, gap, spacing) and
  custom styles where Carbon has no equivalent
- Do NOT override Carbon component internals with Tailwind classes
- Responsive: {mobile-first — Carbon Grid for page layout, Tailwind
  breakpoints for fine-grained adjustments}
- Theme tokens: {reference brand colors from src/styles/carbon-theme.scss}

### Tests
Write tests using Vitest + React Testing Library that verify:
- {key user interaction 1}
- {key user interaction 2}
- {role-based rendering if applicable}
- {error state handling}

### Acceptance Criteria
- [ ] TypeScript strict mode — no `any` types
- [ ] Named export (not default export, unless it's a page component)
- [ ] Props interface defined and exported
- [ ] Loading, error, and empty states handled
- [ ] Uses Carbon components where available (not custom implementations)
- [ ] No Tailwind overrides on Carbon component internals
- [ ] Accessible (proper aria labels, keyboard navigation)
- [ ] Tests written with accessible queries (getByRole, getByLabelText)
```
