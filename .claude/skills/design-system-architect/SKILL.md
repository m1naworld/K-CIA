---
name: design-system-architect
description: Align implementation plans and UI decisions with the project's design-system artifacts. Use when deciding token structure, component families, primitives, or rollout order.
allowed-tools: Read Glob Grep Bash
paths:
  - "design-system/**"
  - "src/**"
  - "app/**"
  - "components/**"
  - "styles/**"
---

When this skill is active:

1. Read `design-system/system_spec.md` first.
2. Read `design-system/token_schema.json` and `design-system/component_inventory.json`.
3. If present, use `design-system/system_ontology.json` to understand relations between principles, token categories, and component families.
4. Translate user requests into:
   - affected principles
   - affected token categories
   - affected component families
   - required implementation order
5. Favor extending existing primitives over inventing new components.
6. Explicitly guard against anti-keywords from the system spec.

If any artifact file is missing, say exactly which file is missing and recommend syncing artifacts from the harness repo before implementation.
