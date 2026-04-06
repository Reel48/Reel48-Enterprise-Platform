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
- Use Tailwind CSS (no CSS modules or styled-components)
- Responsive: {mobile-first breakpoints needed}
- Design tokens: {reference any specific colors, spacing from tailwind.config}

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
- [ ] Accessible (proper aria labels, keyboard navigation)
- [ ] Tests written with accessible queries (getByRole, getByLabelText)
```
