# UI Coding Standards

This document defines the UI coding standards for the entire project.

## Component Usage

### Rule: Use Only shadcn/ui Components

**IMPORTANT: You MUST use ONLY shadcn/ui components. NEVER create custom components.**

- All UI elements must be built using shadcn/ui components
- Do not create custom styled components
- Do not create wrapper components around shadcn/ui
- If a component doesn't exist in shadcn/ui, use a combination of existing shadcn/ui components

### Installing shadcn/ui Components

```bash
npx shadcn@latest add [component-name]
```

### Available Components

Refer to the official shadcn/ui documentation: https://ui.shadcn.com/docs/components

Common components:
- Button
- Card
- Dialog
- Input
- Label
- Select
- Table
- Tabs
- Toast
- Form
- Calendar
- DatePicker

## Date Formatting

### Rule: Use date-fns for All Date Formatting

```bash
npm install date-fns
```

### Date Format Standard

All dates must be displayed in the following format:

```
1st Sep 2025
2nd Aug 2025
3rd Jan 2026
4th Jun 2024
```

### Implementation

```typescript
import { format } from 'date-fns';

function formatDate(date: Date): string {
  const day = format(date, 'd');
  const month = format(date, 'MMM');
  const year = format(date, 'yyyy');

  const suffix = getOrdinalSuffix(parseInt(day));

  return `${day}${suffix} ${month} ${year}`;
}

function getOrdinalSuffix(day: number): string {
  if (day >= 11 && day <= 13) {
    return 'th';
  }

  switch (day % 10) {
    case 1:
      return 'st';
    case 2:
      return 'nd';
    case 3:
      return 'rd';
    default:
      return 'th';
  }
}
```

### Usage Example

```typescript
import { formatDate } from '@/lib/utils';

// In component
<span>{formatDate(new Date('2025-09-01'))}</span>
// Output: "1st Sep 2025"
```

## K-CIA Domain Components (Exception)

The "no custom components" rule applies to **general UI primitives** (buttons, inputs, dialogs, etc.). The following **domain-specific components** are allowed because shadcn/ui does not provide equivalents:

- `HexMap.tsx` — Deck.gl 3D hexagon map (no shadcn equivalent)
- `AsOfBadge.tsx` — Data freshness indicator badge
- `MetricCard.tsx` — Hex detail metric card with QoQ mini-chart
- `FilterPanel.tsx` — Map filter controls (composed from shadcn/ui primitives)
- `ChatPanel.tsx` — AI chat interface (uses Vercel AI SDK)

**Rule:** Domain components must be built **using shadcn/ui primitives internally** wherever possible (e.g., Card, Badge, Select inside FilterPanel). Only create custom rendering when no shadcn/ui component exists (e.g., Deck.gl canvas).

## Summary

| Category | Standard |
|----------|----------|
| UI Components | shadcn/ui ONLY (for general primitives) |
| Domain Components | Allowed (HexMap, AsOfBadge, MetricCard, etc.) |
| Date Library | date-fns |
| Date Format | `1st Sep 2025` |
